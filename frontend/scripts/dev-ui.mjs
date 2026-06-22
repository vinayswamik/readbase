import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");

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

const mockServer = run("node", ["mock/server.mjs"], "mock server");
const vite = run("npm", ["run", "dev"], "vite");

function shutdown() {
  mockServer.kill("SIGTERM");
  vite.kill("SIGTERM");
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
