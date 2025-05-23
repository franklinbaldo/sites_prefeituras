// collect-psi.js
import fs from 'fs';
import path from 'path';
import fetch from 'node-fetch';
import pLimit from 'p-limit';
import csvParse from 'csv-parse/lib/sync';

const API_KEY = process.env.PSI_KEY;
if (!API_KEY) {
  console.error('⚠️ Defina a variável de ambiente PSI_KEY');
  process.exit(1);
}

// lê CSV e extrai as URLs (supondo que estejam na 4ª coluna)
const csv = fs.readFileSync('sites_das_prefeituras_brasileiras.csv', 'utf-8');
const rows = csvParse(csv, { skip_empty_lines: true });
const urls = rows.map(r => r[3]).filter(u => u.startsWith('http'));

const limit = pLimit(4); // até ~4 requisições simultâneas

async function fetchPSI(url) {
  const endpoint = `https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed`
    + `?url=${encodeURIComponent(url)}`
    + `&strategy=mobile`
    + `&key=${API_KEY}`;
  const res = await fetch(endpoint);
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

(async () => {
  const results = [];
  const tasks = urls.map(url =>
    limit(async () => {
      try {
        const data = await fetchPSI(url);
        console.log(`✅ ${url} → ${data.performance}`);
        results.push(data);
      } catch (err) {
        console.warn(`❌ erro em ${url}: ${err.message}`);
        // aqui você poderia implementar retry com backoff
      }
    })
  );
  await Promise.all(tasks);

  // grava JSON
  const outDir = path.resolve('data');
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir);
  fs.writeFileSync(
    path.join(outDir, 'psi-results.json'),
    JSON.stringify(results, null, 2)
  );
  console.log(`💾 Gravados ${results.length} resultados em data/psi-results.json`);
})();
