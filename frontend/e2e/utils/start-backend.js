/**
 * Robust Backend Lifecycle Manager for E2E Tests
 *
 * Features:
 * - Health check with exponential backoff retry
 * - Graceful cleanup of zombie processes
 * - Port conflict detection and resolution
 * - Detailed logging for debugging
 * - Cross-platform support (Windows/Unix)
 */

const { spawn, execSync } = require('child_process');
const http = require('http');
const path = require('path');

const CONFIG = {
  backendPort: 8001,
  healthUrl: 'http://localhost:8001/health',
  maxRetries: 30,
  initialRetryDelay: 500,
  maxRetryDelay: 5000,
  startupTimeout: 60000,
  backendDir: path.resolve(__dirname, '../../../backend_api'),
  projectRoot: path.resolve(__dirname, '../../..'),
};

/**
 * Check if a process is using the specified port
 */
function isPortInUse(port) {
  return new Promise((resolve) => {
    const server = require('net').createServer();
    server.once('error', () => resolve(true));
    server.once('listening', () => {
      server.close();
      resolve(false);
    });
    server.listen(port);
  });
}

/**
 * Kill any process using the backend port
 */
async function killProcessOnPort(port) {
  const isWindows = process.platform === 'win32';

  try {
    if (isWindows) {
      // Windows: find and kill process using netstat
      try {
        const result = execSync(`netstat -ano | findstr :${port}`, { encoding: 'utf8' });
        const lines = result.split('\n').filter(line => line.includes('LISTENING'));
        for (const line of lines) {
          const parts = line.trim().split(/\s+/);
          const pid = parts[parts.length - 1];
          if (pid && pid !== '0') {
            console.log(`[Backend] Killing process ${pid} on port ${port}`);
            try {
              execSync(`taskkill /F /PID ${pid}`, { stdio: 'ignore' });
            } catch (e) {
              // Process might have already exited
            }
          }
        }
      } catch (e) {
        // No process found on port
      }
    } else {
      // Unix: use lsof and kill
      try {
        const result = execSync(`lsof -ti :${port}`, { encoding: 'utf8' });
        const pids = result.trim().split('\n').filter(Boolean);
        for (const pid of pids) {
          console.log(`[Backend] Killing process ${pid} on port ${port}`);
          try {
            execSync(`kill -9 ${pid}`, { stdio: 'ignore' });
          } catch (e) {
            // Process might have already exited
          }
        }
      } catch (e) {
        // No process found on port
      }
    }

    // Wait a moment for ports to be released
    await new Promise(resolve => setTimeout(resolve, 1000));
  } catch (error) {
    console.log(`[Backend] Port cleanup warning: ${error.message}`);
  }
}

/**
 * Check backend health with timeout
 */
function checkHealth(url, timeout = 5000) {
  return new Promise((resolve) => {
    const request = http.get(url, { timeout }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const parsed = JSON.parse(data);
          resolve(parsed.status === 'healthy');
        } catch {
          resolve(false);
        }
      });
    });

    request.on('error', () => resolve(false));
    request.on('timeout', () => {
      request.destroy();
      resolve(false);
    });
  });
}

/**
 * Wait for backend to become healthy with exponential backoff
 */
async function waitForHealth(maxRetries = CONFIG.maxRetries) {
  let delay = CONFIG.initialRetryDelay;

  for (let i = 0; i < maxRetries; i++) {
    const isHealthy = await checkHealth(CONFIG.healthUrl);
    if (isHealthy) {
      console.log(`[Backend] Health check passed (attempt ${i + 1}/${maxRetries})`);
      return true;
    }

    console.log(`[Backend] Health check failed (attempt ${i + 1}/${maxRetries}), retrying in ${delay}ms...`);
    await new Promise(resolve => setTimeout(resolve, delay));

    // Exponential backoff with cap
    delay = Math.min(delay * 1.5, CONFIG.maxRetryDelay);
  }

  return false;
}

/**
 * Check if backend is already running and healthy
 */
async function isBackendRunning() {
  return checkHealth(CONFIG.healthUrl);
}

/**
 * Start the backend server
 */
async function startBackend() {
  console.log('[Backend] Starting backend lifecycle manager...');
  console.log(`[Backend] Project root: ${CONFIG.projectRoot}`);
  console.log(`[Backend] Backend dir: ${CONFIG.backendDir}`);

  // Check if backend is already running
  if (await isBackendRunning()) {
    console.log('[Backend] Backend already running and healthy!');
    // Keep process alive so Playwright doesn't restart
    await new Promise(() => {});
    return;
  }

  // Check for port conflicts
  if (await isPortInUse(CONFIG.backendPort)) {
    console.log(`[Backend] Port ${CONFIG.backendPort} is in use, attempting cleanup...`);
    await killProcessOnPort(CONFIG.backendPort);

    // Verify port is now free
    if (await isPortInUse(CONFIG.backendPort)) {
      console.error(`[Backend] ERROR: Port ${CONFIG.backendPort} still in use after cleanup!`);
      process.exit(1);
    }
  }

  // Determine the Python command
  const isWindows = process.platform === 'win32';
  const pythonCmd = isWindows ? 'python' : 'python3';

  // Start uvicorn
  console.log('[Backend] Starting uvicorn server...');

  const backend = spawn(
    pythonCmd,
    [
      '-m', 'uvicorn',
      'backend_api.main:app',
      '--host', '0.0.0.0',
      '--port', String(CONFIG.backendPort),
      '--reload',
    ],
    {
      cwd: CONFIG.projectRoot,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: isWindows,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
        ENVIRONMENT: 'development',
      },
    }
  );

  // Log backend output
  backend.stdout.on('data', (data) => {
    const lines = data.toString().split('\n').filter(Boolean);
    lines.forEach(line => console.log(`[Backend] ${line}`));
  });

  backend.stderr.on('data', (data) => {
    const lines = data.toString().split('\n').filter(Boolean);
    lines.forEach(line => console.log(`[Backend] ${line}`));
  });

  backend.on('error', (error) => {
    console.error(`[Backend] Failed to start: ${error.message}`);
    process.exit(1);
  });

  backend.on('exit', (code, signal) => {
    if (code !== 0 && code !== null) {
      console.error(`[Backend] Exited with code ${code}`);
      process.exit(code);
    }
    if (signal) {
      console.log(`[Backend] Terminated by signal ${signal}`);
    }
  });

  // Wait for health check
  console.log('[Backend] Waiting for server to become healthy...');
  const isHealthy = await waitForHealth();

  if (!isHealthy) {
    console.error('[Backend] ERROR: Server failed to become healthy within timeout!');
    backend.kill('SIGTERM');
    process.exit(1);
  }

  console.log('[Backend] Server is healthy and ready for tests!');

  // Handle cleanup on process exit
  const cleanup = () => {
    console.log('[Backend] Shutting down server...');
    backend.kill('SIGTERM');

    // Force kill after 5 seconds if still running
    setTimeout(() => {
      if (!backend.killed) {
        console.log('[Backend] Force killing server...');
        backend.kill('SIGKILL');
      }
    }, 5000);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);
  process.on('exit', cleanup);

  // Keep process running
  await new Promise(() => {});
}

// Run
startBackend().catch((error) => {
  console.error(`[Backend] Fatal error: ${error.message}`);
  process.exit(1);
});
