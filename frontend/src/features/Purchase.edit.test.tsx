// TDD tests for purchase-edit-fields (PEDT-CORE-007, PEDT-CORE-008).
// Expected results come from docs/superpowers/specs/2026-11-22-purchase-edit-fields-test-cases.md
// only. The HTTP layer is mocked (globalThis.fetch).
import { QueryClientProvider } from "@tanstack/react-query";
import {
	cleanup,
	render,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

// openapi-fetch captures globalThis.fetch when src/api/client.ts is imported,
// so the mock must be installed before any app module is loaded.
const fetchMock = vi.hoisted(() => {
	const mock = vi.fn<(request: Request) => Promise<Response>>();
	globalThis.fetch = mock as unknown as typeof fetch;
	return mock;
});

import { queryClient } from "@/api/queryClient";
import { Purchase } from "@/features/Purchase";

const milk = {
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

const soyMilk = {
	id: "0b6f0d0e-5c3a-4a39-9a55-3f0f3f1d7a11",
	name: "豆乳",
	category: "飲料",
	unit: "本",
	days_per_unit: 5,
	buffer_days: 0,
	stock: 7,
	is_temporary: false,
	stock_counted_at: "2026-11-21T08:09:10Z",
	created_at: "2026-11-22T00:00:00Z",
	updated_at: "2026-11-22T00:00:00Z",
};

let listed: unknown[];
let putBodies: unknown[];

function json(body: unknown) {
	return new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});
}

beforeEach(() => {
	queryClient.clear();
	listed = [milk, soyMilk];
	putBodies = [];
	fetchMock.mockImplementation(async (request: Request) => {
		if (request.method === "PUT") {
			const body = JSON.parse(await request.clone().text());
			putBodies.push(body);
			return json({ ...milk, ...body });
		}
		return json(listed);
	});
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

type User = ReturnType<typeof userEvent.setup>;

async function openEdit(user: User, name: string) {
	const item = (await screen.findByText(name)).closest("li") as HTMLElement;
	await user.click(within(item).getByRole("button", { name: "編集" }));
	return screen.findByRole("dialog");
}

async function replace(user: User, input: HTMLElement, value: string) {
	await user.clear(input);
	if (value !== "") await user.type(input, value);
}

const fields = {
	unit: /^購入単位/,
	days: /使い切る日数/,
	buffer: /余裕日数/,
	stock: /在庫/,
} as const;

function expectSavedValues(dialog: HTMLElement, p: typeof milk) {
	expect(within(dialog).getByLabelText(/名前/)).toHaveValue(p.name);
	expect(within(dialog).getByLabelText(/カテゴリ/)).toHaveValue(p.category);
	expect(within(dialog).getByLabelText(fields.unit)).toHaveValue(p.unit);
	expect(within(dialog).getByLabelText(fields.days)).toHaveValue(
		p.days_per_unit,
	);
	expect(within(dialog).getByLabelText(fields.buffer)).toHaveValue(
		p.buffer_days,
	);
	expect(within(dialog).getByLabelText(fields.stock)).toHaveValue(p.stock);
	const temporary = within(dialog).getByLabelText(/一時的な購入/);
	if (p.is_temporary) expect(temporary).toBeChecked();
	else expect(temporary).not.toBeChecked();
}

test("PEDT-007-TC1/TC2 (PEDT-CORE-007): the edit dialog shows all seven fields with the saved values and re-initialises per purchase", async () => {
	const user = userEvent.setup();
	renderList();

	const first = await openEdit(user, "牛乳");
	expectSavedValues(first, milk);

	await user.keyboard("{Escape}");
	await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());

	const second = await openEdit(user, "豆乳");
	expectSavedValues(second, soyMilk);
});

test("PEDT-007-TC4 (PEDT-CORE-007): saving sends all seven fields and the list reflects the change", async () => {
	const user = userEvent.setup();
	renderList();
	const dialog = await openEdit(user, "牛乳");

	await replace(user, within(dialog).getByLabelText(fields.unit), "本");
	await replace(user, within(dialog).getByLabelText(fields.buffer), "4");
	listed = [{ ...milk, unit: "本", buffer_days: 4 }, soyMilk];
	await user.click(within(dialog).getByRole("button", { name: /保存|更新/ }));

	await waitFor(() => expect(putBodies).toHaveLength(1));
	expect(putBodies[0]).toEqual({
		name: "牛乳",
		category: "食品",
		unit: "本",
		days_per_unit: 3,
		buffer_days: 4,
		stock: 2,
		is_temporary: true,
	});
	await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
	const item = (await screen.findByText("牛乳")).closest("li") as HTMLElement;
	await waitFor(() => expect(item).toHaveTextContent(/余裕\s*4日/));
	expect(item).toHaveTextContent("本");
});

describe("PEDT-008-TC1 (PEDT-CORE-008): invalid values are not sent and show a field error", () => {
	test.each([
		["unit", ""],
		["unit", "   "],
		["days", "1.5"],
		["days", "366"],
		["buffer", "1.5"],
		["buffer", "31"],
		["stock", "1.5"],
		["stock", "100001"],
	] as const)("%s = %j", async (name, value) => {
		const label = fields[name];
		const user = userEvent.setup();
		renderList();
		const dialog = await openEdit(user, "牛乳");

		const input = within(dialog).getByLabelText(label);
		await replace(user, input, value);
		await user.click(within(dialog).getByRole("button", { name: /保存|更新/ }));

		const group = input.parentElement as HTMLElement;
		await waitFor(() => expect(group.querySelector("p")).not.toBeNull());
		expect(putBodies).toHaveLength(0);
	});
});

test("PEDT-008-TC2 (PEDT-CORE-008): boundary values are sent", async () => {
	const user = userEvent.setup();
	renderList();
	const dialog = await openEdit(user, "牛乳");

	await replace(user, within(dialog).getByLabelText(fields.days), "0");
	await replace(user, within(dialog).getByLabelText(fields.buffer), "30");
	await replace(user, within(dialog).getByLabelText(fields.stock), "100000");
	await replace(user, within(dialog).getByLabelText(fields.unit), "1234567890");
	await user.click(within(dialog).getByRole("button", { name: /保存|更新/ }));

	await waitFor(() => expect(putBodies).toHaveLength(1));
	expect(putBodies[0]).toEqual({
		name: "牛乳",
		category: "食品",
		unit: "1234567890",
		days_per_unit: 0,
		buffer_days: 30,
		stock: 100000,
		is_temporary: true,
	});
});
