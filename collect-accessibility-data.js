const fs = require('fs');
const lighthouse = require('lighthouse');
const chromeLauncher = require('chrome-launcher');
const csv = require('csv-parser');

async function main() {
  const results = [];
  const inputFile = 'sites_das_prefeituras_brasileiras.csv';
  let urlCounter = 0;
  const urlLimit = 3; // Limit for this initial script

  // Ensure accessibility-results.json is an empty array at the start
  fs.writeFileSync('accessibility-results.json', '[]', 'utf8');

  const rows = [];
  fs.createReadStream(inputFile)
    .pipe(csv())
    .on('data', (row) => {
      rows.push(row);
    })
    .on('end', async () => {
      console.log(`CSV file successfully processed. Found ${rows.length} rows.`);
      for (const row of rows) {
        if (urlCounter >= urlLimit) {
          console.log(`Reached URL limit of ${urlLimit}. Stopping further processing.`);
          break; 
        }

        const url = row.url;
        const nome = row.nome;
        const uf = row.uf;
        const codigo_ibge = row.codigo_ibge;

        if (!url || url.trim() === '') {
          console.log(`Skipping empty URL for ${nome} (IBGE: ${codigo_ibge})`);
          continue;
        }

        // This check is crucial to ensure we only process `urlLimit` URLs
        // urlCounter is incremented only when we attempt an audit
        console.log(`Processing URL #${urlCounter + 1}/${urlLimit}: ${url} for ${nome}`);
        try {
          const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'] });
          const options = {
            logLevel: 'info', // 'info' or 'silent' are good options
            output: 'json',
            onlyCategories: ['accessibility'],
            port: chrome.port,
            // formFactor: 'desktop', // or 'mobile'
            // screenEmulation: { mobile: false, width: 1366, height: 768, deviceScaleFactor: 1, disabled: false},
          };
          const runnerResult = await lighthouse(url, options);
          const accessibilityScore = Math.round(runnerResult.lhr.categories.accessibility.score * 100);
          
          results.push({
            codigo_ibge: codigo_ibge,
            nome_municipio: nome,
            uf: uf,
            url: url,
            accessibility_score: accessibilityScore,
            audit_timestamp: new Date().toISOString(),
          });

          console.log(`Successfully audited ${url}. Score: ${accessibilityScore}`);
          await chrome.kill();
          urlCounter++; // Increment after successful processing and kill

        } catch (error) {
          console.error(`Error auditing ${url} for ${nome} (IBGE: ${codigo_ibge}):`, error.message);
          results.push({
            codigo_ibge: codigo_ibge,
            nome_municipio: nome,
            uf: uf,
            url: url,
            accessibility_score: null, // Indicate failure
            error_message: error.message.substring(0, 200), // Store a snippet of the error
            audit_timestamp: new Date().toISOString(),
          });
          // We still increment urlCounter here because an attempt was made.
          // If we only want to count successful audits towards the limit, move increment into try.
          urlCounter++; 
        }
      }

      fs.writeFileSync('accessibility-results.json', JSON.stringify(results, null, 2), 'utf8');
      console.log(`Finished processing. Results saved to accessibility-results.json. Processed ${urlCounter} URLs.`);
      if (results.length === 0 && urlLimit > 0) {
          console.warn("Warning: No results were written. Check stream handling and async operations if URLs were expected to be processed.");
      } else if (urlCounter < urlLimit && rows.length > 0) {
          console.warn(`Warning: Processed ${urlCounter} URLs, which is less than the intended limit of ${urlLimit}. This might be due to empty URLs, errors during processing, or end of file before reaching the limit.`);
      }
    });
}

main().catch(error => {
  console.error("An error occurred in the main function:", error);
  // Ensure results are written even if main crashes, if any results were collected.
  // This part might need refinement based on where `results` is accessible.
  // For now, the main function's own .on('end') handles writing.
});
