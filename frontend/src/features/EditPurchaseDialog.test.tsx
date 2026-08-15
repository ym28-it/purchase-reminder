import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { type PurchaseResponse, putPurchase } from "@/api/purchases";
import { EditPurchaseDialog } from "@/features/EditPurchaseDialog";
import { queryClientWrapper, setUpIsolatedQueryClient } from "@/test-utils";

vi.mock("@/api/purchases", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/api/purchases")>()),
	putPurchase: vi.fn(),
}));

const purchaseFixture: PurchaseResponse = {
	id: "p1",
	name: "卵",
	category: "食品",
	speed: 1.5,
	stock: 5,
	is_temporary: false,
	created_at: "2026-08-01T00:00:00Z",
	updated_at: "2026-08-01T00:00:00Z",
};

const otherPurchaseFixture: PurchaseResponse = {
	id: "p2",
	name: "牛乳",
	category: "食品",
	speed: 2,
	stock: 1,
	is_temporary: true,
	created_at: "2026-08-01T00:00:00Z",
	updated_at: "2026-08-01T00:00:00Z",
};

setUpIsolatedQueryClient();

beforeEach(() => {
	vi.clearAllMocks();
});

describe("EditPurchaseDialog", () => {
	it("EDIT-01: purchaseがnullならダイアログは表示されない", () => {
		const onOpenChange = vi.fn();
		render(<EditPurchaseDialog purchase={null} onOpenChange={onOpenChange} />, {
			wrapper: queryClientWrapper,
		});

		expect(screen.queryByText("購入物を編集")).not.toBeInTheDocument();
		expect(
			screen.queryByRole("button", { name: "更新する" }),
		).not.toBeInTheDocument();
	});

	it("EDIT-02: purchaseの値でフォームが初期化される", () => {
		render(
			<EditPurchaseDialog purchase={purchaseFixture} onOpenChange={vi.fn()} />,
			{ wrapper: queryClientWrapper },
		);

		expect(screen.getByLabelText("名前")).toHaveValue("卵");
		expect(screen.getByLabelText("カテゴリ")).toHaveValue("食品");
		expect(screen.getByLabelText("消費スピード（個/日）")).toHaveValue(1.5);
		expect(screen.getByLabelText("現在の在庫")).toHaveValue(5);
		expect(
			screen.getByRole("checkbox", { name: "一時的な購入（定期購入しない）" }),
		).not.toBeChecked();
	});

	it("EDIT-03: purchaseが切り替わるとフォーム表示値も再同期される", () => {
		const { rerender } = render(
			<EditPurchaseDialog purchase={purchaseFixture} onOpenChange={vi.fn()} />,
			{ wrapper: queryClientWrapper },
		);
		expect(screen.getByLabelText("名前")).toHaveValue("卵");

		rerender(
			<EditPurchaseDialog
				purchase={otherPurchaseFixture}
				onOpenChange={vi.fn()}
			/>,
		);

		expect(screen.getByLabelText("名前")).toHaveValue("牛乳");
		expect(screen.getByLabelText("現在の在庫")).toHaveValue(1);
		expect(
			screen.getByRole("checkbox", { name: "一時的な購入（定期購入しない）" }),
		).toBeChecked();
	});

	it("EDIT-04a: nameが空だと「名前を入力してください」が表示される", async () => {
		const user = userEvent.setup();
		render(
			<EditPurchaseDialog purchase={purchaseFixture} onOpenChange={vi.fn()} />,
			{ wrapper: queryClientWrapper },
		);

		await user.clear(screen.getByLabelText("名前"));
		await user.click(screen.getByRole("button", { name: "更新する" }));

		expect(
			await screen.findByText("名前を入力してください"),
		).toBeInTheDocument();
		expect(putPurchase).not.toHaveBeenCalled();
	});

	it("EDIT-04b: speedが0だとエラーが表示される", async () => {
		const user = userEvent.setup();
		render(
			<EditPurchaseDialog purchase={purchaseFixture} onOpenChange={vi.fn()} />,
			{ wrapper: queryClientWrapper },
		);

		const speedInput = screen.getByLabelText("消費スピード（個/日）");
		await user.clear(speedInput);
		await user.type(speedInput, "0");
		await user.click(screen.getByRole("button", { name: "更新する" }));

		expect(
			await screen.findByText("0より大きい値を入力してください"),
		).toBeInTheDocument();
		expect(putPurchase).not.toHaveBeenCalled();
	});

	it("EDIT-04c: stockが負数だとエラーが表示される", async () => {
		const user = userEvent.setup();
		render(
			<EditPurchaseDialog purchase={purchaseFixture} onOpenChange={vi.fn()} />,
			{ wrapper: queryClientWrapper },
		);

		const stockInput = screen.getByLabelText("現在の在庫");
		await user.clear(stockInput);
		await user.type(stockInput, "-1");
		await user.click(screen.getByRole("button", { name: "更新する" }));

		expect(
			await screen.findByText("0以上を入力してください"),
		).toBeInTheDocument();
		expect(putPurchase).not.toHaveBeenCalled();
	});

	it("EDIT-05: 正常送信でputPurchaseがpurchaseIdとinputで呼ばれる", async () => {
		const user = userEvent.setup();
		vi.mocked(putPurchase).mockResolvedValueOnce(purchaseFixture);
		render(
			<EditPurchaseDialog purchase={purchaseFixture} onOpenChange={vi.fn()} />,
			{ wrapper: queryClientWrapper },
		);

		const nameInput = screen.getByLabelText("名前");
		await user.clear(nameInput);
		await user.type(nameInput, "卵(Lサイズ)");
		await user.click(screen.getByRole("button", { name: "更新する" }));

		await waitFor(() =>
			expect(putPurchase).toHaveBeenCalledWith("p1", {
				name: "卵(Lサイズ)",
				category: "食品",
				speed: 1.5,
				stock: 5,
				is_temporary: false,
			}),
		);
	});

	it("EDIT-06: 成功時はonOpenChange(false)のみでresetは呼ばれない", async () => {
		const user = userEvent.setup();
		vi.mocked(putPurchase).mockResolvedValueOnce(purchaseFixture);
		const onOpenChange = vi.fn();
		render(
			<EditPurchaseDialog
				purchase={purchaseFixture}
				onOpenChange={onOpenChange}
			/>,
			{ wrapper: queryClientWrapper },
		);

		const nameInput = screen.getByLabelText("名前");
		await user.clear(nameInput);
		await user.type(nameInput, "卵(Lサイズ)");
		await user.click(screen.getByRole("button", { name: "更新する" }));

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		// reset()されていれば元のpurchase.name（"卵"）に戻るはずだが、
		// 呼ばれていないので編集後の値のまま。
		expect(screen.getByLabelText("名前")).toHaveValue("卵(Lサイズ)");
	});

	it("EDIT-07: 失敗時は「更新に失敗しました」が表示され閉じない", async () => {
		const user = userEvent.setup();
		vi.mocked(putPurchase).mockRejectedValueOnce(new Error("fail"));
		const onOpenChange = vi.fn();
		render(
			<EditPurchaseDialog
				purchase={purchaseFixture}
				onOpenChange={onOpenChange}
			/>,
			{ wrapper: queryClientWrapper },
		);

		await user.click(screen.getByRole("button", { name: "更新する" }));

		expect(await screen.findByText("更新に失敗しました")).toBeInTheDocument();
		expect(onOpenChange).not.toHaveBeenCalledWith(false);
	});

	it("EDIT-09: 送信中は更新ボタンが無効化され「更新中...」になる", async () => {
		const user = userEvent.setup();
		let resolvePromise: (value: PurchaseResponse) => void = () => {};
		vi.mocked(putPurchase).mockReturnValueOnce(
			new Promise((resolve) => {
				resolvePromise = resolve;
			}),
		);
		render(
			<EditPurchaseDialog purchase={purchaseFixture} onOpenChange={vi.fn()} />,
			{ wrapper: queryClientWrapper },
		);

		await user.click(screen.getByRole("button", { name: "更新する" }));

		await waitFor(() =>
			expect(screen.getByRole("button", { name: "更新中..." })).toBeDisabled(),
		);

		resolvePromise(purchaseFixture);
		await waitFor(() =>
			expect(
				screen.getByRole("button", { name: "更新する" }),
			).not.toBeDisabled(),
		);
	});
});
