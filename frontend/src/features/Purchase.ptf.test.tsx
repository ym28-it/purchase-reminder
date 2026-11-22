// Pre-implementation TDD test for purchase-timing-fields (PTF-TDD-015).
// Approved inputs: docs/superpowers/specs/2026-11-12-purchase-timing-fields-design.md,
// ...-test-cases.md and ...-tdd-plan.md (PTF-CORE-009). Expected results come from the
// logical test cases only. The HTTP layer is mocked (globalThis.fetch).
import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
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
	buffer_days: 0,
	stock: 2,
	is_temporary: false,
	stock_counted_at: "2026-11-22T00:00:00Z",
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

test("PTF-TDD-015 (PTF-015-TC2; PTF-CORE-009): the list shows stock and days with the unit", async () => {
	render(
		<QueryClientProvider client={queryClient}>
			<Purchase />
		</QueryClientProvider>,
	);

	const item = (await screen.findByText("牛乳")).closest("li");
	expect(item).not.toBeNull();
	expect(item).toHaveTextContent("2パック");
	expect(item).toHaveTextContent("1パック3日");
});
