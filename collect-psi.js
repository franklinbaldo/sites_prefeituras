// collect-psi.js
import fs from 'fs';
import path, { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import fetch from 'node-fetch';
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
    logMessage('INFO', `Processing state saved to ${filePath}`, 'saveState');
  } catch (err) {
    logMessage('ERROR', `Error saving processing state to ${filePath}: ${err.message}`, 'saveState');
  }
}

// Save a single result immediately to JSON and CSV
function persistResult(resultObj, jsonFile, csvFile, existingResults) {
  existingResults.push(resultObj);
  fs.writeFileSync(jsonFile, JSON.stringify(existingResults, null, 2));

  const csvHeader = 'timestamp,url,ibge_code,performance,accessibility,seo,bestPractices';
  const csvLine = `${resultObj.timestamp},${resultObj.url},${resultObj.ibge_code},${resultObj.performance},${resultObj.accessibility},${resultObj.seo},${resultObj.bestPractices}`;
  if (!fs.existsSync(csvFile)) {
    fs.writeFileSync(csvFile, csvHeader + '\n' + csvLine + '\n');
  } else {
    fs.appendFileSync(csvFile, csvLine + '\n');
  }
}

// Function to log messages to console and file
function logMessage(level, message, context = '') {
  const timestamp = new Date().toISOString();
  const upperLevel = level.toUpperCase();

  let consoleMessage = `[${upperLevel}]`;
  if (context) {
    consoleMessage += ` [${context}]`;
  }
  consoleMessage += ` ${message}`;

  let fileMessage = `[${timestamp}] [${upperLevel}]`;
  if (context) {
    fileMessage += ` [${context}]`;
  }
  fileMessage += ` ${message}`;

  // Console Logging
  if (upperLevel === 'DEBUG') {
    if (process.env.PSI_DEBUG_LOG === 'true') {
      console.log(consoleMessage);
    }
  } else if (upperLevel === 'INFO') {
    console.log(consoleMessage);
  } else if (upperLevel === 'WARNING') {
    console.warn(consoleMessage);
  } else if (upperLevel === 'ERROR') {
    console.error(consoleMessage);
  } else {
    console.log(consoleMessage); // Default for unknown levels
  }

  // File Logging for INFO, WARNING, ERROR
  if (['INFO', 'WARNING', 'ERROR'].includes(upperLevel)) {
    logErrorToFile(fileMessage); // Pass the fully formatted message for the file
  }
}

// Simplified function to append pre-formatted messages to a log file
function logErrorToFile(formattedMessage) {
  try {
    fs.appendFileSync(ERROR_LOG_FILE, formattedMessage + '\n');
  } catch (err) {
    // If logging to file fails, log to console as a fallback
    console.error(`Fallback: Failed to write to ${ERROR_LOG_FILE}: ${err.message}`);
    console.error(`Fallback: Original error message: ${formattedMessage}`);
  }
}

// This function will be unit tested
export async function originalFetchPSI(url, apiKey, fetchFn) {
  const endpoint = `https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed`
    + `?url=${encodeURIComponent(url)}`
    + `&strategy=mobile`
    + `&category=performance`
    + `&category=accessibility`
    + `&category=best-practices`
    + `&category=seo`
    + `&key=${apiKey}`;
  const res = await fetchFn(endpoint);
  if (res.status === 429) {
    throw new Error('Rate limit');
  }
  const json = await res.json();

  // Validate the PSI response structure to avoid undefined errors
  const cat = json?.lighthouseResult?.categories;
  if (!cat) {
    const errorMsg = json?.error?.message || 'Invalid PSI response';
    throw new Error(errorMsg);
  }

  return {
    url,
    performance: cat.performance?.score ?? null,
    accessibility: cat.accessibility?.score ?? null,
    seo: cat.seo?.score ?? null,
    bestPractices: cat['best-practices']?.score ?? null,
    timestamp: new Date().toISOString(),
  };
}

