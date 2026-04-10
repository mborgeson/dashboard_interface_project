/**
 * Wait for frontend and backend to be ready, then open the browser.
 * Cross-platform replacement for open-browser.sh.
 * Used by "npm run dev:all" via concurrently.
 */
import { exec } from "node:child_process";
import { request } from "node:http";

const FRONTEND_URL = "http://localhost:5173";
const BACKEND_URL = "http://localhost:8000/api/v1/health";
const MAX_WAIT = 30;

function probe(url) {
  return new Promise((resolve) => {
    const req = request(url, { method: "GET", timeout: 1000 }, (res) => {
      res.resume();
      resolve(res.statusCode < 500);
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
    req.end();
  });
}

function openBrowser(url) {
  const cmd =
    process.platform === "win32"
      ? `start "" "${url}"`
      : process.platform === "darwin"
        ? `open "${url}"`
        : `xdg-open "${url}"`;
  exec(cmd);
}

async function main() {
  for (let i = 0; i < MAX_WAIT; i++) {
    const [fe, be] = await Promise.all([probe(FRONTEND_URL), probe(BACKEND_URL)]);
    if (fe && be) {
      console.log(`[open-browser] Servers ready — opening ${FRONTEND_URL}`);
      openBrowser(FRONTEND_URL);
      return;
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  console.log(`[open-browser] Timed out after ${MAX_WAIT}s waiting for servers.`);
}

main();
