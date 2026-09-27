import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import { createPurchase } from "@/api/purchases";
import { queryClient } from "@/api/queryClient";
import { CreatePurchaseDialog } from "@/features/CreatePurchaseDialog";

vi.mock("@/api/purchases", () => ({ createPurchase: vi.fn() }));

afterEach(() => {
	queryClient.clear();
	vi.clearAllMocks();
});

function renderDialog(onOpenChange = vi.fn()) {
	render(
		<QueryClientProvider client={queryClient}>
			<CreatePurchaseDialog open onOpenChange={onOpenChange} />
		</QueryClientProvider>,
	);
	return onOpenChange;
}

async function fillValidForm(user: ReturnType<typeof userEvent.setup>) {
	await user.type(screen.getByLabelText("名前"), "牛乳");
	await user.type(screen.getByLabelText("カテゴリ"), "食品");
	await user.clear(screen.getByLabelText(/消費スピード/));
	await user.type(screen.getByLabelText(/消費スピード/), "1");
	await user.clear(screen.getByLabelText("現在の在庫"));
	await user.type(screen.getByLabelText("現在の在庫"), "2");
}

test("PURC-TDD-003 (PURC-003-TC1; CORE-002): whitespace-only name shows a field error without sending", async () => {
	const user = userEvent.setup();
	renderDialog();

	await user.type(screen.getByLabelText("名前"), "   ");
	await user.type(screen.getByLabelText("カテゴリ"), "食品");
	await user.clear(screen.getByLabelText(/消費スピード/));
	await user.type(screen.getByLabelText(/消費スピード/), "1");
	await user.click(screen.getByRole("button", { name: "登録する" }));

	const nameField = screen.getByLabelText("名前").parentElement;
	await waitFor(() =>
		expect(nameField?.querySelector("p")?.textContent).toBeTruthy(),
	);
	expect(createPurchase).not.toHaveBeenCalled();
});

test("PURC-001-TC1, PURC-002-TC1/2: form exposes five fields with approved defaults", () => {
	renderDialog();
	expect(screen.getByLabelText("名前")).toHaveValue("");
	expect(screen.getByLabelText("カテゴリ")).toHaveValue("");
	expect(screen.getByLabelText(/消費スピード/)).toHaveValue(0);
	expect(screen.getByLabelText("現在の在庫")).toHaveValue(0);
	expect(screen.getByLabelText(/一時的な購入/)).not.toBeChecked();
});

test.each([
	["名前", "x".repeat(51)],
	["カテゴリ", "x".repeat(31)],
	["消費スピード（個/日）", "-1"],
	["消費スピード（個/日）", "1.5"],
	["消費スピード（個/日）", "100001"],
	["現在の在庫", "-1"],
	["現在の在庫", "1.5"],
	["現在の在庫", "100001"],
])("PURC-003-TC1/PURC-004: invalid %s is blocked client-side", async (label, value) => {
	const user = userEvent.setup();
	renderDialog();
	await fillValidForm(user);
	const field = screen.getByLabelText(label);
	await user.clear(field);
	await user.type(field, value);
	await user.click(screen.getByRole("button", { name: "登録する" }));
	await waitFor(() => expect(field.parentElement?.querySelector("p")).not.toBeNull());
	expect(createPurchase).not.toHaveBeenCalled();
});

test("PURC-010-TC1/2: success closes the dialog and resets values", async () => {
	const user = userEvent.setup();
	const onOpenChange = renderDialog();
	vi.mocked(createPurchase).mockResolvedValue({
		id: "aef5de6b-046d-48d2-a84b-df6c989643d0",
		name: "牛乳",
		category: "食品",
		speed: 1,
		stock: 2,
		is_temporary: false,
		created_at: "2026-09-27T00:00:00Z",
		updated_at: "2026-09-27T00:00:00Z",
	});
	await fillValidForm(user);
	await user.click(screen.getByRole("button", { name: "登録する" }));
	await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
	await waitFor(() => expect(screen.getByLabelText("名前")).toHaveValue(""));
	expect(screen.getByLabelText("カテゴリ")).toHaveValue("");
	expect(screen.getByLabelText(/消費スピード/)).toHaveValue(0);
	expect(screen.getByLabelText("現在の在庫")).toHaveValue(0);
});

test("PURC-015-TC1/PURC-016-TC1: duplicate error keeps input and identifies duplicate", async () => {
	const user = userEvent.setup();
	const onOpenChange = renderDialog();
	vi.mocked(createPurchase).mockRejectedValue({
		detail: "同じ名前とカテゴリの購入物は既に存在します",
	});
	await fillValidForm(user);
	await user.click(screen.getByRole("button", { name: "登録する" }));
	expect(await screen.findByText("同じ名前とカテゴリの購入物は既に存在します")).toBeInTheDocument();
	expect(onOpenChange).not.toHaveBeenCalledWith(false);
	expect(screen.getByLabelText("名前")).toHaveValue("牛乳");
	expect(screen.getByLabelText("カテゴリ")).toHaveValue("食品");
	expect(screen.getByLabelText(/消費スピード/)).toHaveValue(1);
	expect(screen.getByLabelText("現在の在庫")).toHaveValue(2);
});

test("PURC-017-TC1/2, PURC-018-TC1/2: generic failure is safe, not retried, and manual retry works", async () => {
	const user = userEvent.setup();
	renderDialog();
	vi.mocked(createPurchase)
		.mockRejectedValueOnce(new Error("internal stack secret"))
		.mockResolvedValueOnce({
			id: "aef5de6b-046d-48d2-a84b-df6c989643d0",
			name: "牛乳",
			category: "食品",
			speed: 1,
			stock: 2,
			is_temporary: false,
			created_at: "2026-09-27T00:00:00Z",
			updated_at: "2026-09-27T00:00:00Z",
		});
	await fillValidForm(user);
	await user.click(screen.getByRole("button", { name: "登録する" }));
	expect(await screen.findByText("登録に失敗しました")).toBeInTheDocument();
	expect(screen.queryByText(/internal stack secret/)).not.toBeInTheDocument();
	await new Promise((resolve) => setTimeout(resolve, 20));
	expect(createPurchase).toHaveBeenCalledTimes(1);
	await user.click(screen.getByRole("button", { name: "登録する" }));
	await waitFor(() => expect(createPurchase).toHaveBeenCalledTimes(2));
});


test("PURC-013-TC1: submit is disabled while the create request is pending", async () => {
	const user = userEvent.setup();
	renderDialog();
	vi.mocked(createPurchase).mockImplementation(
		() => new Promise(() => undefined),
	);
	await fillValidForm(user);
	const submit = screen.getByRole("button", { name: "登録する" });
	await user.click(submit);
	await waitFor(() =>
		expect(screen.getByRole("button", { name: "登録中..." })).toBeDisabled(),
	);
	expect(createPurchase).toHaveBeenCalledTimes(1);
});
