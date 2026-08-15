import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	createPurchase,
	deletePurchase,
	getAllPurchases,
	type PurchaseResponse,
	putPurchase,
} from "@/api/purchases";
import { queryClient } from "@/api/queryClient";
import {
	useCreatePurchase,
	useDeletePurchase,
	usePurchases,
	usePutPurchase,
} from "@/hooks/usePurchases";
import { queryClientWrapper, setUpIsolatedQueryClient } from "@/test-utils";

vi.mock("@/api/purchases", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/api/purchases")>()),
	createPurchase: vi.fn(),
	putPurchase: vi.fn(),
	getAllPurchases: vi.fn(),
	deletePurchase: vi.fn(),
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

setUpIsolatedQueryClient();

beforeEach(() => {
	vi.clearAllMocks();
});

describe("usePurchases", () => {
	it("HOOK-01: 成功時、dataに一覧が入る", async () => {
		vi.mocked(getAllPurchases).mockResolvedValueOnce([purchaseFixture]);

		const { result } = renderHook(() => usePurchases(), {
			wrapper: queryClientWrapper,
		});

		expect(result.current.isPending).toBe(true);
		await waitFor(() => expect(result.current.isPending).toBe(false));
		expect(result.current.data).toEqual([purchaseFixture]);
	});

	it("HOOK-02: 失敗時、isErrorがtrueになる", async () => {
		vi.mocked(getAllPurchases).mockRejectedValueOnce(new Error("fail"));

		const { result } = renderHook(() => usePurchases(), {
			wrapper: queryClientWrapper,
		});

		await waitFor(() => expect(result.current.isError).toBe(true));
	});

	it("HOOK-03: queryKeyが['purchases']で登録される", async () => {
		vi.mocked(getAllPurchases).mockResolvedValueOnce([purchaseFixture]);

		const { result } = renderHook(() => usePurchases(), {
			wrapper: queryClientWrapper,
		});

		await waitFor(() => expect(result.current.isPending).toBe(false));
		expect(queryClient.getQueryData(["purchases"])).toEqual([purchaseFixture]);
	});
});

describe("useCreatePurchase", () => {
	it("HOOK-04: 成功後にpurchasesクエリがinvalidateされる", async () => {
		vi.mocked(createPurchase).mockResolvedValueOnce(purchaseFixture);
		const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

		const { result } = renderHook(() => useCreatePurchase(), {
			wrapper: queryClientWrapper,
		});
		result.current.mutate({
			name: "卵",
			category: "食品",
			speed: 1,
			stock: 5,
			is_temporary: false,
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));
		expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["purchases"] });
	});

	it("HOOK-05: 失敗時はinvalidateされない", async () => {
		vi.mocked(createPurchase).mockRejectedValueOnce(new Error("fail"));
		const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

		const { result } = renderHook(() => useCreatePurchase(), {
			wrapper: queryClientWrapper,
		});
		result.current.mutate({
			name: "卵",
			category: "食品",
			speed: 1,
			stock: 5,
			is_temporary: false,
		});

		await waitFor(() => expect(result.current.isError).toBe(true));
		expect(invalidateSpy).not.toHaveBeenCalled();
	});
});

describe("usePutPurchase", () => {
	it("HOOK-06: {purchaseId, input}がputPurchaseに分解されて渡る", async () => {
		vi.mocked(putPurchase).mockResolvedValueOnce(purchaseFixture);

		const { result } = renderHook(() => usePutPurchase(), {
			wrapper: queryClientWrapper,
		});
		result.current.mutate({
			purchaseId: "p1",
			input: {
				name: "卵",
				category: "食品",
				speed: 1,
				stock: 5,
				is_temporary: false,
			},
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));
		expect(putPurchase).toHaveBeenCalledWith("p1", {
			name: "卵",
			category: "食品",
			speed: 1,
			stock: 5,
			is_temporary: false,
		});
	});

	it("HOOK-07: 成功後にpurchasesクエリがinvalidateされる", async () => {
		vi.mocked(putPurchase).mockResolvedValueOnce(purchaseFixture);
		const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

		const { result } = renderHook(() => usePutPurchase(), {
			wrapper: queryClientWrapper,
		});
		result.current.mutate({
			purchaseId: "p1",
			input: {
				name: "卵",
				category: "食品",
				speed: 1,
				stock: 5,
				is_temporary: false,
			},
		});

		await waitFor(() => expect(result.current.isSuccess).toBe(true));
		expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["purchases"] });
	});
});

describe("useDeletePurchase", () => {
	it("HOOK-08: purchaseIdがdeletePurchaseにそのまま渡る", async () => {
		vi.mocked(deletePurchase).mockResolvedValueOnce(undefined);

		const { result } = renderHook(() => useDeletePurchase(), {
			wrapper: queryClientWrapper,
		});
		result.current.mutate("p1");

		await waitFor(() => expect(result.current.isSuccess).toBe(true));
		// deletePurchaseはmutationFnとして直接渡されており、tanstack-queryが
		// 第2引数（mutationFnContext）を付与して呼び出すため、第1引数のみ検証する。
		expect(vi.mocked(deletePurchase).mock.calls[0]?.[0]).toBe("p1");
	});

	it("HOOK-09: 成功後にpurchasesクエリがinvalidateされる", async () => {
		vi.mocked(deletePurchase).mockResolvedValueOnce(undefined);
		const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

		const { result } = renderHook(() => useDeletePurchase(), {
			wrapper: queryClientWrapper,
		});
		result.current.mutate("p1");

		await waitFor(() => expect(result.current.isSuccess).toBe(true));
		expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["purchases"] });
	});
});
