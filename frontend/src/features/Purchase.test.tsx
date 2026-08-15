import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getAllPurchases, type PurchaseResponse } from "@/api/purchases";
import { Purchase } from "@/features/Purchase";
import { queryClientWrapper, setUpIsolatedQueryClient } from "@/test-utils";

vi.mock("@/api/purchases", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/api/purchases")>()),
	createPurchase: vi.fn(),
	putPurchase: vi.fn(),
	getAllPurchases: vi.fn(),
	deletePurchase: vi.fn(),
}));

const eggPurchase: PurchaseResponse = {
	id: "p1",
	name: "卵",
	category: "食品",
	speed: 42,
	stock: 5,
	is_temporary: false,
	created_at: "2026-08-01T00:00:00Z",
	updated_at: "2026-08-01T00:00:00Z",
};

const tempPurchase: PurchaseResponse = {
	id: "p2",
	name: "電池",
	category: "日用品",
	speed: 0.5,
	stock: 2,
	is_temporary: true,
	created_at: "2026-08-01T00:00:00Z",
	updated_at: "2026-08-01T00:00:00Z",
};

setUpIsolatedQueryClient();

beforeEach(() => {
	vi.clearAllMocks();
});

function renderPurchase() {
	render(<Purchase />, { wrapper: queryClientWrapper });
}

describe("Purchase", () => {
	it("PUR-01: ローディング中は「読み込み中...」が表示される", () => {
		vi.mocked(getAllPurchases).mockReturnValue(new Promise(() => {}));

		renderPurchase();

		expect(screen.getAllByText("読み込み中...").length).toBeGreaterThan(0);
	});

	it("PUR-02: 0件のとき空状態メッセージが表示される", async () => {
		vi.mocked(getAllPurchases).mockResolvedValueOnce([]);

		renderPurchase();

		expect(
			await screen.findByText("まだ登録されていません"),
		).toBeInTheDocument();
	});

	it("PUR-03: 件数がヘッダーに表示される", async () => {
		vi.mocked(getAllPurchases).mockResolvedValueOnce([
			eggPurchase,
			tempPurchase,
		]);

		renderPurchase();

		expect(await screen.findByText("2件")).toBeInTheDocument();
	});

	it("PUR-04: 一覧行にname/category/stockが表示される", async () => {
		vi.mocked(getAllPurchases).mockResolvedValueOnce([eggPurchase]);

		renderPurchase();

		expect(await screen.findByText("卵")).toBeInTheDocument();
		expect(screen.getByText("食品")).toBeInTheDocument();
		expect(screen.getByText("在庫 5")).toBeInTheDocument();
	});

	it("PUR-05: is_temporaryがtrueの行にのみ「一時的」バッジが表示される", async () => {
		vi.mocked(getAllPurchases).mockResolvedValueOnce([
			eggPurchase,
			tempPurchase,
		]);

		renderPurchase();
		await screen.findByText("卵");

		const eggRow = screen.getByText("卵").closest("li");
		const tempRow = screen.getByText("電池").closest("li");
		expect(eggRow).not.toBeNull();
		expect(tempRow).not.toBeNull();
		expect(within(eggRow as HTMLElement).queryByText("一時的")).toBeNull();
		expect(
			within(tempRow as HTMLElement).getByText("一時的"),
		).toBeInTheDocument();
	});

	it("PUR-06: speedの値は一覧に表示されない", async () => {
		vi.mocked(getAllPurchases).mockResolvedValueOnce([eggPurchase]);

		renderPurchase();
		await screen.findByText("卵");

		expect(screen.queryByText("42")).not.toBeInTheDocument();
	});

	it("PUR-07: 編集ボタンで対象行の値が入った編集ダイアログが開く", async () => {
		const user = userEvent.setup();
		vi.mocked(getAllPurchases).mockResolvedValueOnce([eggPurchase]);

		renderPurchase();
		await screen.findByText("卵");

		await user.click(screen.getByRole("button", { name: "編集" }));

		expect(await screen.findByText("購入物を編集")).toBeInTheDocument();
		expect(screen.getByLabelText("名前")).toHaveValue("卵");
		expect(screen.getByLabelText("現在の在庫")).toHaveValue(5);
	});

	it("PUR-08: 削除ボタンで対象行の名前を含む確認ダイアログが開く", async () => {
		const user = userEvent.setup();
		vi.mocked(getAllPurchases).mockResolvedValueOnce([eggPurchase]);

		renderPurchase();
		await screen.findByText("卵");

		await user.click(screen.getByRole("button", { name: "削除" }));

		expect(
			await screen.findByText("購入物を削除しますか？"),
		).toBeInTheDocument();
		expect(screen.getByText(/「卵」を削除します。/)).toBeInTheDocument();
	});

	it("PUR-09: 追加ボタンで追加ダイアログが開く", async () => {
		const user = userEvent.setup();
		vi.mocked(getAllPurchases).mockResolvedValueOnce([]);

		renderPurchase();
		await screen.findByText("まだ登録されていません");

		await user.click(screen.getByRole("button", { name: "追加" }));

		expect(await screen.findByText("購入物を追加")).toBeInTheDocument();
	});

	it("PUR-10: 編集ダイアログを閉じて別行を編集すると新しい行の値になる", async () => {
		const user = userEvent.setup();
		vi.mocked(getAllPurchases).mockResolvedValueOnce([
			eggPurchase,
			tempPurchase,
		]);

		renderPurchase();
		await screen.findByText("卵");

		const editButtons = screen.getAllByRole("button", { name: "編集" });
		await user.click(editButtons[0]);
		expect(await screen.findByLabelText("名前")).toHaveValue("卵");

		await user.click(screen.getByRole("button", { name: "Close" }));
		await waitFor(() =>
			expect(screen.queryByText("購入物を編集")).not.toBeInTheDocument(),
		);

		await user.click(editButtons[1]);
		expect(await screen.findByLabelText("名前")).toHaveValue("電池");
	});
});
