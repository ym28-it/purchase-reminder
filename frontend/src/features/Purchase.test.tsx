import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { createPurchase, getAllPurchases } from "@/api/purchases";
import { queryClient } from "@/api/queryClient";
import { Purchase } from "@/features/Purchase";

vi.mock("@/api/purchases", () => ({
	createPurchase: vi.fn(),
	getAllPurchases: vi.fn(),
	deletePurchase: vi.fn(),
	putPurchase: vi.fn(),
}));

beforeEach(() => {
	queryClient.clear();
	vi.mocked(getAllPurchases).mockResolvedValue([]);
});

afterEach(() => {
	cleanup();
	queryClient.clear();
	vi.clearAllMocks();
});

test("PURC-TDD-002 (PURC-011-TC1, 012-TC1, 004-TC12; CORE-001/002): zero-speed creation refetches and displays all fields", async () => {
	const user = userEvent.setup();
	const created = {
		id: "aef5de6b-046d-48d2-a84b-df6c989643d0",
		name: "牛乳",
		category: "食品",
		speed: 0,
		stock: 2,
		is_temporary: false,
		created_at: "2026-09-27T00:00:00Z",
		updated_at: "2026-09-27T00:00:00Z",
	};
	vi.mocked(createPurchase).mockResolvedValue(created);
	vi.mocked(getAllPurchases)
		.mockResolvedValueOnce([])
		.mockResolvedValueOnce([created]);

	render(
		<QueryClientProvider client={queryClient}>
			<Purchase />
		</QueryClientProvider>,
	);
	await screen.findByText("まだ登録されていません");
	await user.click(screen.getByRole("button", { name: "追加" }));
	await user.type(screen.getByLabelText("名前"), "牛乳");
	await user.type(screen.getByLabelText("カテゴリ"), "食品");
	await user.clear(screen.getByLabelText(/消費スピード/));
	await user.type(screen.getByLabelText(/消費スピード/), "0");
	await user.clear(screen.getByLabelText("現在の在庫"));
	await user.type(screen.getByLabelText("現在の在庫"), "2");
	await user.click(screen.getByRole("button", { name: "登録する" }));

	await waitFor(() =>
		expect(createPurchase).toHaveBeenCalledWith({
			name: "牛乳",
			category: "食品",
			speed: 0,
			stock: 2,
			is_temporary: false,
		}),
	);
	await waitFor(() => expect(getAllPurchases).toHaveBeenCalledTimes(2));
	const item = screen.getByText("牛乳").closest("li");
	expect(item).not.toBeNull();
	expect(item).toHaveTextContent("食品");
	expect(item).toHaveTextContent(/消費スピード\s*0/);
	expect(item).toHaveTextContent(/在庫\s*2/);
});

test("PURC-012-TC2/3: temporary badge appears only for temporary purchases", async () => {
	const temporary = {
		id: "aef5de6b-046d-48d2-a84b-df6c989643d0",
		name: "旅行用シャンプー",
		category: "日用品",
		speed: 0,
		stock: 1,
		is_temporary: true,
		created_at: "2026-09-27T00:00:00Z",
		updated_at: "2026-09-27T00:00:00Z",
	};
	const regular = {
		...temporary,
		id: "b1fd5e6b-046d-48d2-a84b-df6c989643d0",
		name: "牛乳",
		is_temporary: false,
	};
	vi.mocked(getAllPurchases).mockResolvedValue([temporary, regular]);

	render(
		<QueryClientProvider client={queryClient}>
			<Purchase />
		</QueryClientProvider>,
	);

	const temporaryItem = (await screen.findByText("旅行用シャンプー")).closest(
		"li",
	);
	const regularItem = screen.getByText("牛乳").closest("li");
	expect(temporaryItem).toHaveTextContent("一時的");
	expect(regularItem).not.toHaveTextContent("一時的");
});
