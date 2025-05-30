import path from 'path'; // Import the 'path' module
import { runMainLogic, originalFetchPSI } from './collect-psi.js';
import fs from 'fs'; // This will be the mocked version
import fetch from 'node-fetch'; // This will be the mocked version

// Mock the fs module
jest.mock('fs');
// Mock node-fetch. Jest will auto-mock it.
// The actual fetch calls will be done via mockExternalFetchPSI passed to runMainLogic,
// or if originalFetchPSI is tested, we'd mock its 'fetchFn' parameter.
jest.mock('node-fetch');

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
  let mockExternalFetchPSI;

  beforeEach(() => {
    // Spy on console methods
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    // Mock process.exit
    processExitSpy = jest.spyOn(process, 'exit').mockImplementation((code) => {
      throw new Error(`process.exit: ${code}`); // Throw error to stop execution in test
    });

    // Reset fs mocks
    fs.readFileSync.mockReset();
    fs.writeFileSync.mockReset();
    fs.existsSync.mockReset();
    fs.mkdirSync.mockReset();

    // Default mock for existsSync (to simulate 'data' directory possibly not existing)
    fs.existsSync.mockReturnValue(false); 
    // Mock readFileSync to return our test CSV content when expected
    fs.readFileSync.mockImplementation((filepath) => {
      if (filepath === 'test_sites.csv') {
        return testCsvContent;
      }
      // For sites_das_prefeituras_brasileiras.csv, you might want to return a different mock or throw an error
      // For this test suite, we'll primarily focus on --test mode.
      return ''; 
    });

    // Mock for fetchPSI function that will be passed to runMainLogic
    mockExternalFetchPSI = jest.fn();
  });

  afterEach(() => {
    // Restore original console and process methods
    consoleLogSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
    processExitSpy.mockRestore();
    delete process.env.PSI_KEY; // Clean up env variable
    jest.clearAllMocks(); // Clear all mocks
  });

  describe('PSI_KEY validation', () => {
    it('should log an error and exit if PSI_KEY is not set', async () => {
      expect.assertions(3); // Ensure all assertions are checked
      try {
        await runMainLogic(['node', 'collect-psi.js'], undefined, mockExternalFetchPSI);
      } catch (e) {
        expect(e.message).toBe('process.exit: 1');
      }
      expect(consoleErrorSpy).toHaveBeenCalledWith('⚠️ Defina a variável de ambiente PSI_KEY');
      expect(processExitSpy).toHaveBeenCalledWith(1);
    });

    it('should not exit if PSI_KEY is set', async () => {
      process.env.PSI_KEY = 'test-key';
      // Mock readFileSync to prevent error when PSI_KEY is set but file might not be found
      fs.readFileSync.mockReturnValue(testCsvContent); 
      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);
      expect(processExitSpy).not.toHaveBeenCalled();
    });
  });

  describe('Test Mode (--test flag)', () => {
    beforeEach(() => {
      process.env.PSI_KEY = 'fake-key'; // Needs to be set to pass initial check
    });

    it('should read from test_sites.csv and write to data/test-psi-results.json', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));
      fs.readFileSync.mockReturnValue(testCsvContent); // Ensure test_sites.csv is "read"

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      expect(fs.readFileSync).toHaveBeenCalledWith('test_sites.csv', 'utf-8');
      expect(fs.writeFileSync).toHaveBeenCalled();
      const writeArgs = fs.writeFileSync.mock.calls[0];
      expect(writeArgs[0]).toBe('data/test-psi-results.json'); // Output file path
      // More detailed checks on content written can be added here
    });

    it('should process valid URLs and skip invalid ones from CSV', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));
      fs.readFileSync.mockReturnValue(testCsvContent);

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);
      
      // http://example.com, http://invalid-url-that-does-not-exist-hopefully.com, http://another-example.com
      // are the valid http URLs in the test CSV.
      expect(mockExternalFetchPSI).toHaveBeenCalledTimes(3); 
      expect(mockExternalFetchPSI).toHaveBeenCalledWith('http://example.com');
      expect(mockExternalFetchPSI).toHaveBeenCalledWith('http://invalid-url-that-does-not-exist-hopefully.com');
      expect(mockExternalFetchPSI).toHaveBeenCalledWith('http://another-example.com');
      // "not_a_url" and "" should be filtered out
    });

    it('should correctly handle successful PSI calls and save results', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => {
        if (url === 'http://example.com' || url === 'http://another-example.com') {
          return { ...mockPsiSuccessResult, url };
        }
        throw new Error('Simulated error for other URLs');
      });
      fs.readFileSync.mockReturnValue(testCsvContent);
      
      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      expect(fs.writeFileSync).toHaveBeenCalledTimes(1);
      const writtenData = JSON.parse(fs.writeFileSync.mock.calls[0][1]);
      expect(writtenData.length).toBe(2);
      expect(writtenData[0].url).toBe('http://example.com');
      expect(writtenData[1].url).toBe('http://another-example.com');
      expect(consoleLogSpy).toHaveBeenCalledWith('✅ http://example.com → 0.9');
      expect(consoleLogSpy).toHaveBeenCalledWith('✅ http://another-example.com → 0.9');
      expect(consoleLogSpy).toHaveBeenCalledWith('💾 Gravados 2 resultados em data/test-psi-results.json');
    });

    it('should correctly handle errors from fetchPSI and log them', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => {
        if (url === 'http://invalid-url-that-does-not-exist-hopefully.com') {
          throw new Error('Simulated fetch error for non-existent URL');
        }
        return { ...mockPsiSuccessResult, url };
      });
      fs.readFileSync.mockReturnValue(testCsvContent);

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);
      
      expect(fs.writeFileSync).toHaveBeenCalledTimes(1); // example.com and another-example.com should still succeed
      const writtenData = JSON.parse(fs.writeFileSync.mock.calls[0][1]);
      expect(writtenData.length).toBe(2); // Only successful results are saved
      expect(consoleWarnSpy).toHaveBeenCalledWith('❌ erro em http://invalid-url-that-does-not-exist-hopefully.com: Simulated fetch error for non-existent URL');
      expect(consoleLogSpy).toHaveBeenCalledWith('💾 Gravados 2 resultados em data/test-psi-results.json');
    });

    it('should create data directory if it does not exist', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));
      fs.readFileSync.mockReturnValue(testCsvContent);
      fs.existsSync.mockReturnValue(false); // Simulate directory does not exist

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      expect(fs.existsSync).toHaveBeenCalledWith(path.resolve('data'));
      expect(fs.mkdirSync).toHaveBeenCalledWith(path.resolve('data'));
    });
    
    it('should not try to create data directory if it already exists', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));
      fs.readFileSync.mockReturnValue(testCsvContent);
      fs.existsSync.mockReturnValue(true); // Simulate directory exists

      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      expect(fs.existsSync).toHaveBeenCalledWith(path.resolve('data'));
      expect(fs.mkdirSync).not.toHaveBeenCalled();
    });

    it('should log appropriate messages during test mode execution', async () => {
      mockExternalFetchPSI.mockImplementation(async (url) => ({ ...mockPsiSuccessResult, url }));
      fs.readFileSync.mockReturnValue(testCsvContent);
      
      await runMainLogic(['node', 'collect-psi.js', '--test'], process.env.PSI_KEY, mockExternalFetchPSI);

      expect(consoleLogSpy).toHaveBeenCalledWith('ℹ️ Running in TEST mode.');
      expect(consoleLogSpy).toHaveBeenCalledWith('ℹ️ Reading URLs from: test_sites.csv');
      expect(consoleLogSpy).toHaveBeenCalledWith('ℹ️ Writing results to: data/test-psi-results.json');
      // Other logs are tested in specific scenarios (success, error, save)
    });
  });

  // TODO: Add tests for originalFetchPSI if direct testing is desired,
  // though its functionality is covered by testing runMainLogic in production mode (not done here yet).
  // describe('originalFetchPSI', () => { ... });
});
