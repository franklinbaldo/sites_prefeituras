// collect-psi.js
import fs from 'fs';
import path from 'path';
import fetch from 'node-fetch';
import { parse as csvParse } from 'csv-parse/sync';
import pLimit from 'p-limit';
import pThrottle from 'p-throttle';
import duckdb from 'duckdb';

let API_KEY = process.env.PSI_KEY; // Made non-const to allow modification in tests

const ERROR_LOG_FILE = 'psi_errors.log';
const PROCESSING_STATE_FILE = 'data/psi_processing_state.json';
const DUCKDB_FILE = path.resolve(process.cwd(), 'data/psi_results.duckdb');
const DUCKDB_TABLE_NAME = 'psi_metrics';

// DuckDB database instance and connection
let db;
let conn;

// Function to initialize DuckDB and create table if it doesn't exist
async function initDuckDB() {
  db = new duckdb.Database(DUCKDB_FILE, (err) => {
    if (err) {
      logMessage('ERROR', `Failed to open/create DuckDB database at ${DUCKDB_FILE}: ${err.message}`, 'duckdbInit');
      process.exit(1); // Critical error, cannot proceed
    }
    logMessage('INFO', `DuckDB database opened/created at ${DUCKDB_FILE}`, 'duckdbInit');
  });

  conn = db.connect();

  const createTableQuery = `
    CREATE TABLE IF NOT EXISTS ${DUCKDB_TABLE_NAME} (
      timestamp TIMESTAMPTZ,
      url VARCHAR,
      ibge_code VARCHAR,
      performance FLOAT,
      accessibility FLOAT,
      seo FLOAT,
      bestPractices FLOAT,
      PRIMARY KEY (url, timestamp)
    );
  `;
  // Using PRIMARY KEY (url, timestamp) to allow multiple records for the same URL over time,
  // but prevent exact duplicate entries for the same URL at the exact same microsecond.

  return new Promise((resolve, reject) => {
    conn.run(createTableQuery, (err) => {
      if (err) {
        logMessage('ERROR', `Failed to create table ${DUCKDB_TABLE_NAME}: ${err.message}`, 'duckdbInit');
        reject(err);
      } else {
        logMessage('INFO', `Table ${DUCKDB_TABLE_NAME} is ready (created if not exists).`, 'duckdbInit');
        resolve();
      }
    });
  });
}

// Function to close DuckDB connection
async function closeDuckDB() {
  return new Promise((resolve, reject) => {
    if (conn) {
      conn.close((err) => {
        if (err) {
          logMessage('ERROR', `Error closing DuckDB connection: ${err.message}`, 'duckdbClose');
          return reject(err);
        }
        logMessage('INFO', 'DuckDB connection closed.', 'duckdbClose');
        if (db) {
          db.close((err_db) => {
            if (err_db) {
              logMessage('ERROR', `Error closing DuckDB database: ${err_db.message}`, 'duckdbClose');
              return reject(err_db);
            }
            logMessage('INFO', 'DuckDB database closed.', 'duckdbClose');
            resolve();
          });
        } else {
          resolve();
        }
      });
    } else {
      resolve();
    }
  });
}


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

