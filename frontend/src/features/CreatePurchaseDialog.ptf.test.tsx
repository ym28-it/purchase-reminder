// Pre-implementation TDD tests for purchase-timing-fields (PTF-TDD-013, PTF-TDD-014).
// Approved inputs: docs/superpowers/specs/2026-11-12-purchase-timing-fields-design.md,
// ...-test-cases.md and ...-tdd-plan.md (PTF-CORE-008). Expected results come from the
// logical test cases only. The HTTP layer is mocked (globalThis.fetch), so the real
// api/hooks/component chain is exercised.
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

type User = ReturnType<typeof userEvent.setup>;

let postBodies: unknown[];

function json(status: number, body: unknown): Response {
	return new Response(JSON.stringify(body), {
		status,
		headers: { "Content-Type": "application/json" },
	});
}

beforeEach(() => {
	queryClient.clear();
	postBodies = [];
	fetchMock.mockImplementation(async (request: Request) => {
		if (request.method === "POST") {
			const body = JSON.parse(await request.clone().text());
			postBodies.push(body);
			return json(201, {
				id: "aef5de6b-046d-48d2-a84b-df6c989643d0",
				stock_counted_at: "2026-11-22T00:00:00Z",
				created_at: "2026-11-22T00:00:00Z",
				updated_at: "2026-11-22T00:00:00Z",
				...body,
			});
		}
		return json(200, []);
	});
});

afterEach(() => {
	cleanup();
	queryClient.clear();
	fetchMock.mockReset();
});

async function openDialog(user: User): Promise<HTMLElement> {
	render(
		<QueryClientProvider client={queryClient}>
			<Purchase />
		</QueryClientProvider>,
	);
	await user.click(await screen.findByRole("button", { name: "追加" }));
	return screen.findByRole("dialog");
}

async function type(user: User, input: HTMLElement, value: string) {
	await user.clear(input);
	await user.click(input);
	await user.paste(value);
}

test("PTF-TDD-013 (PTF-001-TC1; PTF-CORE-008): the create dialog has the seven fields", async () => {
	const user = userEvent.setup();
	const dialog = await openDialog(user);

	expect(within(dialog).getByLabelText(/^名前$/)).toBeInTheDocument();
	expect(within(dialog).getByLabelText(/^カテゴリ$/)).toBeInTheDocument();
	expect(within(dialog).getByLabelText(/^購入単位/)).toBeInTheDocument();
	expect(within(dialog).getByLabelText(/使い切る日数/)).toBeInTheDocument();
	expect(within(dialog).getByLabelText(/余裕日数/)).toBeInTheDocument();
	expect(within(dialog).getByLabelText(/^在庫/)).toBeInTheDocument();
	expect(within(dialog).getByLabelText(/一時的な購入/)).toBeInTheDocument();
});

test("PTF-TDD-014 (PTF-003-TC5; PTF-CORE-008): untouched buffer days is sent as 0", async () => {
	const user = userEvent.setup();
	const dialog = await openDialog(user);

	await type(user, within(dialog).getByLabelText(/^名前$/), "牛乳");
	await type(user, within(dialog).getByLabelText(/^カテゴリ$/), "食品");
	await type(user, within(dialog).getByLabelText(/^購入単位/), "パック");
	await type(user, within(dialog).getByLabelText(/使い切る日数/), "3");
	await type(user, within(dialog).getByLabelText(/^在庫/), "2");
	await user.click(within(dialog).getByRole("button", { name: "登録する" }));

	await waitFor(() => expect(postBodies).toHaveLength(1));
	expect(postBodies[0]).toEqual({
		name: "牛乳",
		category: "食品",
		unit: "パック",
		days_per_unit: 3,
		buffer_days: 0,
		stock: 2,
		is_temporary: false,
	});
});
