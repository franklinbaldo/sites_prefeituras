// collect-psi.js
import fs from 'fs';
import path from 'path';
import fetch from 'node-fetch';
import { parse as csvParse } from 'csv-parse/sync';
import pLimit from 'p-limit';
import pThrottle from 'p-throttle';
import duckdb from 'duckdb';

// --- Configuration Loading ---
// Call loadConfiguration early to set up SCRIPT_CONFIG, API_KEY, and resolved file paths.
// logMessage can be used by loadConfiguration itself if needed for errors during loading.
const CONFIG_FILE_PATH = path.resolve(process.cwd(), 'psi-collector-config.json');

// Global config object, will be populated by loadConfiguration
let SCRIPT_CONFIG = {};

// To be set by loadConfiguration from SCRIPT_CONFIG or environment variables
let API_KEY;

// File path variables, will be set by loadConfiguration by resolving paths from SCRIPT_CONFIG
let ERROR_LOG_FILE;
let PROCESSING_STATE_FILE;
let DUCKDB_FILE_PATH;
const DUCKDB_TABLE_NAME = 'psi_metrics'; // Likely to remain constant

// DuckDB database instance and connection
let db; // Global db instance for the main script execution
let conn; // Global connection for the main script execution

function loadConfiguration(configFilePath) {
  // Default config used if file is missing or parsing fails
  const defaultConfig = {
    "psi_api_key_env_var": "PSI_KEY",
    "psi_api_categories": ["performance", "accessibility", "best-practices", "seo"],
    psi_requests_per_min": 60,
    psi_concurrency": 4,
    psi_max_retries": 2,
    psi_retry_delay_ms": 1000,
    psi_debug_log_env_var": "PSI_DEBUG_LOG", // Name of env var for debug logging
    input_csv_file": "sites_das_prefeituras_brasileiras.csv",
    test_input_csv_file": "test_sites.csv",
    duckdb_file": "data/psi_results.duckdb",
    processing_state_file": "data/psi_processing_state.json",
    error_log_file": "psi_errors.log",
    strategies_to_run": ["mobile", "desktop"]
  };

  try {
    if (fs.existsSync(configFilePath)) {
      const rawConfig = fs.readFileSync(configFilePath, 'utf-8');
      SCRIPT_CONFIG = JSON.parse(rawConfig);
      logMessage('INFO', `Loaded configuration from ${configFilePath}`, 'configLoad');
    } else {
      SCRIPT_CONFIG = defaultConfig;
      logMessage('WARNING', `Configuration file ${configFilePath} not found. Using default script configuration.`, 'configLoad');
    }
  } catch (err) {
    SCRIPT_CONFIG = defaultConfig;
    logMessage('ERROR', `Error loading or parsing configuration file ${configFilePath}: ${err.message}. Using default script configuration.`, 'configLoad');
  }

  // Override file paths from config if they exist, then resolve them
  ERROR_LOG_FILE = path.resolve(process.cwd(), SCRIPT_CONFIG.error_log_file || 'psi_errors.log');
  PROCESSING_STATE_FILE = path.resolve(process.cwd(), SCRIPT_CONFIG.processing_state_file || 'data/psi_processing_state.json');
  DUCKDB_FILE_PATH = path.resolve(process.cwd(), SCRIPT_CONFIG.duckdb_file || 'data/psi_results.duckdb');

  // Set API_KEY from environment variable specified in config
  API_KEY = process.env[SCRIPT_CONFIG.psi_api_key_env_var || "PSI_KEY"];

  // Set PSI_DEBUG_LOG based on environment variable specified in config
  // This is to ensure logMessage works correctly even before full config is processed by runMainLogic
  if (process.env[SCRIPT_CONFIG.psi_debug_log_env_var || "PSI_DEBUG_LOG"] === 'true') {
    process.env.PSI_DEBUG_LOG = 'true'; // Ensure the global env var used by logMessage is set
  }
}
loadConfiguration(CONFIG_FILE_PATH); // Initialize configuration

