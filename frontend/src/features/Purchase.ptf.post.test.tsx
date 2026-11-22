// Post-implementation component coverage for purchase-timing-fields.
// Expected results come from docs/superpowers/specs/2026-11-12-purchase-timing-fields-test-cases.md
// only (PTF-009-TC1, PTF-012-TC2). The HTTP layer is mocked (globalThis.fetch).
import { QueryClientProvider } from "@tanstack/react-query";
import {
	cleanup,
	render,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

// openapi-fetch captures globalThis.fetch when src/api/client.ts is imported,
// so the mock must be installed before any app module is loaded.
const fetchMock = vi.hoisted(() => {
	const mock = vi.fn<(request: Request) => Promise<Response>>();
	globalThis.fetch = mock as unknown as typeof fetch;
	return mock;
});

import { queryClient } from "@/api/queryClient";
import { Purchase } from "@/features/Purchase";

const purchase = {
	id: "aef5de6b-046d-48d2-a84b-df6c989643d0",
	name: "牛乳",
	category: "食品",
	unit: "パック",
	days_per_unit: 3,
	buffer_days: 2,
	stock: 2,
	is_temporary: true,
	stock_counted_at: "2026-11-21T08:09:10Z",
	created_at: "2026-11-22T00:00:00Z",
	updated_at: "2026-11-22T00:00:00Z",
};

beforeEach(() => {
	queryClient.clear();
	fetchMock.mockImplementation(
		async () =>
			new Response(JSON.stringify([purchase]), {
				status: 200,
				headers: { "Content-Type": "application/json" },
			}),
	);
});

afterEach(() => {
	cleanup();
	queryClient.clear();
	fetchMock.mockReset();
});

function renderList() {
	render(
		<QueryClientProvider client={queryClient}>
			<Purchase />
		</QueryClientProvider>,
	);
}

test("PTF-009-TC1: the list shows every registered field but not stock_counted_at", async () => {
	renderList();

	const item = (await screen.findByText("牛乳")).closest("li");
	expect(item).not.toBeNull();
	expect(item).toHaveTextContent("食品");
	expect(item).toHaveTextContent("パック");
	expect(item).toHaveTextContent("1パック3日");
	expect(item).toHaveTextContent(/余裕\s*2日/);
	expect(item).toHaveTextContent("2パック");
	expect(item).toHaveTextContent("一時的");
	expect(item).not.toHaveTextContent("2026-11-21");
	expect(item).not.toHaveTextContent("08:09");
});

test("PTF-012-TC2: the edit dialog shows the saved days per unit", async () => {
	const user = userEvent.setup();
	renderList();
	const item = (await screen.findByText("牛乳")).closest("li") as HTMLElement;

	await user.click(within(item).getByRole("button", { name: "編集" }));

	const dialog = await screen.findByRole("dialog");
	expect(within(dialog).getByLabelText(/使い切る日数/)).toHaveValue(3);
});

test("PTF-012-TC1 (UI side): saving an edit sends days_per_unit and never unit or buffer_days", async () => {
	const putBodies: unknown[] = [];
	fetchMock.mockImplementation(async (request: Request) => {
		if (request.method === "PUT") {
			putBodies.push(JSON.parse(await request.clone().text()));
			return new Response(JSON.stringify({ ...purchase, days_per_unit: 5 }), {
				status: 200,
				headers: { "Content-Type": "application/json" },
			});
		}
		return new Response(JSON.stringify([purchase]), {
			status: 200,
			headers: { "Content-Type": "application/json" },
		});
	});
	const user = userEvent.setup();
	renderList();
	const item = (await screen.findByText("牛乳")).closest("li") as HTMLElement;
	await user.click(within(item).getByRole("button", { name: "編集" }));
	const dialog = await screen.findByRole("dialog");

	const days = within(dialog).getByLabelText(/使い切る日数/);
	await user.clear(days);
	await user.type(days, "5");
	await user.click(within(dialog).getByRole("button", { name: /保存|更新/ }));

	await waitFor(() => expect(putBodies).toHaveLength(1));
	expect(putBodies[0]).toEqual({
		name: "牛乳",
		category: "食品",
		days_per_unit: 5,
		stock: 2,
		is_temporary: true,
	});
});
