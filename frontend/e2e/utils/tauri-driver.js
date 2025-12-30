/**
 * Tauri WebDriver Integration for E2E Testing
 *
 * This module provides utilities for testing the Tauri desktop application
 * using WebDriver protocol via tauri-driver.
 *
 * Prerequisites:
 * 1. Install tauri-driver: cargo install tauri-driver
 * 2. Build the Tauri app: npm run tauri:build (or use dev mode)
 *
 * Usage:
 * This is used by playwright.tauri.config.ts for desktop E2E tests.
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const CONFIG = {
  tauriDriverPort: 4444,
  projectRoot: path.resolve(__dirname, '../../..'),
  frontendDir: path.resolve(__dirname, '../..'),
  appName: 'Alabama Auction Watcher',
};

/**
 * Find the built Tauri executable
 */
function findTauriExecutable() {
  const isWindows = process.platform === 'win32';
  const isMac = process.platform === 'darwin';

  const possiblePaths = [];

  if (isWindows) {
    possiblePaths.push(
      path.join(CONFIG.frontendDir, 'src-tauri/target/release/alabama-auction-watcher.exe'),
      path.join(CONFIG.frontendDir, 'src-tauri/target/debug/alabama-auction-watcher.exe'),
    );
  } else if (isMac) {
    possiblePaths.push(
      path.join(CONFIG.frontendDir, 'src-tauri/target/release/bundle/macos/Alabama Auction Watcher.app/Contents/MacOS/Alabama Auction Watcher'),
      path.join(CONFIG.frontendDir, 'src-tauri/target/debug/bundle/macos/Alabama Auction Watcher.app/Contents/MacOS/Alabama Auction Watcher'),
    );
  } else {
    possiblePaths.push(
      path.join(CONFIG.frontendDir, 'src-tauri/target/release/alabama-auction-watcher'),
      path.join(CONFIG.frontendDir, 'src-tauri/target/debug/alabama-auction-watcher'),
    );
  }

  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      return p;
    }
  }

  return null;
}

/**
 * Check if tauri-driver is installed
 */
function isTauriDriverInstalled() {
  try {
    execSync('tauri-driver --version', { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

/**
 * Start tauri-driver
 */
function startTauriDriver() {
  return new Promise((resolve, reject) => {
    if (!isTauriDriverInstalled()) {
      console.error('[Tauri] tauri-driver not installed. Run: cargo install tauri-driver');
      reject(new Error('tauri-driver not installed'));
      return;
    }

    const driver = spawn('tauri-driver', ['--port', String(CONFIG.tauriDriverPort)], {
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    driver.stdout.on('data', (data) => {
      console.log(`[Tauri Driver] ${data.toString().trim()}`);
    });

    driver.stderr.on('data', (data) => {
      console.log(`[Tauri Driver] ${data.toString().trim()}`);
    });

    // Wait for driver to be ready
    setTimeout(() => {
      resolve(driver);
    }, 2000);

    driver.on('error', reject);
  });
}

/**
 * Get WebDriver capabilities for Tauri
 */
function getTauriCapabilities() {
  const executable = findTauriExecutable();

  if (!executable) {
    throw new Error('Tauri executable not found. Build the app first: npm run tauri:build');
  }

  return {
    capabilities: {
      alwaysMatch: {
        'tauri:options': {
          application: executable,
        },
      },
    },
  };
}

module.exports = {
  findTauriExecutable,
  isTauriDriverInstalled,
  startTauriDriver,
  getTauriCapabilities,
  CONFIG,
};
