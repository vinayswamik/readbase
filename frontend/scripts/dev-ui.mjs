import { execSync, spawn } from "node:child_process";
import path from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");

const MOCK_PORT = Number(process.env.MOCK_API_PORT || 4010);
const VITE_PORTS = [5173, 5174, 5175, 5176, 5177, 5178];

function killPort(port) {
  let output = "";
  try {
    output = execSync(`lsof -ti tcp:${port}`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return false;
  }

  const pids = output.split(/\s+/).filter(Boolean);
  if (!pids.length) {
    return false;
  }

  for (const pid of pids) {
    try {
      process.kill(Number(pid), "SIGKILL");
    } catch {
      // process may already be gone
    }
  }

  console.log(`[dev:ui] freed port ${port} (pids: ${pids.join(", ")})`);
  return true;
}

function freeDevPorts() {
  let freedAny = false;
  for (const port of [MOCK_PORT, ...VITE_PORTS]) {
    if (killPort(port)) {
      freedAny = true;
    }
  }
  return freedAny;
}

function run(command, args, label) {
  const child = spawn(command, args, {
    cwd: frontendRoot,
    stdio: "inherit",
    env: process.env,
  });
  child.on("exit", (code) => {
    if (code && code !== 0) {
      console.error(`[dev:ui] ${label} exited with code ${code}`);
    }
  });
  return child;
}

async function main() {
  if (freeDevPorts()) {
    await sleep(200);
  }

  const mockServer = run("node", ["mock/server.mjs"], "mock server");
  const vite = run("npm", ["run", "dev"], "vite");

  function shutdown() {
    mockServer.kill("SIGTERM");
    vite.kill("SIGTERM");
    process.exit(0);
  }

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

void main();