// This is the script's own mock, used when run with --test directly
async function scriptMockFetchPSI(url) {
  logMessage('DEBUG', `SCRIPT MOCK fetchPSI called for: ${url}`, 'mockFetchPSI');
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

// Wrapper to retry PSI fetches on rate limit errors
async function fetchPSIWithRetry(url, fetchFn, maxRetries = 2, baseDelay = 1000) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fetchFn(url);
    } catch (err) {
      if (err.message === 'Rate limit' && attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt);
        logMessage('WARNING', `Rate limit for ${url}. Retrying in ${delay}ms (attempt ${attempt + 1}/${maxRetries})`, 'retry');
        await new Promise(res => setTimeout(res, delay));
      } else {
        throw err;
      }
    }
  }
}

// Main logic of the script, now exportable and testable
export async function runMainLogic(argv, currentApiKey, externalFetchPSI) {
  logMessage('INFO', 'PSI data collection script started.', 'main');
  API_KEY = currentApiKey; // Update API_KEY from parameter for testability
  if (!API_KEY) {
    logMessage('ERROR', 'PSI_KEY environment variable is NOT SET.', 'init');
    process.exit(1); // This will be mocked in tests
  } else {
    logMessage('INFO', 'PSI_KEY environment variable is set.', 'init');
  }

  const scriptStartTime = Date.now();
  const SCRIPT_TIMEOUT_MS = 9.5 * 60 * 1000; // 9.5 minutes

  const isTestMode = argv.includes('--test');
  const baseDir = process.cwd();
  const inputCsvFile = isTestMode
      ? path.resolve(baseDir, 'test_sites.csv')
      : path.resolve(baseDir, 'sites_das_prefeituras_brasileiras.csv');
  const outputJsonFile = isTestMode ? 'data/test-psi-results.json' : 'data/psi-results.json';
  const outputCsvFile = isTestMode ? 'data/test-psi-results.csv' : 'data/psi-results.csv';

  const outDir = path.resolve('data');
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir);

  logMessage('INFO', `Running in ${isTestMode ? 'TEST' : 'PRODUCTION'} mode. Input: ${inputCsvFile}, Output: ${outputJsonFile}, CSV: ${outputCsvFile}`, 'init');

  let processingState = {};
  try {
    if (fs.existsSync(PROCESSING_STATE_FILE)) {
      processingState = JSON.parse(fs.readFileSync(PROCESSING_STATE_FILE, 'utf-8'));
      logMessage('INFO', `Loaded processing state from ${PROCESSING_STATE_FILE}`, 'loadState');
    } else {
      logMessage('INFO', `No processing state file found at ${PROCESSING_STATE_FILE}. Starting with a fresh state.`, 'loadState');
    }
  } catch (err) {
    logMessage('WARNING', `Error loading or parsing ${PROCESSING_STATE_FILE}: ${err.message}. Starting with a fresh state.`, 'loadState');
    processingState = {}; // Reset to empty if error
  }

  let allCsvUrls;
  let urlToIbge = {};
  try {
    const csv = fs.readFileSync(inputCsvFile, 'utf-8'); // fs will be mocked in tests
    const rows = csvParse(csv, { columns: true, skip_empty_lines: true });

    const sample = rows[0] || {};
    let urlField = Object.keys(sample).find(k => k.toLowerCase().includes('url'));
    if (!urlField) {
      urlField = Object.keys(sample).find(k => k.toLowerCase().includes('endere'));
    }
    const ibgeField = Object.keys(sample).find(k => k.toLowerCase().includes('ibge'));

    allCsvUrls = [];
    for (const row of rows) {
      const url = row[urlField];
      const ibge = row[ibgeField];
      if (url && url.startsWith('http')) {
        allCsvUrls.push(url);
        urlToIbge[url] = ibge;
      }
    }
    logMessage('INFO', `Loaded ${allCsvUrls.length} URLs from ${inputCsvFile} after initial filter.`, 'readCsvFile');

    if (allCsvUrls.length === 0) {
      const message = `Nenhuma URL válida (http/https) encontrada em ${inputCsvFile} na coluna 'url'.`;
      logMessage('WARNING', message, 'readCsvFile');
      // Se não há URLs válidas em allCsvUrls, não há o que processar.
      // O script vai perceber que urlsToProcess está vazio mais adiante e reportar "Nenhum resultado para gravar."
    }
  } catch (err) {
    const errorMessage = `Erro ao ler ou processar o arquivo CSV ${inputCsvFile}: ${err.message}`;
    // console.error automatically handled by logMessage
    logMessage('ERROR', errorMessage, 'readCsvFile');
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
          logMessage('WARNING', `Invalid last_attempt date found for ${url}: "${stateEntry.last_attempt}". Treating as new/very old.`, 'urlPrioritization');
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
      logMessage('INFO', `Prioritized ${urlsToProcess.length} URLs for processing. Newest/oldest attempts will be processed first.`, 'urlPrioritization');
      logMessage('DEBUG', `Top URLs in queue: ${urlsToProcess.slice(0, 5).join(', ')}`, 'urlPrioritization');
    }
  }

  if (urlsToProcess.length === 0) {
    // This message is slightly different from the one above, specifically if allCsvUrls was not empty but filtering made it empty
    logMessage('INFO', 'No URLs to process after filtering and prioritization.', 'urlPrioritization');
  }

  // Use externalFetchPSI if provided (for unit tests), otherwise choose based on mode
  const fetchPSI = externalFetchPSI
    ? externalFetchPSI
    : isTestMode
      ? scriptMockFetchPSI
      : (url) => originalFetchPSI(url, API_KEY, fetch); // Pass API_KEY and global fetch

  const maxRetries = parseInt(process.env.PSI_MAX_RETRIES || '2', 10);
  const retryDelay = parseInt(process.env.PSI_RETRY_DELAY_MS || '1000', 10);
  const delayBetweenRequests = 1000; // 1 second between requests
  const results = [];
  let processedInThisRunCount = 0;

  let existingResults = [];
  if (fs.existsSync(outputJsonFile)) {
    try {
      existingResults = JSON.parse(fs.readFileSync(outputJsonFile, 'utf-8'));
    } catch (err) {
      logMessage('WARNING', `Error reading existing results from ${outputJsonFile}: ${err.message}`, 'loadResults');
      existingResults = [];
    }
  }

  logMessage('INFO', `Starting sequential processing of ${urlsToProcess.length} URLs with 1s spacing.`, 'mainLoop');
  for (const url of urlsToProcess) {
    const elapsedTime = Date.now() - scriptStartTime;
    if (elapsedTime >= SCRIPT_TIMEOUT_MS) {
      logMessage('INFO', `Time limit approaching. Stopping new requests. Elapsed: ${(elapsedTime / 60000).toFixed(2)} mins.`, 'timeout');
      break;
    }

    const attemptTimestamp = new Date().toISOString();
    if (!processingState[url]) {
      processingState[url] = { last_attempt: attemptTimestamp, last_success: null };
    } else {
      processingState[url].last_attempt = attemptTimestamp;
    }
    saveProcessingState(processingState, PROCESSING_STATE_FILE);

    try {
      const data = await fetchPSIWithRetry(url, fetchPSI, maxRetries, retryDelay);
      logMessage('INFO', `✅ ${url} → ${data.performance}`, 'fetchPSISuccess');
      const resultObj = { ...data, ibge_code: urlToIbge[url] };
      results.push(resultObj);
      processedInThisRunCount++;
      processingState[url].last_success = new Date().toISOString();
      saveProcessingState(processingState, PROCESSING_STATE_FILE);
      persistResult(resultObj, outputJsonFile, outputCsvFile, existingResults);
    } catch (err) {
      logMessage('ERROR', `Error for URL ${url}: ${err.message}`, 'fetchPSI');
      saveProcessingState(processingState, PROCESSING_STATE_FILE);
    }

    await new Promise(res => setTimeout(res, delayBetweenRequests));
  }

  logMessage('INFO', `Processed ${processedInThisRunCount} URLs in this run.`, 'summary');
  saveProcessingState(processingState, PROCESSING_STATE_FILE);
  logMessage('INFO', 'PSI data collection script finished.', 'main');
}

// This allows the script to still be run directly using `node collect-psi.js`
if (process.argv[1] && process.argv[1].endsWith('collect-psi.js')) {
  (async () => {
    await runMainLogic(process.argv, process.env.PSI_KEY);
    // logMessage('INFO', 'PSI data collection script finished (direct invocation).', 'main'); // Already logged at the end of runMainLogic
  })();
}
