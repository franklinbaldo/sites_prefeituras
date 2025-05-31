// collect-psi.js
import fs from 'fs';
import path from 'path';
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
export async function originalFetchPSI(url, apiKey, fetchFn) {
  const endpoint = `https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed`
    + `?url=${encodeURIComponent(url)}`
    + `&strategy=mobile`
    + `&key=${apiKey}`;
  const res = await fetchFn(endpoint);
  if (res.status === 429) {
    throw new Error('Rate limit');
  }
  const json = await res.json();
  const cat = json.lighthouseResult.categories;
  return {
    url,
    performance: cat.performance.score,
    accessibility: cat.accessibility.score,
    seo: cat.seo.score,
    bestPractices: cat['best-practices']?.score ?? null,
    timestamp: new Date().toISOString()
  };
}

// This is the script's own mock, used when run with --test directly
async function scriptMockFetchPSI(url) {
  console.log(`ℹ️ SCRIPT MOCK fetchPSI called for: ${url}`);
  if (url === 'http://example.com' || url === 'http://another-example.com') {
    return {
      url,
      performance: 0.9,
      accessibility: 0.8,
      seo: 0.7,
      bestPractices: 0.95,
      timestamp: new Date().toISOString()
    };
  } else if (url === 'http://invalid-url-that-does-not-exist-hopefully.com') {
    throw new Error('Simulated fetch error for non-existent URL');
  } else {
    throw new Error(`Script Mock PSI fetch not defined for URL: ${url}`);
  }
}

// Main logic of the script, now exportable and testable
export async function runMainLogic(argv, currentApiKey, externalFetchPSI) {
  API_KEY = currentApiKey; // Update API_KEY from parameter for testability
  if (!API_KEY) {
    console.error('⚠️ Defina a variável de ambiente PSI_KEY');
    process.exit(1); // This will be mocked in tests
  }

  const scriptStartTime = Date.now();
  const SCRIPT_TIMEOUT_MS = 9.5 * 60 * 1000; // 9.5 minutes

  const isTestMode = argv.includes('--test');
  const inputCsvFile = isTestMode ? 'test_sites.csv' : 'sites_das_prefeituras_brasileiras.csv';
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
  const fetchPSI = externalFetchPSI
    ? externalFetchPSI
    : isTestMode
      ? scriptMockFetchPSI
      : (url) => originalFetchPSI(url, API_KEY, fetch); // Pass API_KEY and global fetch

  const limit = pLimit(4); // Concurrency limit
  const results = []; // To store PSI scores of successfully processed URLs in this run
  const activeTasks = []; // To store promises of tasks added to p-limit
  let processedInThisRunCount = 0;

  for (const url of urlsToProcess) {
    const elapsedTime = Date.now() - scriptStartTime;
    if (elapsedTime >= SCRIPT_TIMEOUT_MS) {
      console.log(`ℹ️ Time limit approaching (${(elapsedTime / 60000).toFixed(2)} mins). No more URLs will be processed in this run.`);
      break; // Exit the loop, stop adding new tasks
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
        try {
          const data = await fetchPSI(url); // fetchPSI is the actual PSI fetching function
          console.log(`✅ ${url} → ${data.performance}`);
          results.push(data);
          processedInThisRunCount++;
          // Update last_success on successful fetch
          processingState[url].last_success = new Date().toISOString();
        } catch (err) {
          const errorMsg = `erro em ${url}: ${err.message}`;
          console.warn(`❌ ${errorMsg}`);
          logErrorToFile(`Error for URL ${url}: ${err.message}`);
          // On error, last_success for processingState[url] is NOT updated,
          // preserving its previous success state (or null if never successful).
        }
      })
    );
  }

  console.log(`ℹ️ Waiting for ${activeTasks.length} active PSI tasks to complete...`);
  await Promise.all(activeTasks);
  console.log(`ℹ️ All active PSI tasks finished.`);
  console.log(`📈 Processed ${processedInThisRunCount} URLs successfully in this run.`);

  // Save the updated processingState
  saveProcessingState(processingState, PROCESSING_STATE_FILE);

  if (results.length > 0) {
    const outDir = path.resolve('data');
    if (!fs.existsSync(outDir)) fs.mkdirSync(outDir); // fs will be mocked
    fs.writeFileSync( // fs will be mocked
      outputJsonFile,
      JSON.stringify(results, null, 2)
    );
    console.log(`💾 Gravados ${results.length} resultados em ${outputJsonFile}`);
  } else {
    console.log('ℹ️ Nenhum resultado para gravar.');
  }
}

// This allows the script to still be run directly using `node collect-psi.js`
if (process.argv[1] && process.argv[1].endsWith('collect-psi.js')) {
  (async () => {
    await runMainLogic(process.argv, process.env.PSI_KEY);
  })();
}