// Function to insert a result into DuckDB
async function insertResultToDuckDB(resultObj) {
  const { timestamp, url, ibge_code, performance, accessibility, seo, bestPractices } = resultObj;
  const insertQuery = `
    INSERT INTO ${DUCKDB_TABLE_NAME} (timestamp, url, ibge_code, performance, accessibility, seo, bestPractices)
    VALUES (?, ?, ?, ?, ?, ?, ?);
  `;
  return new Promise((resolve, reject) => {
    conn.run(insertQuery, [timestamp, url, ibge_code, performance, accessibility, seo, bestPractices], (err) => {
      if (err) {
        // Log error, but don't let it stop the entire process for other URLs.
        // The error might be due to constraint violation if somehow a duplicate is attempted,
        // or other DB issues.
        logMessage('ERROR', `Failed to insert result for ${url} into DuckDB: ${err.message}`, 'duckdbInsert');
        reject(err); // Reject so the calling function knows there was an issue with this specific insert
      } else {
        logMessage('DEBUG', `Result for ${url} inserted into DuckDB.`, 'duckdbInsert');
        resolve();
      }
    });
  });
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
  if (res.status >= 500) {
    throw new Error(`Server error ${res.status}`);
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

// Wrapper to retry PSI fetches on transient errors
async function fetchPSIWithRetry(url, fetchFn, maxRetries = 2, baseDelay = 1000) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fetchFn(url);
    } catch (err) {
      const retryable =
        err.message === 'Rate limit' ||
        err.message.startsWith('Server error') ||
        err.message.toLowerCase().includes('network');
      if (retryable && attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt);
        logMessage('WARNING', `Retrying ${url} in ${delay}ms due to ${err.message} (attempt ${attempt + 1}/${maxRetries})`, 'retry');
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
  // const outputJsonFile = isTestMode ? 'data/test-psi-results.json' : 'data/psi-results.json'; // No longer primary output
  // const outputCsvFile = isTestMode ? 'data/test-psi-results.csv' : 'data/psi-results.csv'; // No longer primary output

  const outDir = path.dirname(DUCKDB_FILE); // Ensure data directory exists for DuckDB file
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });


  logMessage('INFO', `Running in ${isTestMode ? 'TEST' : 'PRODUCTION'} mode. Input: ${inputCsvFile}, Output DB: ${DUCKDB_FILE}`, 'init');

  await initDuckDB(); // Initialize DuckDB

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
  const concurrency = parseInt(process.env.PSI_CONCURRENCY || '4', 10);
  const requestsPerMin = parseInt(process.env.PSI_REQUESTS_PER_MIN || '60', 10);
  const limit = pLimit(concurrency);
  const throttle = pThrottle({ limit: requestsPerMin, interval: 60000 });

  const throttledFetch = throttle((url) => fetchPSIWithRetry(url, fetchPSI, maxRetries, retryDelay));

  // const results = []; // No longer accumulating in memory for JSON/CSV
  let processedInThisRunCount = 0;

  // let existingResults = []; // No longer needed for JSON output
  // if (fs.existsSync(outputJsonFile)) {
  //   try {
  //     existingResults = JSON.parse(fs.readFileSync(outputJsonFile, 'utf-8'));
  //   } catch (err) {
  //     logMessage('WARNING', `Error reading existing results from ${outputJsonFile}: ${err.message}`, 'loadResults');
  //     existingResults = [];
  //   }
  // }

  logMessage('INFO', `Starting concurrent processing of ${urlsToProcess.length} URLs with concurrency ${concurrency}.`, 'mainLoop');
  const tasks = urlsToProcess.map(url => limit(async () => {
    const elapsedTime = Date.now() - scriptStartTime;
    if (elapsedTime >= SCRIPT_TIMEOUT_MS) {
      logMessage('INFO', `Time limit approaching. Skipping ${url}.`, 'timeout');
      return;
    }

    const attemptTimestamp = new Date().toISOString();
    if (!processingState[url]) {
      processingState[url] = { last_attempt: attemptTimestamp, last_success: null };
    } else {
      processingState[url].last_attempt = attemptTimestamp;
    }
    saveProcessingState(processingState, PROCESSING_STATE_FILE);

    try {
      const data = await throttledFetch(url);
      logMessage('INFO', `✅ ${url} → ${data.performance}`, 'fetchPSISuccess');
      const resultObj = { ...data, ibge_code: urlToIbge[url] };
      // results.push(resultObj); // No longer accumulating in memory
      try {
        await insertResultToDuckDB(resultObj);
        processedInThisRunCount++;
        processingState[url].last_success = new Date().toISOString();
        // persistResult(resultObj, outputJsonFile, existingResults); // Removed
      } catch (dbErr) {
        // Error already logged by insertResultToDuckDB, just note that this specific URL's success state won't be updated
        logMessage('WARNING', `Result for ${url} not marked as success in state file due to DB insert error.`, 'mainLoop');
      }
      saveProcessingState(processingState, PROCESSING_STATE_FILE); // Save state regardless of DB insert outcome for this particular URL
    } catch (err) {
      logMessage('ERROR', `Error for URL ${url}: ${err.message}`, 'fetchPSI');
      // Note: processingState for last_attempt was already saved before try block
      // No need to save processingState here again unless an error in throttledFetch should clear last_success
    }
  }));

  await Promise.all(tasks);

  logMessage('INFO', `Processed ${processedInThisRunCount} URLs in this run.`, 'summary');
  // writeCsvFile(existingResults, outputCsvFile); // Removed
  saveProcessingState(processingState, PROCESSING_STATE_FILE); // Final save of processing state
  await closeDuckDB(); // Close DuckDB connection
  logMessage('INFO', 'PSI data collection script finished.', 'main');
}

// This allows the script to still be run directly using `node collect-psi.js`
if (process.argv[1] && process.argv[1].endsWith('collect-psi.js')) {
  (async () => {
    try {
      await runMainLogic(process.argv, process.env.PSI_KEY);
    } catch (e) {
      logMessage('ERROR', `Unhandled error in main execution: ${e.message}`, 'mainCrash');
      await closeDuckDB(); // Attempt to close DB even on crash
      process.exit(1);
    }
  })();
}
