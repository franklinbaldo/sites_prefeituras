// collect-psi.js
import fs from 'fs';
import path from 'path';
import fetch from 'node-fetch';
import pLimit from 'p-limit';
import { parse as csvParse } from 'csv-parse/sync';

let API_KEY = process.env.PSI_KEY; // Made non-const to allow modification in tests

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

  const isTestMode = argv.includes('--test');
  const inputCsvFile = isTestMode ? 'test_sites.csv' : 'sites_das_prefeituras_brasileiras.csv';
  const outputJsonFile = isTestMode ? 'data/test-psi-results.json' : 'data/psi-results.json';

  console.log(`ℹ️ Running in ${isTestMode ? 'TEST' : 'PRODUCTION'} mode.`);
  console.log(`ℹ️ Reading URLs from: ${inputCsvFile}`);

  let urlsToProcess;
  try {
    const csv = fs.readFileSync(inputCsvFile, 'utf-8'); // fs will be mocked in tests
    const rows = csvParse(csv, { columns: true, skip_empty_lines: true });
    urlsToProcess = rows.map(r => r['Endereço Eletrônico']).filter(u => u && u.startsWith('http'));
  } catch (err) {
    console.error(`❌ Erro ao ler ou processar o arquivo CSV ${inputCsvFile}: ${err.message}`);
    // In a real scenario, might want to process.exit(1) here too, or handle more gracefully
    return; // Exit function if CSV processing fails
  }
  
  console.log(`ℹ️ Writing results to: ${outputJsonFile}`);

  // Use externalFetchPSI if provided (for unit tests), otherwise choose based on mode
  const fetchPSI = externalFetchPSI 
    ? externalFetchPSI
    : isTestMode 
      ? scriptMockFetchPSI 
      : (url) => originalFetchPSI(url, API_KEY, fetch); // Pass API_KEY and global fetch

  const limit = pLimit(4);
  const results = [];
  const tasks = urlsToProcess.map(url =>
    limit(async () => {
      try {
        const data = await fetchPSI(url);
        console.log(`✅ ${url} → ${data.performance}`);
        results.push(data);
      } catch (err) {
        console.warn(`❌ erro em ${url}: ${err.message}`);
      }
    })
  );
  await Promise.all(tasks);

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
