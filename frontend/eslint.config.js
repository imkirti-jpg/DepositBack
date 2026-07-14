const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');
const prettierConfig = require('eslint-config-prettier');

module.exports = defineConfig([
  {
    ignores: ['**/node_modules/**', '**/.expo/**', '**/dist/**', '**/web-build/**'],
  },
  ...expoConfig,
  {
    files: ['**/*.{ts,tsx}'],
    plugins: {
      '@typescript-eslint': require('@typescript-eslint/eslint-plugin'),
      prettier: require('eslint-plugin-prettier'),
    },
    rules: {
      '@typescript-eslint/consistent-type-imports': 'error',
      'prettier/prettier': 'error',
    },
  },
  {
    files: ['**/*.{js,jsx}'],
    plugins: {
      prettier: require('eslint-plugin-prettier'),
    },
    rules: {
      'prettier/prettier': 'error',
    },
  },
  prettierConfig,
]);
