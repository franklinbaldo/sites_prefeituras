#!/usr/bin/env node

import duckdb from 'duckdb';
import path from 'path';
import fs from 'fs';

// Attempt to load SCRIPT_CONFIG to get default DUCKDB_FILE_PATH
// This is a simplified version of collect-psi.js's config loader
let defaultDbPath = 'data/psi_results.duckdb'; // Fallback default
try {
    const configFilePath = path.resolve(process.cwd(), 'psi-collector-config.json');
    if (fs.existsSync(configFilePath)) {
        const rawConfig = fs.readFileSync(configFilePath, 'utf-8');
        const scriptConfig = JSON.parse(rawConfig);
        if (scriptConfig.duckdb_file) {
            defaultDbPath = scriptConfig.duckdb_file;
        }
    }
} catch (e) {
    console.warn(`Warning: Could not load psi-collector-config.json to get default DB path. Using '${defaultDbPath}'. Error: ${e.message}`);
}
const DUCKDB_FILE = path.resolve(process.cwd(), defaultDbPath);
const DUCKDB_TABLE_NAME = 'psi_metrics';


function printHelp() {
    console.log(`
Local PSI Data Analysis Script

Usage: node analyze_psi_data.js [options]

Options:
  --db <path>                Path to the DuckDB file (default: ${defaultDbPath})
  --summary                  Show a summary of the database (total records, latest timestamp, unique URLs).
  --avg-scores [strategy]    Calculate average scores. Strategy can be 'mobile', 'desktop', or 'all' (default).
  --list-worst <metric> <N> [strategy]
                             List the top N URLs with the worst score for a given metric
                             (performance, accessibility, seo, bestPractices).
                             Strategy can be 'mobile', 'desktop', or 'all' (default).
  --find-url <pattern>       Show all records for URLs containing the pattern (case-insensitive).
  --query <SQL>              Execute a custom SQL query.
  -h, --help                 Show this help message.

Examples:
  node analyze_psi_data.js --summary
  node analyze_psi_data.js --avg-scores mobile
  node analyze_psi_data.js --list-worst accessibility 10 desktop
  node analyze_psi_data.js --find-url "example.com"
  node analyze_psi_data.js --query "SELECT url, AVG(performance) as avg_perf FROM ${DUCKDB_TABLE_NAME} GROUP BY url ORDER BY avg_perf ASC LIMIT 5"
    `);
}

async function runQuery(db, sql, params = []) {
    return new Promise((resolve, reject) => {
        db.all(sql, ...params, (err, res) => {
            if (err) {
                reject(err);
            } else {
                resolve(res);
            }
        });
    });
}

function displayResults(results) {
    if (results.length === 0) {
        console.log("No results found.");
        return;
    }
    // Simple table display
    console.table(results);
}

