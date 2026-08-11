/**
 * プレースホルダー。backendにエンドポイントが実装され次第、
 * `bun run gen:api`（http://localhost:8000/openapi.json から生成）でこのファイル全体が上書きされる。
 */

export interface paths {
	[path: string]: never;
}

export interface webhooks {
	[name: string]: never;
}

export interface components {
	schemas: never;
	responses: never;
	parameters: never;
	requestBodies: never;
	headers: never;
	pathItems: never;
}

export type $defs = Record<string, never>;

export type operations = Record<string, never>;
