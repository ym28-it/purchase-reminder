// Full-stack E2E: Chromium -> Vite dev server -> FastAPI -> DynamoDB Local.
// Run through the approved DynamoDB Local runner (see run-e2e.sh); it creates
// an empty test table and passes DYNAMODB_* variables to these web servers.
import { defineConfig, devices } from "@playwright/test";

const API_PORT = Number(process.env.E2E_API_PORT ?? 8000);
const WEB_PORT = Number(process.env.E2E_WEB_PORT ?? 5173);

export default defineConfig({
	testDir: "./tests",
	fullyParallel: false,
	workers: 1,
	retries: 0,
	forbidOnly: true,
	reporter: [["list"]],
	use: {
		baseURL: `http://localhost:${WEB_PORT}`,
		trace: "retain-on-failure",
		...devices["Desktop Chrome"],
	},
	webServer: [
		{
			command: `../bin/mise exec -- uv run uvicorn main:app --host 127.0.0.1 --port ${API_PORT}`,
			cwd: "../backend",
			url: `http://127.0.0.1:${API_PORT}/openapi.json`,
			reuseExistingServer: false,
			timeout: 120_000,
		},
		{
			command: `bun run dev --host localhost --port ${WEB_PORT} --strictPort`,
			cwd: "../frontend",
			url: `http://localhost:${WEB_PORT}`,
			reuseExistingServer: false,
			timeout: 120_000,
			env: { VITE_API_BASE_URL: `http://localhost:${API_PORT}` },
		},
	],
});