async function main() {
    const args = process.argv.slice(2);

    if (args.includes('-h') || args.includes('--help') || args.length === 0) {
        printHelp();
        process.exit(0);
    }

    let dbFilePath = DUCKDB_FILE;
    const dbPathArgIndex = args.indexOf('--db');
    if (dbPathArgIndex > -1 && args[dbPathArgIndex + 1]) {
        dbFilePath = path.resolve(process.cwd(), args[dbPathArgIndex + 1]);
        args.splice(dbPathArgIndex, 2); // Remove --db and its value
    }

    if (!fs.existsSync(dbFilePath)) {
        console.error(`Error: Database file not found at ${dbFilePath}`);
        console.error(`Please specify a valid database path using --db <path> or ensure the default exists.`);
        process.exit(1);
    }

    const db = new duckdb.Database(dbFilePath, { access_mode: 'READ_ONLY' }, (err) => {
        if (err) {
            console.error(`Error connecting to database: ${err.message}`);
            process.exit(1);
        }
        console.log(`Connected to database: ${dbFilePath}`);
    });

    try {
        if (args.includes('--summary')) {
            console.log("\n--- Database Summary ---");
            const totalRecords = await runQuery(db, `SELECT COUNT(*) as count FROM ${DUCKDB_TABLE_NAME}`);
            const latestTimestamp = await runQuery(db, `SELECT MAX(timestamp) as latest_ts FROM ${DUCKDB_TABLE_NAME}`);
            const uniqueUrls = await runQuery(db, `SELECT COUNT(DISTINCT url) as unique_urls FROM ${DUCKDB_TABLE_NAME}`);
            console.log(`Total records: ${totalRecords[0].count}`);
            console.log(`Latest timestamp: ${latestTimestamp[0].latest_ts ? new Date(latestTimestamp[0].latest_ts).toISOString() : 'N/A'}`);
            console.log(`Unique URLs: ${uniqueUrls[0].unique_urls}`);
        } else if (args.includes('--avg-scores')) {
            console.log("\n--- Average Scores ---");
            let strategyFilter = args[args.indexOf('--avg-scores') + 1];
            if (!strategyFilter || strategyFilter.startsWith('--')) strategyFilter = 'all';

            let query;
            const params = [];
            if (strategyFilter === 'all') {
                query = `SELECT
                            'all' as strategy_summary,
                            ROUND(AVG(performance), 3) as avg_performance,
                            ROUND(AVG(accessibility), 3) as avg_accessibility,
                            ROUND(AVG(seo), 3) as avg_seo,
                            ROUND(AVG(bestPractices), 3) as avg_best_practices,
                            COUNT(*) as record_count
                         FROM ${DUCKDB_TABLE_NAME}`;
                // No WHERE clause, no GROUP BY needed for a single summary row
            } else {
                query = `SELECT
                            strategy,
                            ROUND(AVG(performance), 3) as avg_performance,
                            ROUND(AVG(accessibility), 3) as avg_accessibility,
                            ROUND(AVG(seo), 3) as avg_seo,
                            ROUND(AVG(bestPractices), 3) as avg_best_practices,
                            COUNT(*) as record_count
                         FROM ${DUCKDB_TABLE_NAME}
                         WHERE lower(strategy) = lower(?)
                         GROUP BY strategy`;
                params.push(strategyFilter);
            }
            const results = await runQuery(db, query, params);
            displayResults(results);
        } else if (args.includes('--list-worst')) {
            const metricIndex = args.indexOf('--list-worst') + 1;
            const nIndex = metricIndex + 1;
            const strategyIndex = nIndex + 1;

            const metric = args[metricIndex];
            const n = parseInt(args[nIndex], 10);
            let strategy = args[strategyIndex];

            if (!metric || !['performance', 'accessibility', 'seo', 'bestPractices'].includes(metric) || isNaN(n) || n <= 0) {
                console.error("Invalid arguments for --list-worst. Usage: --list-worst <metric> <N> [strategy]");
                printHelp();
                process.exit(1);
            }
            if (!strategy || strategy.startsWith('--')) strategy = 'all';

            console.log(`\n--- Top ${n} Worst Scores for ${metric} (Strategy: ${strategy}) ---`);
            // To get the latest record for each URL before ranking
            let query = `
                WITH LatestScores AS (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY url, strategy ORDER BY timestamp DESC) as rn
                    FROM ${DUCKDB_TABLE_NAME}
                    ${strategy !== 'all' ? "WHERE lower(strategy) = lower(?)" : ""}
                )
                SELECT url, strategy, timestamp, ${metric}
                FROM LatestScores
                WHERE rn = 1 AND ${metric} IS NOT NULL
                ORDER BY ${metric} ASC
                LIMIT ?;
            `;
            const params = [];
            if (strategy !== 'all') params.push(strategy);
            params.push(n);

            const results = await runQuery(db, query, params);
            displayResults(results);

        } else if (args.includes('--find-url')) {
            const patternIndex = args.indexOf('--find-url') + 1;
            const pattern = args[patternIndex];
            if (!pattern) {
                console.error("Missing pattern for --find-url.");
                process.exit(1);
            }
            console.log(`\n--- Records for URLs matching "%${pattern}%" ---`);
            const query = `SELECT * FROM ${DUCKDB_TABLE_NAME} WHERE url LIKE ? ORDER BY timestamp DESC;`;
            const results = await runQuery(db, query, [`%${pattern}%`]);
            displayResults(results);
        } else if (args.includes('--query')) {
            const queryIndex = args.indexOf('--query') + 1;
            const customQuery = args[queryIndex];
            if (!customQuery) {
                console.error("Missing SQL for --query.");
                process.exit(1);
            }
            console.log(`\n--- Custom Query Results ---`);
            console.log(`Executing: ${customQuery}`);
            const results = await runQuery(db, customQuery);
            displayResults(results);
        } else {
            console.warn("No valid operation specified or unknown arguments.");
            printHelp();
        }

    } catch (error) {
        console.error(`Execution error: ${error.message}`);
        console.error(error.stack);
    } finally {
        db.close((err) => {
            if (err) console.error(`Error closing database: ${err.message}`);
            else console.log("\nDatabase connection closed.");
        });
    }
}

main();
