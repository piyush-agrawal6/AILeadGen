import path from "path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./test-setup.ts",
    exclude: ["gmail-e2e/**", "admission-e2e/**", "sheet-export-e2e/**", "developer-e2e/**", "e2e/**", "auth-e2e/**", "workspace-e2e/**", "preview-e2e/**", "integration-e2e/**", "brand-e2e/**", "node_modules/**", ".next/**"],
  },
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./"),
    },
  },
});
