import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPurchase, type PurchaseResponse } from "@/api/purchases";
import { CreatePurchaseDialog } from "@/features/CreatePurchaseDialog";
import { queryClientWrapper, setUpIsolatedQueryClient } from "@/test-utils";

vi.mock("@/api/purchases", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/api/purchases")>()),
	createPurchase: vi.fn(),
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

function renderDialog(onOpenChange = vi.fn()) {
	render(<CreatePurchaseDialog open={true} onOpenChange={onOpenChange} />, {
		wrapper: queryClientWrapper,
	});
	return { onOpenChange };
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
	await user.type(screen.getByLabelText("名前"), "卵");
	await user.type(screen.getByLabelText("カテゴリ"), "食品");
	const speedInput = screen.getByLabelText("消費スピード（個/日）");
	await user.clear(speedInput);
	await user.type(speedInput, "2");
}

describe("CreatePurchaseDialog", () => {
	it("CRE-01: 初期値は空/0、一時的チェックは未チェック", () => {
		renderDialog();

		expect(screen.getByLabelText("名前")).toHaveValue("");
		expect(screen.getByLabelText("カテゴリ")).toHaveValue("");
		expect(screen.getByLabelText("消費スピード（個/日）")).toHaveValue(0);
		expect(screen.getByLabelText("現在の在庫")).toHaveValue(0);
		expect(
			screen.getByRole("checkbox", { name: "一時的な購入（定期購入しない）" }),
		).not.toBeChecked();
	});

	it("CRE-02: nameが空だと「名前を入力してください」が表示され送信されない", async () => {
		const user = userEvent.setup();
		renderDialog();

		await user.click(screen.getByRole("button", { name: "登録する" }));

		expect(
			await screen.findByText("名前を入力してください"),
		).toBeInTheDocument();
		expect(createPurchase).not.toHaveBeenCalled();
	});

	it("CRE-03: categoryが空だと「カテゴリを入力してください」が表示される", async () => {
		const user = userEvent.setup();
		renderDialog();

		await user.type(screen.getByLabelText("名前"), "卵");
		await user.click(screen.getByRole("button", { name: "登録する" }));

		expect(
			await screen.findByText("カテゴリを入力してください"),
		).toBeInTheDocument();
		expect(createPurchase).not.toHaveBeenCalled();
	});

	it("CRE-04: speedが0だと「0より大きい値を入力してください」が表示される", async () => {
		const user = userEvent.setup();
		renderDialog();

		await user.type(screen.getByLabelText("名前"), "卵");
		await user.type(screen.getByLabelText("カテゴリ"), "食品");
		await user.click(screen.getByRole("button", { name: "登録する" }));

		expect(
			await screen.findByText("0より大きい値を入力してください"),
		).toBeInTheDocument();
		expect(createPurchase).not.toHaveBeenCalled();
	});

	it("CRE-05: speedが負数だとエラーが表示される", async () => {
		const user = userEvent.setup();
		renderDialog();

		await user.type(screen.getByLabelText("名前"), "卵");
		await user.type(screen.getByLabelText("カテゴリ"), "食品");
		const speedInput = screen.getByLabelText("消費スピード（個/日）");
		await user.clear(speedInput);
		await user.type(speedInput, "-1");
		await user.click(screen.getByRole("button", { name: "登録する" }));

		expect(
			await screen.findByText("0より大きい値を入力してください"),
		).toBeInTheDocument();
		expect(createPurchase).not.toHaveBeenCalled();
	});

	it("CRE-06: stockが負数だと「0以上を入力してください」が表示される", async () => {
		const user = userEvent.setup();
		renderDialog();

		await fillValidForm(user);
		const stockInput = screen.getByLabelText("現在の在庫");
		await user.clear(stockInput);
		await user.type(stockInput, "-1");
		await user.click(screen.getByRole("button", { name: "登録する" }));

		expect(
			await screen.findByText("0以上を入力してください"),
		).toBeInTheDocument();
		expect(createPurchase).not.toHaveBeenCalled();
	});

	it("CRE-07: stockが0は許容される", async () => {
		const user = userEvent.setup();
		vi.mocked(createPurchase).mockResolvedValueOnce(purchaseFixture);
		renderDialog();

		await fillValidForm(user);
		await user.click(screen.getByRole("button", { name: "登録する" }));

		await waitFor(() => expect(createPurchase).toHaveBeenCalledTimes(1));
		expect(
			screen.queryByText("0以上を入力してください"),
		).not.toBeInTheDocument();
	});

	it("CRE-08: 正常送信でis_temporaryにキー変換されてcreatePurchaseが呼ばれる", async () => {
		const user = userEvent.setup();
		vi.mocked(createPurchase).mockResolvedValueOnce(purchaseFixture);
		renderDialog();

		await fillValidForm(user);
		const stockInput = screen.getByLabelText("現在の在庫");
		await user.clear(stockInput);
		await user.type(stockInput, "3");
		await user.click(
			screen.getByRole("checkbox", { name: "一時的な購入（定期購入しない）" }),
		);
		await user.click(screen.getByRole("button", { name: "登録する" }));

		// createPurchaseはmutationFnとして直接渡されており、tanstack-queryが
		// 第2引数（mutationFnContext）を付与して呼び出すため、第1引数のみ検証する。
		await waitFor(() =>
			expect(vi.mocked(createPurchase).mock.calls[0]?.[0]).toEqual({
				name: "卵",
				category: "食品",
				speed: 2,
				stock: 3,
				is_temporary: true,
			}),
		);
	});

	it("CRE-09: 成功時にフォームがresetされダイアログが閉じる", async () => {
		const user = userEvent.setup();
		vi.mocked(createPurchase).mockResolvedValueOnce(purchaseFixture);
		const { onOpenChange } = renderDialog();

		await fillValidForm(user);
		await user.click(screen.getByRole("button", { name: "登録する" }));

		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
		expect(screen.getByLabelText("名前")).toHaveValue("");
	});

	it("CRE-10: 失敗時は「登録に失敗しました」が表示され閉じない", async () => {
		const user = userEvent.setup();
		vi.mocked(createPurchase).mockRejectedValueOnce(new Error("fail"));
		const { onOpenChange } = renderDialog();

		await fillValidForm(user);
		await user.click(screen.getByRole("button", { name: "登録する" }));

		expect(await screen.findByText("登録に失敗しました")).toBeInTheDocument();
		expect(onOpenChange).not.toHaveBeenCalledWith(false);
	});

	it("CRE-11: キャンセル（閉じる操作）で入力内容がresetされる", async () => {
		const user = userEvent.setup();
		const { onOpenChange } = renderDialog();

		await user.type(screen.getByLabelText("名前"), "書きかけ");
		await user.click(screen.getByRole("button", { name: "Close" }));

		expect(onOpenChange).toHaveBeenCalledWith(false);
		expect(screen.getByLabelText("名前")).toHaveValue("");
	});

	it("CRE-12: 送信中は登録ボタンが無効化され「登録中...」になる", async () => {
		const user = userEvent.setup();
		let resolvePromise: (value: PurchaseResponse) => void = () => {};
		vi.mocked(createPurchase).mockReturnValueOnce(
			new Promise((resolve) => {
				resolvePromise = resolve;
			}),
		);
		renderDialog();

		await fillValidForm(user);
		await user.click(screen.getByRole("button", { name: "登録する" }));

		await waitFor(() =>
			expect(screen.getByRole("button", { name: "登録中..." })).toBeDisabled(),
		);

		resolvePromise(purchaseFixture);
		await waitFor(() =>
			expect(
				screen.getByRole("button", { name: "登録する" }),
			).not.toBeDisabled(),
		);
	});
});
