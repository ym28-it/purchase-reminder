import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const apiClient = createClient<paths>({
	baseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
});

/** APIがエラー応答を返したことを表す。原因はHTTPステータスで判定する。 */
export class ApiError extends Error {
	readonly status: number;
	readonly body: unknown;

	constructor(status: number, body: unknown) {
		super(`API request failed with status ${status}`);
		this.name = "ApiError";
		this.status = status;
		this.body = body;
	}
}
