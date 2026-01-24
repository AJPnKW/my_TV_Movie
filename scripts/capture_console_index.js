/*
FILE: scripts/capture_console_index.js
PROJECT: my_TV_Movie
PURPOSE: Capture console + page errors for web/index.html using Chrome DevTools Protocol (CDP)
NOTES:
- Launches a temporary Chrome profile on a local debugging port
- Captures console messages + uncaught exceptions + page errors
- Writes to logs/cdp_index_console_<timestamp>.log.txt
*/

const fs = require("fs");
const path = require("path");
const http = require("http");
const { spawn } = require("child_process");

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function httpGetJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(e); }
      });
    }).on("error", reject);
  });
}

async function main() {
  const port = 9223;
  const repoRoot = process.cwd();
  const logsDir = path.join(repoRoot, "logs");
  fs.mkdirSync(logsDir, { recursive: true });

  const ts = new Date().toISOString().replace(/[:.]/g, "").replace("Z", "Z");
  const outPath = path.join(logsDir, `cdp_index_console_${ts}.log.txt`);

  const url = `https://ajpnkw.github.io/my_TV_Movie/web/index.html?cb=${Date.now()}`;

  // Find Chrome
  const chromeCandidates = [
    process.env["ProgramFiles"] ? path.join(process.env["ProgramFiles"], "Google", "Chrome", "Application", "chrome.exe") : null,
    process.env["ProgramFiles(x86)"] ? path.join(process.env["ProgramFiles(x86)"], "Google", "Chrome", "Application", "chrome.exe") : null,
  ].filter(Boolean);

  const chromePath = chromeCandidates.find(p => fs.existsSync(p));
  if (!chromePath) {
    console.error("ERROR: Chrome not found in standard locations.");
    process.exit(2);
  }

  const profileDir = path.join(process.env.TEMP || ".", `chrome_cdp_profile_${port}`);
  const chromeArgs = [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profileDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    url,
  ];

  const log = (line) => fs.appendFileSync(outPath, line + "\n", "utf8");
  log(`URL=${url}`);
  log(`CHROME=${chromePath}`);
  log(`PROFILE=${profileDir}`);
  log(`PORT=${port}`);

  // Launch Chrome
  const chrome = spawn(chromePath, chromeArgs, { stdio: "ignore", detached: true });
  chrome.unref();

  // Wait for CDP to come up
  const versionUrl = `http://127.0.0.1:${port}/json/version`;
  let wsUrl = null;
  for (let i = 0; i < 40; i++) {
    try {
      const v = await httpGetJson(versionUrl);
      wsUrl = v.webSocketDebuggerUrl;
      if (wsUrl) break;
    } catch {}
    await sleep(250);
  }
  if (!wsUrl) {
    log("ERROR: Could not connect to CDP. Is another Chrome already using the port?");
    console.error(`WROTE: ${outPath}`);
    process.exit(3);
  }

  // Use puppeteer-core to attach and capture logs
  const puppeteer = require("puppeteer-core");
  const browser = await puppeteer.connect({ browserWSEndpoint: wsUrl });

  const pages = await browser.pages();
  const page = pages[pages.length - 1]; // the tab we opened with the URL

  page.on("console", (msg) => {
    try {
      log(`[console.${msg.type()}] ${msg.text()}`);
    } catch {}
  });

  page.on("pageerror", (err) => {
    log(`[pageerror] ${String(err && err.stack ? err.stack : err)}`);
  });

  page.on("requestfailed", (req) => {
    const f = req.failure();
    log(`[requestfailed] ${req.url()} :: ${f ? f.errorText : "unknown"}`);
  });

  page.on("response", (res) => {
    try {
      const status = res.status();
      if (status >= 400) {
        log(`[response] ${status} ${res.url()}`);
      }
    } catch {}
  });

  // Force a reload after listeners are attached to capture network responses.
  try {
    await page.setCacheEnabled(false);
    await page.reload({ waitUntil: "networkidle2" });
    log("[reload] ok");
  } catch (e) {
    log(`[reload] ERROR ${String(e && e.stack ? e.stack : e)}`);
  }

  // Let it settle
  await sleep(7000);

  // Try to capture any runtime errors by forcing a trivial eval
  try {
    await page.evaluate(() => "ping");
    log("[evaluate] ok");
  } catch (e) {
    log(`[evaluate] ERROR ${String(e && e.stack ? e.stack : e)}`);
  }

  await browser.disconnect();

  console.log(`WROTE: ${outPath}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