// Function to initialize DuckDB and create table if it doesn't exist
// Accepts an optional existing connection for testability
export async function initDuckDB(existingConnection = null) {
  if (existingConnection) {
    conn = existingConnection;
    logMessage('INFO', 'Using existing DuckDB connection for init.', 'duckdbInit');
    // db remains null or undefined if only a connection is passed.
    // This is fine if the connection is already tied to an in-memory DB for tests.
  } else {
    // Use DUCKDB_FILE_PATH which is now resolved
    db = new duckdb.Database(DUCKDB_FILE_PATH, (err) => {
      if (err) {
        logMessage('ERROR', `Failed to open/create DuckDB database at ${DUCKDB_FILE_PATH}: ${err.message}`, 'duckdbInit');
        // In tests, process.exit might be mocked or handled.
        // For production, this is a critical failure.
        if (typeof process !== 'undefined' && process.exit) process.exit(1);
        else throw err; // if process.exit is not available (e.g. some test environments)
      }
      logMessage('INFO', `DuckDB database opened/created at ${DUCKDB_FILE_PATH}`, 'duckdbInit');
    });
    conn = db.connect();
  }

  const createTableQuery = `
    CREATE TABLE IF NOT EXISTS ${DUCKDB_TABLE_NAME} (
      timestamp TIMESTAMPTZ,
      url VARCHAR,
      ibge_code VARCHAR,
      strategy VARCHAR, -- Added strategy column
      performance FLOAT,
      accessibility FLOAT,
      seo FLOAT,
      bestPractices FLOAT,
      PRIMARY KEY (url, timestamp, strategy) -- Updated primary key
    );
  `;
  // Using PRIMARY KEY (url, timestamp, strategy) to allow records for both mobile and desktop
  // for the same URL and timestamp, preventing exact duplicates.

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
// Now accepts dbConnection for testability
export async function insertResultToDuckDB(resultObj, dbConnection) {
  const { timestamp, url, ibge_code, strategy, performance, accessibility, seo, bestPractices } = resultObj;
  const insertQuery = `
    INSERT INTO ${DUCKDB_TABLE_NAME} (timestamp, url, ibge_code, strategy, performance, accessibility, seo, bestPractices)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
  `;
  return new Promise((resolve, reject) => {
    dbConnection.run(insertQuery, [timestamp, url, ibge_code, strategy, performance, accessibility, seo, bestPractices], (err) => {
      if (err) {
        // Log error, but don't let it stop the entire process for other URLs.
        // The error might be due to constraint violation if somehow a duplicate is attempted for the same (url, timestamp, strategy)
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

  // File Logging
  // True ERRORS go to ERROR_LOG_FILE for critical error tracking by workflow
  if (upperLevel === 'ERROR') {
    appendMessageToFile(ERROR_LOG_FILE, fileMessage);
  }
  // Optionally, log INFO, WARNING, ERROR to a more comprehensive activity log
  // if (['INFO', 'WARNING', 'ERROR'].includes(upperLevel)) {
  //   appendMessageToFile(ACTIVITY_LOG_FILE, fileMessage);
  // }
}

// Generic function to append pre-formatted messages to a specified log file
function appendMessageToFile(logFilePath, formattedMessage) {
  try {
    fs.appendFileSync(logFilePath, formattedMessage + '\n');
  } catch (err) {
    // If logging to file fails, log to console as a fallback
    console.error(`Fallback: Failed to write to ${logFilePath}: ${err.message}`);
    console.error(`Fallback: Original message for ${logFilePath}: ${formattedMessage}`);
  }
}

// Custom error class for PSI specific errors
class PsiError extends Error {
  constructor(message, code, category, isRetryable = false) {
    super(message);
    this.name = "PsiError";
    this.code = code; // HTTP status code or custom error code
    this.category = category; // e.g., 'API_ERROR', 'LIGHTHOUSE_ERROR', 'NETWORK_ERROR'
    this.isRetryable = isRetryable;
  }
}

// This function will be unit tested
export async function originalFetchPSI(url, apiKey, fetchFn, strategy = 'mobile') {
  const categoriesQueryParam = (SCRIPT_CONFIG.psi_api_categories || ['performance', 'accessibility', 'best-practices', 'seo'])
    .map(cat => `&category=${cat}`)
    .join('');

  const endpoint = `https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed`
    + `?url=${encodeURIComponent(url)}`
    + `&strategy=${strategy}`
    + categoriesQueryParam
    + `&key=${apiKey}`;

  let res;
  try {
    res = await fetchFn(endpoint);
  } catch (networkErr) {
    // Handle fetch-specific network errors (e.g., DNS resolution, TCP connection)
    throw new PsiError(`Network error fetching PSI data for ${url}: ${networkErr.message}`, 'NETWORK_FAILURE', 'NETWORK_ERROR', true);
  }

  if (!res.ok) { // status is not in the range 200-299
    let errorJson;
    try {
      errorJson = await res.json();
    } catch (e) {
      // If parsing error JSON fails, use status text
      throw new PsiError(
        `PSI API request failed for ${url} with status ${res.status}: ${res.statusText}. Failed to parse error response.`,
        res.status,
        'API_ERROR',
        res.status === 429 || res.status >= 500 // Retry on rate limit or server errors
      );
    }
    const apiErrorMessage = errorJson?.error?.message || 'Unknown API error';
    const isRetryable = res.status === 429 || res.status >= 500; // Rate limit (429) or server errors (5xx)

    // Check for specific non-retryable client errors (4xx) based on message content if necessary
    // For example, if a URL is truly invalid (e.g., DNS lookup failed for the target URL)
    let category = 'API_ERROR';
    if (apiErrorMessage.includes('Lighthouse returned error: ERRORED_DOCUMENT_REQUEST') ||
        apiErrorMessage.includes('DNS_FAILURE')) {
      category = 'LIGHTHOUSE_ERROR_DOCUMENT_REQUEST'; // Specific category for unreachabale URLs
    }

    throw new PsiError(
      `PSI API error for ${url} (Status ${res.status}): ${apiErrorMessage}`,
      res.status,
      category,
      isRetryable
    );
  }

  const json = await res.json();

  // Validate the PSI response structure
  const lighthouseResult = json?.lighthouseResult;
  if (!lighthouseResult) {
    // This case might indicate a successful HTTP response but an unexpected payload structure
    throw new PsiError(`Invalid PSI response structure for ${url}: lighthouseResult missing.`, 'INVALID_RESPONSE', 'API_ERROR', false);
  }

  const categories = lighthouseResult?.categories;
  if (!categories) {
    // Check if Lighthouse itself reported an error within a successful response
    const runtimeError = lighthouseResult?.runtimeError;
    if (runtimeError && runtimeError.code) {
      throw new PsiError(
        `Lighthouse runtime error for ${url}: ${runtimeError.message} (Code: ${runtimeError.code})`,
        runtimeError.code,
        'LIGHTHOUSE_RUNTIME_ERROR',
        false // Usually, specific Lighthouse errors are not retryable unless it's a timeout that we might want to retry.
      );
    }
    throw new PsiError(`Invalid PSI response structure for ${url}: categories missing.`, 'INVALID_RESPONSE_CATEGORIES', 'API_ERROR', false);
  }

  return {
    url,
    strategy, // Include strategy in the result
    performance: cat.performance?.score ?? null,
    accessibility: cat.accessibility?.score ?? null,
    seo: cat.seo?.score ?? null,
    bestPractices: cat['best-practices']?.score ?? null,
    timestamp: new Date().toISOString(),
  };
}

// This is the script's own mock, used when run with --test directly
// Now needs to accept strategy
async function scriptMockFetchPSI(url, strategy = 'mobile') {
  logMessage('DEBUG', `SCRIPT MOCK fetchPSI called for: ${url} with strategy: ${strategy}`, 'mockFetchPSI');
  if (url === 'http://example.com' || url === 'http://another-example.com') {
    return {
      url,
      strategy,
      performance: strategy === 'mobile' ? 0.9 : 0.85, // Slightly different scores for mock
      accessibility: strategy === 'mobile' ? 0.8 : 0.75,
      seo: strategy === 'mobile' ? 0.7 : 0.65,
      bestPractices: strategy === 'mobile' ? 0.95 : 0.90,
      timestamp: new Date().toISOString()
    };
  } else if (url === 'http://invalid-url-that-does-not-exist-hopefully.com') {
    throw new PsiError('Simulated fetch error for non-existent URL', 'MOCK_FETCH_ERROR', 'NETWORK_ERROR', true);
  } else {
    throw new PsiError(`Script Mock PSI fetch not defined for URL: ${url} and strategy: ${strategy}`, 'MOCK_UNDEFINED', 'INTERNAL_MOCK_ERROR', false);
  }
}

// Wrapper to retry PSI fetches on transient errors
// Now needs to pass strategy to fetchFn
async function fetchPSIWithRetry(url, strategy, fetchFn, maxRetries = 2, baseDelay = 1000) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fetchFn(url, strategy); // Pass strategy to the actual fetch function
    } catch (err) {
      // Check if it's a PsiError and if it's marked as retryable
      // Also, ensure we haven't exceeded maxRetries
      if (err instanceof PsiError && err.isRetryable && attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt);
        logMessage(
          'WARNING',
          `Retrying ${url} in ${delay}ms due to ${err.category} (Code: ${err.code}, Attempt: ${attempt + 1}/${maxRetries}): ${err.message}`,
          'retry'
        );
        await new Promise(res => setTimeout(res, delay));
      } else if (err instanceof PsiError) {
        // Non-retryable PsiError or max retries reached
        logMessage(
          'ERROR',
          `Non-retryable error or max retries reached for ${url} after ${attempt +1} attempts (Category: ${err.category}, Code: ${err.code}): ${err.message}`,
          'fetchPSI'
        );
        throw err; // Re-throw the original PsiError
      } else {
        // Generic error, not a PsiError (e.g., programming error in fetchFn itself)
        logMessage('ERROR', `Generic error during fetch/retry for ${url}: ${err.message}`, 'retry');
        throw err; // Re-throw as is
      }
    }
  }
  // Should not be reached if maxRetries is > 0, as the loop would throw.
  // If maxRetries is 0, the first error would throw.
  // Adding a safeguard throw in case logic changes.
  throw new Error(`fetchPSIWithRetry exhausted retries for ${url} or encountered an unhandled error.`);
}

// Exported for testing
export async function loadAndPrioritizeUrls(inputCsvFile, processingState, fsUtils, isTestMode = false) {
  let allCsvUrls;
  let urlToIbgeMap = {}; // Changed name for clarity

  try {
    const csv = fsUtils.readFileSync(inputCsvFile, 'utf-8');
    const rows = fsUtils.parse(csv, { columns: true, skip_empty_lines: true });

    const sample = rows[0] || {};
    let urlField = Object.keys(sample).find(k => k.toLowerCase().includes('url'));
    if (!urlField) {
      urlField = Object.keys(sample).find(k => k.toLowerCase().includes('endere'));
    }
    const ibgeField = Object.keys(sample).find(k => k.toLowerCase().includes('ibge'));

    if (!urlField || !ibgeField) {
      logMessage('ERROR', `Could not determine URL or IBGE field from CSV headers: ${Object.keys(sample).join(', ')}`, 'readCsvFile');
      return { urlsToProcess: null, urlToIbgeMap: null }; // Critical error
    }

    allCsvUrls = [];
    for (const row of rows) {
      const url = row[urlField];
      const ibge = row[ibgeField];
      if (url && url.startsWith('http')) {
        allCsvUrls.push(url);
        urlToIbgeMap[url] = ibge;
      }
    }
    logMessage('INFO', `Loaded ${allCsvUrls.length} URLs from ${inputCsvFile} after initial filter.`, 'readCsvFile');

    if (allCsvUrls.length === 0) {
      logMessage('WARNING', `No valid URLs (http/https) found in ${inputCsvFile}.`, 'readCsvFile');
    }
  } catch (err) {
    let detailedMessage = `Error reading or processing CSV file ${inputCsvFile}: ${err.message}`;
    // Check if the error is from csv-parse and has specific properties
    // `err.code` from CsvError is a string like 'CSV_INVALID_RECORD_LENGTH'
    // `err.lineNumber` is also available from csv-parse errors (using default 'lines' for generic errors)
    if (typeof err.code === 'string' && err.code.startsWith('CSV_')) {
        detailedMessage = `Error parsing CSV file ${inputCsvFile} near line ${err.lineNumber || err.lines || 'N/A'}. CSV Error Code: ${err.code}. Message: ${err.message}`;
        if(err.record) {
            const recordSnippet = Array.isArray(err.record) ? err.record.join(',') : String(err.record);
            detailedMessage += ` Faulty record snippet: ${recordSnippet.substring(0, 200)}`;
        }
    } else if (err.code === 'ENOENT') { // File not found error from fs.readFileSync
        detailedMessage = `CSV input file not found: ${inputCsvFile}. Message: ${err.message}`;
    }
    // else, it's a generic error, the initial detailedMessage with err.message is used.

    if (isTestMode && inputCsvFile.includes(SCRIPT_CONFIG.test_input_csv_file || 'test_sites.csv')) {
        logMessage('WARNING', `[TEST MODE] ${detailedMessage}`, 'readCsvFile');
    } else {
        logMessage('ERROR', detailedMessage, 'readCsvFile');
    }
    return { urlsToProcess: null, urlToIbgeMap: null }; // Critical error
  }

  let urlsToProcess = [];
  if (allCsvUrls && allCsvUrls.length > 0) {
    urlsToProcess = allCsvUrls.map(url => {
      const stateEntry = processingState[url];
      let lastAttemptDate = new Date(0);
      if (stateEntry && stateEntry.last_attempt) {
        const parsedDate = new Date(stateEntry.last_attempt);
        if (!isNaN(parsedDate)) {
          lastAttemptDate = parsedDate;
        } else {
          logMessage('WARNING', `Invalid last_attempt date for ${url}: "${stateEntry.last_attempt}". Treating as new/very old.`, 'urlPrioritization');
        }
      }
      return { url: url, last_attempt: lastAttemptDate };
    })
    .sort((a, b) => a.last_attempt - b.last_attempt)
    .map(item => item.url);

    if (urlsToProcess.length > 0) {
      logMessage('INFO', `Prioritized ${urlsToProcess.length} URLs. Oldest attempts first.`, 'urlPrioritization');
      logMessage('DEBUG', `Top URLs in queue: ${urlsToProcess.slice(0, 5).join(', ')}`, 'urlPrioritization');
    }
  }

  if (urlsToProcess.length === 0 && allCsvUrls.length > 0) {
      logMessage('INFO', 'No URLs to process after filtering and prioritization (e.g. if all were processed recently and list is empty).', 'urlPrioritization');
  } else if (urlsToProcess.length === 0 && allCsvUrls.length === 0) {
      logMessage('INFO', 'No URLs loaded from CSV, so no URLs to process.', 'urlPrioritization');
  }


  return { urlsToProcess, urlToIbgeMap };
}


// Main logic of the script, now exportable and testable
export async function runMainLogic(argv, currentApiKey, externalFetchPSI) {
  logMessage('DEBUG', `Running with argv: ${JSON.stringify(argv)}`, 'init'); // Log argv
  const isTestMode = argv.includes('--test');
  if (isTestMode) {
    logMessage('INFO', 'Script is running in TEST MODE (--test flag detected).', 'init');
  }

  logMessage('INFO', 'PSI data collection script started.', 'main');
  API_KEY = currentApiKey; // Update API_KEY from parameter for testability
  if (!API_KEY) {
    logMessage('ERROR', 'PSI_KEY environment variable is NOT SET.', 'init');
    process.exit(1); // This will be mocked in tests
  } else {
    logMessage('INFO', 'PSI_KEY environment variable is set.', 'init');
  }

  const scriptStartTime = Date.now(); // Keep for elapsed time calculations if ever needed, but not for timeout enforcement here.

  // const SCRIPT_TIMEOUT_MS = 9.5 * 60 * 1000; // 9.5 minutes - REMOVED, defer to workflow timeout

  const baseDir = process.cwd(); // Still useful for context if needed elsewhere
  const inputCsvFile = isTestMode
      ? path.resolve(baseDir, SCRIPT_CONFIG.test_input_csv_file || 'test_sites.csv')
      : path.resolve(baseDir, SCRIPT_CONFIG.input_csv_file || 'sites_das_prefeituras_brasileiras.csv');

  // DUCKDB_FILE_PATH, PROCESSING_STATE_FILE, ERROR_LOG_FILE are now set globally by loadConfiguration
  // Ensure parent directory for DuckDB file exists
  const outDir = path.dirname(DUCKDB_FILE_PATH);
  if (!fs.existsSync(outDir)) {
    try {
      fs.mkdirSync(outDir, { recursive: true });
      logMessage('INFO', `Created output directory: ${outDir}`, 'init');
    } catch (err) {
      logMessage('ERROR', `Failed to create output directory ${outDir}: ${err.message}`, 'init');
      // This might be a critical error, consider exiting or throwing
      if (typeof process !== 'undefined' && process.exit) process.exit(1);
      else throw err;
    }
  }

  logMessage('INFO', `Input: ${inputCsvFile}, Output DB: ${DUCKDB_FILE_PATH}`, 'init');

  await initDuckDB(); // Initialize DuckDB (uses global DUCKDB_FILE_PATH)

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

  // --- Refactored URL Loading and Prioritization ---
  const { urlsToProcess, urlToIbgeMap } = await loadAndPrioritizeUrls(
    inputCsvFile, // This is already resolved
    processingState,
    { readFileSync: fs.readFileSync, parse: csvParse }, // Inject dependencies
    isTestMode
  );

  if (urlsToProcess === null) { // Indicates a critical error during URL loading
    await closeDuckDB();
    return; // Exit or throw as appropriate for workflow
  }
  // --- End of Refactored URL Loading ---

  // Use externalFetchPSI if provided (for unit tests), otherwise choose based on mode
  const fetchPSI = externalFetchPSI
    ? externalFetchPSI
    : isTestMode
      ? scriptMockFetchPSI // scriptMockFetchPSI now also accepts strategy
      : (url, strategy) => originalFetchPSI(url, API_KEY, fetch, strategy);

  // Get settings from SCRIPT_CONFIG, with defaults from process.env or hardcoded as fallback
  const maxRetries = parseInt(process.env.PSI_MAX_RETRIES || SCRIPT_CONFIG.psi_max_retries || '2', 10);
  const retryDelay = parseInt(process.env.PSI_RETRY_DELAY_MS || SCRIPT_CONFIG.psi_retry_delay_ms || '1000', 10);
  const concurrency = parseInt(process.env.PSI_CONCURRENCY || SCRIPT_CONFIG.psi_concurrency || '4', 10);
  const requestsPerMin = parseInt(process.env.PSI_REQUESTS_PER_MIN || SCRIPT_CONFIG.psi_requests_per_min || '60', 10);

  const limit = pLimit(concurrency);
  const throttle = pThrottle({ limit: requestsPerMin, interval: 60000 });

  const throttledFetch = throttle((url, strategy) => fetchPSIWithRetry(url, strategy, fetchPSI, maxRetries, retryDelay));

  let processedInThisRunCount = 0;
  const strategiesToRun = SCRIPT_CONFIG.strategies_to_run || ['mobile', 'desktop'];

  logMessage('INFO', `Starting processing for ${urlsToProcess.length} URLs, each with strategies: ${strategiesToRun.join(', ')}. Concurrency: ${concurrency}, RPM: ${requestsPerMin}.`, 'mainLoop');

  const tasks = [];
  for (const url of urlsToProcess) {
    for (const strategy of strategiesToRun) {
      tasks.push(limit(async () => {
        // Update processing state keyed by URL and strategy, or just URL if state is strategy-agnostic for attempts
        // For simplicity, let's assume last_attempt on processingState[url] covers both.
        // More granular state could be processingState[url][strategy].last_attempt if needed.
        const attemptTimestamp = new Date().toISOString();
        if (!processingState[url]) {
          // Initialize if new URL, or if we want strategy-specific state:
          // processingState[url] = { mobile: {last_attempt: null, ...}, desktop: {last_attempt: null, ...}};
          processingState[url] = { last_attempt: attemptTimestamp, last_success_mobile: null, last_success_desktop: null };
        } else {
          processingState[url].last_attempt = attemptTimestamp; // General last attempt for the URL
        }
        // Consider saving state less frequently, e.g., after both strategies for a URL, or batch saves.
        // For now, save on each attempt for robustness.
        saveProcessingState(processingState, PROCESSING_STATE_FILE);

        try {
          logMessage('DEBUG', `Fetching ${strategy} PSI for ${url}`, 'mainLoopTask');
          const data = await throttledFetch(url, strategy); // Pass strategy here
          logMessage('INFO', `✅ ${strategy} for ${url} → Performance: ${data.performance}`, 'fetchPSISuccess');

          const resultObj = { ...data, ibge_code: urlToIbgeMap[url] }; // Use urlToIbgeMap, 'strategy' is already in 'data'

          await insertResultToDuckDB(resultObj, conn); // Pass the global conn
          processedInThisRunCount++;

          // Update last_success state, now strategy-specific
          if (strategy === 'mobile') {
            processingState[url].last_success_mobile = new Date().toISOString();
          } else if (strategy === 'desktop') {
            processingState[url].last_success_desktop = new Date().toISOString();
          }
          saveProcessingState(processingState, PROCESSING_STATE_FILE);

        } catch (err) {
          // err should be a PsiError instance from fetchPSIWithRetry/originalFetchPSI
          // The error message from PsiError already contains details.
          logMessage('ERROR', `Failed ${strategy} for ${url}: ${err.message}`, 'fetchPSIError');
          // Note: processingState for last_attempt was already saved.
          // If an error occurs, last_success for this strategy won't be updated.
        }
      }));
    }
  }

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
