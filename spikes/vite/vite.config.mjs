import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const spikeDir = fileURLToPath(new URL(".", import.meta.url));
const repoRoot = resolve(spikeDir, "..", "..");
const outDir = resolve(repoRoot, ".tmp", "vite-spike-dist");

export default defineConfig({
  root: spikeDir,
  publicDir: false,
  base: "./",
  build: {
    outDir,
    emptyOutDir: true,
    sourcemap: true,
    target: "es2022",
    rollupOptions: {
      input: resolve(spikeDir, "index.html"),
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4174,
    strictPort: true,
  },
});
