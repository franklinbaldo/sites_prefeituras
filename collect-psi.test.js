import path from 'path'; // Import the 'path' module
import { jest, describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { runMainLogic, originalFetchPSI } from './collect-psi.js';
import fs from 'fs'; // This will be the mocked version from __mocks__/fs.js
import fetch from 'node-fetch'; // This will be the mocked version from __mocks__/node-fetch.js

// Mock the fs module - RELY ON __mocks__/fs.js
// jest.mock('fs');
// Mock node-fetch - RELY ON __mocks__/node-fetch.js
// jest.mock('node-fetch');

// At the top of collect-psi.test.js, after path import
// Assuming tests run from project root, so __dirname for collect-psi.js is project root.
const expectedTestCsvPath = path.resolve('test_sites.csv');
const expectedProcessingStatePath = path.resolve('data', 'psi_processing_state.json');

// Test CSV data
const testCsvContent = `"Nome do Município","UF","Código IBGE","Endereço Eletrônico","Observação"
"Test City 1","TS","1234567","http://example.com","Valid URL"
"Test City 2","TS","7654321","http://invalid-url-that-does-not-exist-hopefully.com","Invalid URL (non-existent)"
"Test City 3","TS","0000000","not_a_url","Invalid URL (bad format)"
"Test City 4","TS","1111111","","Empty URL"
"Test City 5","TS","2222222","http://another-example.com","Another valid URL"`;

const mockPsiSuccessResult = {
  performance: 0.9,
  accessibility: 0.8,
  seo: 0.7,
  bestPractices: 0.95,
  timestamp: 'test-timestamp'
};

describe('collect-psi.js', () => {
  let consoleLogSpy;
  let consoleWarnSpy;
  let consoleErrorSpy;
  let processExitSpy;
  let mockExternalFetchPSI; // This will be our own mock for the fetchPSI function passed to runMainLogic

  beforeEach(() => {
    // Spy on console methods
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    // Mock process.exit
    processExitSpy = jest.spyOn(process, 'exit').mockImplementation((code) => {
      throw new Error(`process.exit: ${code}`); // Throw error to stop execution in test
    });

    // Reset specific mock functions from the auto-mocked fs and fetch modules
    fs.readFileSync.mockReset();
    fs.writeFileSync.mockReset();
    fs.existsSync.mockReset();
    fs.mkdirSync.mockReset();
    fs.appendFileSync.mockReset(); // Ensure this is reset if used by main script for errors
    fetch.mockReset(); // Reset the default export from __mocks__/node-fetch.js

    // Default mock for existsSync (to simulate 'data' directory possibly not existing for output, or state file)
    // For PROCESSING_STATE_FILE:
    fs.existsSync.mockImplementation(filePath => {
      if (filePath === expectedProcessingStatePath) {
        return false; // Default: no state file exists
      }
      if (filePath === path.resolve('data')) { // For output directory 'data'
        return false; // Default: output directory does not exist
      }
      return false; // Default for any other path
    });

    // Default mock for readFileSync
    fs.readFileSync.mockImplementation((filepath) => {
      if (filepath === expectedTestCsvPath) {
        return testCsvContent;
      }
      if (filepath === expectedProcessingStatePath) {
        // This should only be called if existsSync for this path was true
        return JSON.stringify({});
      }
      return ''; // Default for other unexpected calls
    });

    // This is the mock for the fetchPSI function *parameter* of runMainLogic, not global fetch
    mockExternalFetchPSI = jest.fn();
  });

  afterEach(() => {
    // Restore original console and process methods
    consoleLogSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
    processExitSpy.mockRestore();
    delete process.env.PSI_KEY; // Clean up env variable
    jest.clearAllMocks(); // Reset all mocks after each test
  });

  describe('PSI_KEY validation', () => {
    it('should log an error and exit if PSI_KEY is not set', async () => {
      expect.assertions(3); // Ensure all assertions are checked
      try {
        // Pass undefined for apiKey, and our mockExternalFetchPSI
        await runMainLogic(['node', 'collect-psi.js'], undefined, mockExternalFetchPSI);
      } catch (e) {
        expect(e.message).toBe('process.exit: 1');
      }
      expect(consoleErrorSpy).toHaveBeenCalledWith('⚠️ Defina a variável de ambiente PSI_KEY');
      expect(processExitSpy).toHaveBeenCalledWith(1);
    });

    it('should not exit if PSI_KEY is set', async () => {
      process.env.PSI_KEY = 'test-key';
      // Ensure CSV read doesn't fail and processing state read doesn't fail
      fs.readFileSync.mockImplementation((filepath) => {
        if (filepath === expectedTestCsvPath) return testCsvContent;
        if (filepath === expectedProcessingStatePath) return JSON.stringify({});
        return '';
      });
      fs.existsSync.mockReturnValue(true); // Assume all relevant files/dirs exist for this specific test

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);
      expect(processExitSpy).not.toHaveBeenCalled();
    });
  });

  describe('Test Mode (--test flag)', () => {
    beforeEach(() => {
      process.env.PSI_KEY = 'fake-key'; // Needs to be set to pass initial check

      // Specific mock for readFileSync for most test mode tests
      fs.readFileSync.mockImplementation((filepath) => {
        if (filepath === expectedTestCsvPath) return testCsvContent;
        // Simulate no processing state file by default for these tests, unless overridden
        if (filepath === expectedProcessingStatePath) return JSON.stringify({});
        return '';
      });
      // Simulate processing state file does not exist by default
      fs.existsSync.mockImplementation(filePath => {
        if (filePath === expectedProcessingStatePath) return false;
        if (filePath === path.resolve('data')) return false; // Output directory
        return false;
      });
    });

    it('should read from test_sites.csv and write to data/test-psi-results.json', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      expect(fs.readFileSync).toHaveBeenCalledWith(expectedTestCsvPath, 'utf-8');
      expect(fs.writeFileSync).toHaveBeenCalled(); // Check if called, path/content checked in other tests
      const writeArgs = fs.writeFileSync.mock.calls[0];
      // The outputJsonFile in test mode is 'data/test-psi-results.json'
      // path.resolve is not strictly necessary here as it's a relative path from root.
      expect(writeArgs[0]).toBe(path.resolve('data/test-psi-results.json'));
    });

    it('should process valid URLs and skip invalid ones from CSV', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      expect(mockExternalFetchPSI).toHaveBeenCalledTimes(3);
      expect(mockExternalFetchPSI).toHaveBeenCalledWith('http://example.com');
      expect(mockExternalFetchPSI).toHaveBeenCalledWith('http://invalid-url-that-does-not-exist-hopefully.com');
      expect(mockExternalFetchPSI).toHaveBeenCalledWith('http://another-example.com');
    });

    it('should correctly handle successful PSI calls and save results', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => {
        if (url === 'http://example.com' || url === 'http://another-example.com') {
          return { ...mockPsiSuccessResult, url, performance: 0.9 }; // Ensure performance is in mock
        }
        throw new Error('Simulated error for other URLs');
      });

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      expect(fs.writeFileSync).toHaveBeenCalledTimes(1); // For results.json
      const resultsWriteCall = fs.writeFileSync.mock.calls.find(call => call[0].endsWith('test-psi-results.json'));
      expect(resultsWriteCall).toBeDefined();
      const writtenData = JSON.parse(resultsWriteCall[1]);
      expect(writtenData.length).toBe(2);
      expect(writtenData[0].url).toBe('http://example.com');
      expect(writtenData[1].url).toBe('http://another-example.com');
      expect(consoleLogSpy).toHaveBeenCalledWith('✅ http://example.com → 0.9');
      expect(consoleLogSpy).toHaveBeenCalledWith('✅ http://another-example.com → 0.9');
      expect(consoleLogSpy).toHaveBeenCalledWith(`💾 Gravados 2 resultados em ${path.resolve('data/test-psi-results.json')}`);
    });

    it('should correctly handle errors from fetchPSI and log them', async () => {
      const specificErrorUrl = 'http://invalid-url-that-does-not-exist-hopefully.com';
      mockExternalFetchPSI.mockImplementation(async (url) => {
        if (url === specificErrorUrl) {
          throw new Error('Simulated fetch error for non-existent URL');
        }
        return { ...mockPsiSuccessResult, url, performance: 0.9 }; // Ensure performance
      });

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      const resultsWriteCall = fs.writeFileSync.mock.calls.find(call => call[0].endsWith('test-psi-results.json'));
      expect(resultsWriteCall).toBeDefined();
      const writtenData = JSON.parse(resultsWriteCall[1]);
      expect(writtenData.length).toBe(2); // Only successful results are saved

      expect(consoleWarnSpy).toHaveBeenCalledWith(`❌ erro em ${specificErrorUrl}: Simulated fetch error for non-existent URL`);
      // Check that error was logged to file
      expect(fs.appendFileSync).toHaveBeenCalledWith('psi_errors.log', expect.stringContaining(`Error for URL ${specificErrorUrl}: Simulated fetch error for non-existent URL`));
      expect(consoleLogSpy).toHaveBeenCalledWith(`💾 Gravados 2 resultados em ${path.resolve('data/test-psi-results.json')}`);
    });

    it('should create data directory if it does not exist for results', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));
      // Simulate 'data' directory does not exist, but processing state file also doesn't exist
      fs.existsSync.mockImplementation(filePath => {
        if (filePath === path.resolve('data')) return false; // data dir for output
        if (filePath === expectedProcessingStatePath) return false; // processing state file
        if (filePath === path.dirname(expectedProcessingStatePath)) return false; // data dir for state file
        return false;
      });

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      // Check for creation of 'data' dir for psi-results.json
      expect(fs.mkdirSync).toHaveBeenCalledWith(path.resolve('data'), { recursive: true });
    });

    it('should create data directory if it does not exist for processing state', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));
      // Simulate 'data' directory (for state file) does not exist
      // but output 'data' directory might exist or not, let's make it specific
      const stateDir = path.dirname(expectedProcessingStatePath); // should be 'data'
      fs.existsSync.mockImplementation(filePath => {
        if (filePath === stateDir) return false; // THIS is the critical check for this test
        if (filePath === expectedProcessingStatePath) return false;
        // for output results file, assume its data dir exists to isolate the test
        if (filePath === path.resolve('data')) return true;
        return false;
      });

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      // Check for creation of 'data' dir for psi_processing_state.json
      expect(fs.mkdirSync).toHaveBeenCalledWith(stateDir, { recursive: true });
    });


    it('should not try to create data directory if it already exists', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));
      fs.existsSync.mockReturnValue(true); // Simulate all directories exist

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      // Check that mkdirSync was not called if 'data' (for results) and 'data' (for state) exist
      // fs.existsSync(path.resolve('data')) would be true
      // fs.existsSync(path.dirname(expectedProcessingStatePath)) would be true
      expect(fs.mkdirSync).not.toHaveBeenCalled();
    });

    it('should log appropriate messages during test mode execution', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      expect(consoleLogSpy).toHaveBeenCalledWith('ℹ️ Running in TEST mode.');
      expect(consoleLogSpy).toHaveBeenCalledWith(`ℹ️ Reading URLs from: ${expectedTestCsvPath}`);
      expect(consoleLogSpy).toHaveBeenCalledWith(`ℹ️ Writing results to: ${path.resolve('data/test-psi-results.json')}`);
    });
  });

  // describe('originalFetchPSI', () => { ... });
});
