import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/api/client";
import {
	createPurchase,
	deletePurchase,
	getAllPurchases,
	type PurchaseCreateRequest,
	type PurchasePutRequest,
	type PurchaseResponse,
	putPurchase,
} from "@/api/purchases";

vi.mock("@/api/client", () => ({
	apiClient: {
		POST: vi.fn(),
		GET: vi.fn(),
		PUT: vi.fn(),
		DELETE: vi.fn(),
	},
}));

const purchaseFixture: PurchaseResponse = {
	id: "p1",
	name: "卵",
	category: "食品",
	speed: 1,
	stock: 5,
	is_temporary: false,
	created_at: "2026-08-01T00:00:00Z",
	updated_at: "2026-08-01T00:00:00Z",
};

const createInput: PurchaseCreateRequest = {
	name: "卵",
	category: "食品",
	speed: 1,
	stock: 5,
	is_temporary: false,
};

const putInput: PurchasePutRequest = createInput;

beforeEach(() => {
	vi.clearAllMocks();
});

describe("createPurchase", () => {
	it("API-01: 成功時、POSTが正しい引数で呼ばれ、dataがそのまま返る", async () => {
		vi.mocked(apiClient.POST).mockResolvedValueOnce({
			data: purchaseFixture,
			error: undefined,
			response: new Response(),
		});

		const result = await createPurchase(createInput);

		expect(apiClient.POST).toHaveBeenCalledWith("/purchases", {
			body: createInput,
		});
		expect(result).toEqual(purchaseFixture);
	});

	it("API-02: 失敗時、errorオブジェクトがそのままthrowされる", async () => {
		const apiError = {
			detail: [{ loc: ["body", "name"], msg: "invalid", type: "value_error" }],
		};
		vi.mocked(apiClient.POST).mockResolvedValueOnce({
			data: undefined,
			error: apiError,
			response: new Response(),
		});

		await expect(createPurchase(createInput)).rejects.toBe(apiError);
	});
});

describe("putPurchase", () => {
	it("API-03: 成功時、purchase_idとbodyを渡してPUTが呼ばれ、dataが返る", async () => {
		vi.mocked(apiClient.PUT).mockResolvedValueOnce({
			data: purchaseFixture,
			error: undefined,
			response: new Response(),
		});

		const result = await putPurchase("p1", putInput);

		expect(apiClient.PUT).toHaveBeenCalledWith("/purchases/{purchase_id}", {
			params: { path: { purchase_id: "p1" } },
			body: putInput,
		});
		expect(result).toEqual(purchaseFixture);
	});

	it("API-04: 失敗時、errorオブジェクトがそのままthrowされる", async () => {
		const apiError = {
			detail: [
				{ loc: ["path", "purchase_id"], msg: "not found", type: "value_error" },
			],
		};
		vi.mocked(apiClient.PUT).mockResolvedValueOnce({
			data: undefined,
			error: apiError,
			response: new Response(),
		});

		await expect(putPurchase("p1", putInput)).rejects.toBe(apiError);
	});
});

describe("getAllPurchases", () => {
	it("API-05: 成功時、GETが呼ばれ配列がそのまま返る", async () => {
		vi.mocked(apiClient.GET).mockResolvedValueOnce({
			data: [purchaseFixture],
			error: undefined,
			response: new Response(),
		});

		const result = await getAllPurchases();

		expect(apiClient.GET).toHaveBeenCalledWith("/purchases");
		expect(result).toEqual([purchaseFixture]);
	});

	it("API-06: 失敗時、errorオブジェクトがそのままthrowされる", async () => {
		const apiError = {
			detail: [{ loc: ["query"], msg: "server error", type: "value_error" }],
		};
		vi.mocked(apiClient.GET).mockResolvedValueOnce({
			data: undefined,
			error: apiError,
			response: new Response(),
		});

		await expect(getAllPurchases()).rejects.toBe(apiError);
	});
});

describe("deletePurchase", () => {
	it("API-07: 成功時、purchase_idを渡してDELETEが呼ばれ、戻り値はundefined", async () => {
		vi.mocked(apiClient.DELETE).mockResolvedValueOnce({
			data: undefined,
			error: undefined,
			response: new Response(),
		});

		const result = await deletePurchase("p1");

		expect(apiClient.DELETE).toHaveBeenCalledWith("/purchases/{purchase_id}", {
			params: { path: { purchase_id: "p1" } },
		});
		expect(result).toBeUndefined();
	});

	it("API-08: 失敗時、errorオブジェクトがそのままthrowされる", async () => {
		const apiError = {
			detail: [
				{ loc: ["path", "purchase_id"], msg: "not found", type: "value_error" },
			],
		};
		vi.mocked(apiClient.DELETE).mockResolvedValueOnce({
			data: undefined,
			error: apiError,
			response: new Response(),
		});

		await expect(deletePurchase("p1")).rejects.toBe(apiError);
	});
});
