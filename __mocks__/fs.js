// __mocks__/fs.js
import { jest } from '@jest/globals';

export default {
  readFileSync: jest.fn(),
  writeFileSync: jest.fn(),
  existsSync: jest.fn(),
  mkdirSync: jest.fn(),
  appendFileSync: jest.fn(),
  // Ensure all functions used by the main script are mocked here.
  // From a quick look at collect-psi.js, these seem to be the main ones.
  // path.dirname, path.resolve are from 'path' module, not 'fs'.
};
