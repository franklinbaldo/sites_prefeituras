// collect-psi.js
import fs from 'fs';
import path, { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import fetch from 'node-fetch';
import pLimit from 'p-limit';
import { parse as csvParse } from 'csv-parse/sync';

let API_KEY = process.env.PSI_KEY; // Made non-const to allow modification in tests

const ERROR_LOG_FILE = 'psi_errors.log';
const PROCESSING_STATE_FILE = 'data/psi_processing_state.json';

// Function to save processing state
function saveProcessingState(stateObject, filePath) {
  try {
    const outDir = path.dirname(filePath);
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true });
    }
    fs.writeFileSync(filePath, JSON.stringify(stateObject, null, 2));
    console.log(`💾 Processing state saved to ${filePath}`);
  } catch (err) {
    console.error(`❌ Error saving processing state to ${filePath}: ${err.message}`);
  }
}

// Function to log errors to a file
function logErrorToFile(errorMessage) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${errorMessage}\n`;
  try {
    fs.appendFileSync(ERROR_LOG_FILE, logMessage);
  } catch (err) {
    // If logging to file fails, log to console as a fallback
    console.error(`Fallback: Failed to write to ${ERROR_LOG_FILE}: ${err.message}`);
    console.error(`Fallback: Original error: ${errorMessage}`);
  }
}

// This function will be unit tested
export async function originalFetchPSI(url, apiKey, fetchFn, params = {}) {
  const queryParams = new URLSearchParams();
  queryParams.append('url', encodeURIComponent(url));
  for (const key in params) {
    queryParams.append(key, params[key]);
  }
  queryParams.append('key', apiKey);

  const endpoint = `https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed?${queryParams.toString()}`;

  const response = await fetchFn(endpoint);
  const status = response.status;
  let json;

  try {
    json = await response.json();
  } catch (e) {
    const error = new Error(`Invalid JSON response from PSI API for ${url}. Status: ${status}. Error: ${e.message}`);
    error.status = status; // Attach status to error
    throw error;
  }

  if (!response.ok) {
    const message = json?.error?.message || `API request failed with status ${status}`;
    const code = json?.error?.code;
    const apiErrorDetails = json?.error;

    const error = new Error(message);
    error.status = status;
    error.code = code; // Standard error code if available
    error.apiError = apiErrorDetails; // Full Google API error details
    throw error;
  }

  // If successful, return the full JSON and status. Specific scores can be extracted later.
  return { json, status };
}

// This is the script's own mock, used when run with --test directly
async function scriptMockFetchPSI(url, apiKey, fetchFn, params = {}) { // Add params for consistent signature
  console.log(`ℹ️ SCRIPT MOCK fetchPSI called for: ${url} with params: ${JSON.stringify(params)}`);
  if (url === 'http://example.com' || url === 'http://another-example.com') {
    // Mimic the new structure returned by originalFetchPSI
    return {
      status: 200,
      json: {
        lighthouseResult: {
          categories: {
            performance: { score: 0.9 },
            accessibility: { score: 0.8 },
            seo: { score: 0.7 },
            'best-practices': { score: 0.95 }
          },
          fetchTime: new Date().toISOString() // Add fetchTime for logging consistency
        },
        // Include other fields if your main logic uses them from the raw report
        analysisUTCTimestamp: new Date().toISOString()
      }
    };
  } else if (url === 'http://invalid-url-that-does-not-exist-hopefully.com') {
    const error = new Error('Simulated fetch error for non-existent URL');
    error.status = 500; // Simulate a server error status
    error.apiError = { code: 500, message: 'Simulated API error details' };
    throw error;
  } else {
    const error = new Error(`Script Mock PSI fetch not defined for URL: ${url}`);
    error.status = 404; // Simulate not found
    error.apiError = { code: 404, message: 'URL not covered by script mock' };
    throw error;
  }
}

// Main logic of the script, now exportable and testable
export async function runMainLogic(argv, currentApiKey, externalFetchPSI) {
  // Global Context Logging
  console.log("🚀 Iniciando script collect-psi...");
  console.log(`🔧 Ambiente: NODE_ENV=${process.env.NODE_ENV || 'undefined'} | CI=${process.env.CI || 'undefined'}`);
  console.log(`🔧 Versão do Node: ${process.version}`);

  API_KEY = currentApiKey; // Update API_KEY from parameter for testability
  if (!API_KEY) {
    console.error('⚠️ Defina a variável de ambiente PSI_KEY');
    process.exit(1); // This will be mocked in tests
  }

  const scriptStartTime = Date.now();
  const SCRIPT_TIMEOUT_MS = 9.5 * 60 * 1000; // 9.5 minutes

  const isTestMode = argv.includes('--test');
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);

  // Create reports directory if it doesn't exist
  if (!fs.existsSync('reports')) {
    fs.mkdirSync('reports', { recursive: true });
  }
  const baseDir = __dirname; // Or resolve(__dirname, '..') if the script is in a subdirectory like 'src'
  const inputCsvFile = isTestMode
      ? path.resolve(baseDir, 'test_sites.csv')
      : path.resolve(baseDir, 'sites_das_prefeituras_brasileiras.csv');
  const outputJsonFile = isTestMode ? 'data/test-psi-results.json' : 'data/psi-results.json';

  console.log(`ℹ️ Running in ${isTestMode ? 'TEST' : 'PRODUCTION'} mode.`);
  console.log(`ℹ️ Reading URLs from: ${inputCsvFile}`);

  let processingState = {};
  try {
    if (fs.existsSync(PROCESSING_STATE_FILE)) {
      processingState = JSON.parse(fs.readFileSync(PROCESSING_STATE_FILE, 'utf-8'));
      console.log(`ℹ️ Loaded processing state from ${PROCESSING_STATE_FILE}`);
    } else {
      console.log(`ℹ️ No processing state file found at ${PROCESSING_STATE_FILE}. Starting with a fresh state.`);
    }
  } catch (err) {
    console.warn(`⚠️ Error loading or parsing ${PROCESSING_STATE_FILE}: ${err.message}. Starting with a fresh state.`);
    processingState = {}; // Reset to empty if error
  }

  let allCsvUrls;
  try {
    const csv = fs.readFileSync(inputCsvFile, 'utf-8'); // fs will be mocked in tests
    const rows = csvParse(csv, { columns: true, skip_empty_lines: true });
    allCsvUrls = rows.map(r => r['url']).filter(u => u && u.startsWith('http'));

    if (allCsvUrls.length === 0) {
      const message = `Nenhuma URL válida (http/https) encontrada em ${inputCsvFile} na coluna 'url'.`;
      console.warn(`⚠️ ${message}`);
      logErrorToFile(message);
      // Se não há URLs válidas em allCsvUrls, não há o que processar.
      // O script vai perceber que urlsToProcess está vazio mais adiante e reportar "Nenhum resultado para gravar."
    }
  } catch (err) {
    const errorMessage = `Erro ao ler ou processar o arquivo CSV ${inputCsvFile}: ${err.message}`;
    console.error(`❌ ${errorMessage}`);
    logErrorToFile(errorMessage);
    return;
  }

  // Prioritize URLs based on processingState
  let urlsToProcess = [];
  if (allCsvUrls && allCsvUrls.length > 0) {
    urlsToProcess = allCsvUrls.map(url => {
      const stateEntry = processingState[url];
      let lastAttemptDate = new Date(0); // Default to very old if new or no valid timestamp
      if (stateEntry && stateEntry.last_attempt) {
        const parsedDate = new Date(stateEntry.last_attempt);
        if (!isNaN(parsedDate)) { // Check if the date is valid
          lastAttemptDate = parsedDate;
        } else {
          console.warn(`⚠️ Invalid last_attempt date found for ${url}: "${stateEntry.last_attempt}". Treating as new/very old.`);
        }
      }
      return {
        url: url,
        last_attempt: lastAttemptDate
      };
    })
    .sort((a, b) => a.last_attempt - b.last_attempt) // Sorts by date, ascending (oldest first)
    .map(item => item.url);

    if (urlsToProcess.length > 0) {
      console.log(`ℹ️ Prioritized ${urlsToProcess.length} URLs. Newest/oldest attempts will be processed first.`);
      // console.log(`ℹ️ Top URLs in queue: ${urlsToProcess.slice(0, 5).join(', ')}`); // Optional: for debugging
    }
  }

  if (urlsToProcess.length === 0) {
    console.log('ℹ️ No URLs to process after prioritization (or CSV was empty/invalid).');
  }

  console.log(`ℹ️ Writing results to: ${outputJsonFile}`);

  // Use externalFetchPSI if provided (for unit tests), otherwise choose based on mode
  const effectiveFetchPSI = externalFetchPSI
    ? externalFetchPSI
    : isTestMode
      ? (url, apiKey, fetchFn, params) => scriptMockFetchPSI(url, API_KEY, fetch, params) // Ensure mock also gets params
      : (url, apiKey, fetchFn, params) => originalFetchPSI(url, API_KEY, fetch, params);

  const limit = pLimit(4); // Concurrency limit
  const successes = [];
  const failures = [];
  const activeTasks = [];
  let processedInThisRunCount = 0; // Renamed from results to avoid confusion

  urlsToProcess.forEach((url, index) => {
    const elapsedTime = Date.now() - scriptStartTime;
    if (elapsedTime >= SCRIPT_TIMEOUT_MS) {
      console.log(`ℹ️ Time limit approaching (${(elapsedTime / 60000).toFixed(2)} mins). No more URLs will be processed in this run.`);
      return; // Exit forEach iteration if time limit reached (won't stop already queued tasks)
    }

    // Initialize or update the URL's entry in processingState and set last_attempt
    const attemptTimestamp = new Date().toISOString();
    if (!processingState[url]) {
      processingState[url] = { last_attempt: attemptTimestamp, last_success: null };
    } else {
      processingState[url].last_attempt = attemptTimestamp;
    }

    activeTasks.push(
      limit(async () => {
        console.log(`▶️ [${index + 1}/${urlsToProcess.length}] Iniciando análise para ${url} — ${new Date().toISOString()}`);
        const psiParams = { strategy: 'mobile' /* add other relevant params like locale if used */ };
        console.log(`   • Parâmetros: strategy=${psiParams.strategy}`);

        try {
          const responseData = await effectiveFetchPSI(url, API_KEY, fetch, psiParams);

          const fetchTime = responseData.json.lighthouseResult?.fetchTime || responseData.json.analysisUTCTimestamp || 'N/A';
          console.log(`✅ Sucesso: ${url} — HTTP ${responseData.status} — tempo total: ${fetchTime}`);

          const slug = url.replace(/https?:\/\//, '').replace(/[\/.:?&=%]/g, '_');
          const reportPath = `reports/pagespeed-${slug}.json`;
          fs.writeFileSync(reportPath, JSON.stringify(responseData.json, null, 2));
          console.log(`   • Relatório salvo em: ${reportPath}`);

          // Extract key data for successes (similar to old 'results' array but from new response structure)
          const cat = responseData.json.lighthouseResult?.categories;
          if (cat) {
            successes.push({
              url,
              performance: cat.performance?.score ?? null,
              accessibility: cat.accessibility?.score ?? null,
              seo: cat.seo?.score ?? null,
              bestPractices: cat['best-practices']?.score ?? null,
              timestamp: new Date().toISOString()
            });
          } else {
            // Should not happen if PSI API call was successful and returned valid JSON
            console.warn(`⚠️ Missing categories in PSI result for ${url}. Raw report saved.`);
            successes.push({ url, timestamp: new Date().toISOString(), warning: "Missing category scores" });
          }

          processedInThisRunCount++;
          processingState[url].last_success = new Date().toISOString();

        } catch (err) {
          console.error(`❌ Falha: ${url} — ${new Date().toISOString()}`);
          console.error(`   • Mensagem: ${err.message}`);
          if (err.stack) {
            const trechoStack = err.stack.split('\n').slice(0, 3).join(' | ');
            console.error(`   • Stack (top 3): ${trechoStack}`);
          }
          if (err.status) { // HTTP status from our custom error in originalFetchPSI
            console.error(`   • HTTP status: ${err.status}`);
          }
          if (err.apiError) { // Custom field for Google API error details
            console.error(`   • Erro API Google (code ${err.apiError.code}): ${err.apiError.message}`);
          }
          failures.push({ url, reason: err.message, status: err.status, apiErrorCode: err.apiError?.code });
          logErrorToFile(`Error for URL ${url}: ${err.message}${err.status ? ` (HTTP ${err.status})` : ''}${err.apiError ? ` (API Code: ${err.apiError.code} - ${err.apiError.message})` : ''}`);
        }
      })
    );
  });

  console.log(`ℹ️ Waiting for ${activeTasks.length} active PSI tasks to complete...`);
  await Promise.all(activeTasks);
  console.log(`ℹ️ All active PSI tasks finished.`);

  // --- Comprehensive Final Summary ---
  console.log("\n🔔 ===================== RESUMO GERAL =====================");
  console.log(`📈 Total de URLs na lista de entrada (CSV): ${allCsvUrls.length}`);
  console.log(`🔩 Total de URLs efetivamente processadas (após priorização e timeout): ${activeTasks.length}`);
  // processedInThisRunCount reflects successful PSI API calls, successes.length is after data extraction
  console.log(`👍 Sucessos (dados extraídos e salvos): ${successes.length}`);
  console.log(`👎 Falhas (erros durante a tentativa): ${failures.length}`);

  if (failures.length > 0) {
    console.log("   --- Detalhes das URLs com falha ---");
    failures.forEach(f => {
      let detail = `     – ${f.url} → Motivo: ${f.reason}`;
      if (f.status) detail += ` (HTTP ${f.status})`;
      if (f.apiErrorCode) detail += ` (API Code: ${f.apiErrorCode})`;
      console.log(detail);
    });
    console.log("   -----------------------------------");
  }
  console.log("🔔 =======================================================\n");

  // Save the updated processingState
  saveProcessingState(processingState, PROCESSING_STATE_FILE);

  // Save overall results (scores from successful fetches)
  // This replaces the old 'results' array saving logic
  if (successes.length > 0) {
    const outDir = path.dirname(outputJsonFile); // Use path.dirname for outputJsonFile
    if (!fs.existsSync(outDir)) {
      fs.mkdirSync(outDir, { recursive: true });
    }
    fs.writeFileSync(
      outputJsonFile,
      JSON.stringify(successes, null, 2)
    );
    console.log(`💾 Gravados ${successes.length} resultados de sucesso em ${outputJsonFile}`);
  } else {
    console.log('ℹ️ Nenhum resultado de sucesso para gravar.');
  }
}

// This allows the script to still be run directly using `node collect-psi.js`
if (process.argv[1] && process.argv[1].endsWith('collect-psi.js')) {
  (async () => {
    await runMainLogic(process.argv, process.env.PSI_KEY);
  })();
}
