import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { deletePurchase, type PurchaseResponse } from "@/api/purchases";
import { DeletePurchaseDialog } from "@/features/DeletePurchaseDialog";
import { queryClientWrapper, setUpIsolatedQueryClient } from "@/test-utils";

vi.mock("@/api/purchases", async (importOriginal) => ({
	...(await importOriginal<typeof import("@/api/purchases")>()),
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

describe("DeletePurchaseDialog", () => {
	it("DEL-01: purchaseがnullならダイアログは表示されない", () => {
		render(<DeletePurchaseDialog purchase={null} onOpenChange={vi.fn()} />, {
			wrapper: queryClientWrapper,
		});

		expect(
			screen.queryByText("購入物を削除しますか？"),
		).not.toBeInTheDocument();
	});

	it("DEL-02: 確認文言にpurchase.nameが含まれる", () => {
		render(
			<DeletePurchaseDialog
				purchase={purchaseFixture}
				onOpenChange={vi.fn()}
			/>,
			{ wrapper: queryClientWrapper },
		);

		expect(screen.getByText(/「卵」を削除します。/)).toBeInTheDocument();
	});

	it("DEL-03: キャンセルではdeletePurchaseは呼ばれず閉じる方向で呼ばれる", async () => {
		const user = userEvent.setup();
		const onOpenChange = vi.fn();
		render(
			<DeletePurchaseDialog
				purchase={purchaseFixture}
				onOpenChange={onOpenChange}
			/>,
			{ wrapper: queryClientWrapper },
		);

		await user.click(screen.getByRole("button", { name: "キャンセル" }));

		expect(deletePurchase).not.toHaveBeenCalled();
		expect(onOpenChange).toHaveBeenCalledWith(false);
	});

	it("DEL-04: 削除確定でdeletePurchaseが呼ばれ、成功後onOpenChange(false)が呼ばれる", async () => {
		const user = userEvent.setup();
		vi.mocked(deletePurchase).mockResolvedValueOnce(undefined);
		const onOpenChange = vi.fn();
		render(
			<DeletePurchaseDialog
				purchase={purchaseFixture}
				onOpenChange={onOpenChange}
			/>,
			{ wrapper: queryClientWrapper },
		);

		await user.click(screen.getByRole("button", { name: "削除する" }));

		// deletePurchaseはmutationFnとして直接渡されており、tanstack-queryが
		// 第2引数（mutationFnContext）を付与して呼び出すため、第1引数のみ検証する。
		expect(vi.mocked(deletePurchase).mock.calls[0]?.[0]).toBe("p1");
		await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
	});

	it("DEL-05: 失敗時は「削除に失敗しました」が表示され閉じない", async () => {
		const user = userEvent.setup();
		vi.mocked(deletePurchase).mockRejectedValueOnce(new Error("fail"));
		const onOpenChange = vi.fn();
		render(
			<DeletePurchaseDialog
				purchase={purchaseFixture}
				onOpenChange={onOpenChange}
			/>,
			{ wrapper: queryClientWrapper },
		);

		await user.click(screen.getByRole("button", { name: "削除する" }));

		expect(await screen.findByText("削除に失敗しました")).toBeInTheDocument();
		expect(onOpenChange).not.toHaveBeenCalledWith(false);
	});

	it("DEL-06: 送信中はキャンセル・削除ボタンが無効化され「削除中...」になる", async () => {
		const user = userEvent.setup();
		let resolvePromise: (value: undefined) => void = () => {};
		vi.mocked(deletePurchase).mockReturnValueOnce(
			new Promise((resolve) => {
				resolvePromise = resolve;
			}),
		);
		render(
			<DeletePurchaseDialog
				purchase={purchaseFixture}
				onOpenChange={vi.fn()}
			/>,
			{ wrapper: queryClientWrapper },
		);

		await user.click(screen.getByRole("button", { name: "削除する" }));

		await waitFor(() =>
			expect(screen.getByRole("button", { name: "削除中..." })).toBeDisabled(),
		);
		expect(screen.getByRole("button", { name: "キャンセル" })).toBeDisabled();

		resolvePromise(undefined);
		await waitFor(() =>
			expect(
				screen.getByRole("button", { name: "削除する" }),
			).not.toBeDisabled(),
		);
	});
});
