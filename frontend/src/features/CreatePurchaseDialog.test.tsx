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

test("PURC-TDD-003 (PURC-003-TC1; CORE-002): whitespace-only name shows a field error without sending", async () => {
	const user = userEvent.setup();
	render(
		<QueryClientProvider client={queryClient}>
			<CreatePurchaseDialog open onOpenChange={vi.fn()} />
		</QueryClientProvider>,
	);

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
