import reactPlugin from 'eslint-plugin-react'

// Browser globals used in the source and test files
const browserGlobals = {
  fetch: 'readonly',
  ReadableStream: 'readonly',
  TextDecoderStream: 'readonly',
  TextEncoderStream: 'readonly',
  DOMException: 'readonly',
  AbortController: 'readonly',
  AbortSignal: 'readonly',
  Response: 'readonly',
}

const testGlobals = {
  global: 'readonly',  // vitest sets global.fetch in tests
  describe: 'readonly',
  it: 'readonly',
  expect: 'readonly',
  vi: 'readonly',
  beforeEach: 'readonly',
}

export default [
  {
    files: ['src/**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
      globals: browserGlobals,
    },
    plugins: { react: reactPlugin },
    rules: {
      'react/jsx-uses-vars': 'error',
      'no-unused-vars': 'warn',
    },
  },
  {
    files: ['src/**/*.test.{js,jsx}'],
    languageOptions: {
      globals: { ...browserGlobals, ...testGlobals },
    },
  },
]
