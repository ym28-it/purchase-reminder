// Post-implementation component coverage for purchase-edit-fields (PEDT).
// Expected results come from docs/superpowers/specs/2026-11-22-purchase-edit-fields-test-cases.md
// and the plan Review Focus only. The frozen TDD tests live in Purchase.edit.test.tsx.
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

const SURROGATE = "\u{20BB7}"; // one character, two UTF-16 code units
const IDEOGRAPHIC_SPACE = "　";

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
	listed = [milk];
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

async function openEdit(user: User) {
	const item = (await screen.findByText("牛乳")).closest("li") as HTMLElement;
	await user.click(within(item).getByRole("button", { name: "編集" }));
	return screen.findByRole("dialog");
}

async function replace(user: User, input: HTMLElement, value: string) {
	await user.clear(input);
	if (value !== "") await user.type(input, value);
}

const fields = {
	name: /^名前$/,
	category: /^カテゴリ$/,
	unit: /^購入単位/,
	days: /使い切る日数/,
	buffer: /余裕日数/,
	stock: /^在庫/,
} as const;

type FieldKey = keyof typeof fields;

const SAVE = { name: /保存|更新/ };

function errorOf(input: HTMLElement) {
	return (input.parentElement as HTMLElement).querySelector("p");
}

describe("PEDT-007-TC3: labels explain unit, days, buffer days and stock", () => {
	test("the edit dialog labels name what each value means", async () => {
		const user = userEvent.setup();
		renderList();
		const dialog = await openEdit(user);

		const label = (key: FieldKey) =>
			(within(dialog).getByLabelText(fields[key]) as HTMLInputElement)
				.labels?.[0];
		expect(label("days")).toHaveTextContent(/1単位.*使い切る日数.*日/);
		expect(label("buffer")).toHaveTextContent(/余裕日数.*日/);
		expect(label("stock")).toHaveTextContent(/購入単位/);
		expect(label("unit")).toHaveTextContent(/購入単位/);
	});
});

describe("PEDT-008-TC1: the remaining invalid values are not sent and show a field error", () => {
	test.each<[string, FieldKey, string]>([
		["empty name", "name", ""],
		["whitespace-only name", "name", "   "],
		["U+3000-only name", "name", IDEOGRAPHIC_SPACE],
		["51-character surrogate name", "name", SURROGATE.repeat(51)],
		["empty category", "category", ""],
		["whitespace-only category", "category", "   "],
		["31-character surrogate category", "category", SURROGATE.repeat(31)],
		["11-character unit", "unit", "あ".repeat(11)],
		["11-character surrogate unit", "unit", SURROGATE.repeat(11)],
		["negative days", "days", "-1"],
		["negative buffer days", "buffer", "-1"],
		["negative stock", "stock", "-1"],
	])("%s", async (_title, key, value) => {
		const user = userEvent.setup();
		renderList();
		const dialog = await openEdit(user);

		const input = within(dialog).getByLabelText(fields[key]);
		if (value.length > 20) {
			await user.clear(input);
			await user.click(input);
			await user.paste(value); // user.type is too slow for long values
		} else {
			await replace(user, input, value);
		}
		await user.click(within(dialog).getByRole("button", SAVE));

		await waitFor(() => expect(errorOf(input)).not.toBeNull());
		expect(putBodies).toHaveLength(0);
	});
});

describe("PEDT-008-TC2: boundary text lengths count code points", () => {
	test("a 50-character name, 30-character category and 10-character surrogate unit are sent", async () => {
		const user = userEvent.setup();
		renderList();
		const dialog = await openEdit(user);

		for (const [key, value] of [
			["name", SURROGATE.repeat(50)],
			["category", SURROGATE.repeat(30)],
			["unit", SURROGATE.repeat(10)],
		] as const) {
			const input = within(dialog).getByLabelText(fields[key]);
			await user.clear(input);
			await user.click(input);
			await user.paste(value);
		}
		await user.click(within(dialog).getByRole("button", SAVE));

		await waitFor(() => expect(putBodies).toHaveLength(1));
		expect(putBodies[0]).toMatchObject({
			name: SURROGATE.repeat(50),
			category: SURROGATE.repeat(30),
			unit: SURROGATE.repeat(10),
		});
	});
});

describe("PEDT-008-TC3: an input error clears once the value is fixed", () => {
	test("out-of-range days show an error, then a valid value is sent and the error is gone", async () => {
		const user = userEvent.setup();
		renderList();
		const dialog = await openEdit(user);
		const days = within(dialog).getByLabelText(fields.days);

		await replace(user, days, "366");
		await user.click(within(dialog).getByRole("button", SAVE));
		await waitFor(() => expect(errorOf(days)).not.toBeNull());
		expect(putBodies).toHaveLength(0);

		await replace(user, days, "7");
		await user.click(within(dialog).getByRole("button", SAVE));

		await waitFor(() => expect(putBodies).toHaveLength(1));
		expect(putBodies[0]).toMatchObject({ days_per_unit: 7 });
		await waitFor(() => expect(errorOf(days)).toBeNull());
	});
});

describe("PEDT Review Focus 3: an emptied numeric field is an input error, not NaN or 0", () => {
	test.each<[string, FieldKey]>([
		["days", "days"],
		["buffer days", "buffer"],
		["stock", "stock"],
	])("empty %s", async (_title, key) => {
		const user = userEvent.setup();
		renderList();
		const dialog = await openEdit(user);

		const input = within(dialog).getByLabelText(fields[key]);
		await replace(user, input, "");
		await user.click(within(dialog).getByRole("button", SAVE));

		await waitFor(() => expect(errorOf(input)).not.toBeNull());
		expect(putBodies).toHaveLength(0);
	});
});

describe("PEDT Review Focus 1: a stale non-integer saved value", () => {
	test("is shown as saved, blocks sending with an error, and saves once made an integer", async () => {
		listed = [{ ...milk, stock: 1.5 }];
		const user = userEvent.setup();
		renderList();
		const dialog = await openEdit(user);
		const stock = within(dialog).getByLabelText(fields.stock);
		expect(stock).toHaveValue(1.5);

		await user.click(within(dialog).getByRole("button", SAVE));
		await waitFor(() => expect(errorOf(stock)).not.toBeNull());
		expect(putBodies).toHaveLength(0);

		await replace(user, stock, "2");
		await user.click(within(dialog).getByRole("button", SAVE));

		await waitFor(() => expect(putBodies).toHaveLength(1));
		expect(putBodies[0]).toMatchObject({ stock: 2 });
	});
});

describe("PEDT-007-TC4 / PEDT-001: the temporary flag is edited and sent", () => {
	test("unchecking the temporary checkbox sends is_temporary=false with the other saved values", async () => {
		const user = userEvent.setup();
		renderList();
		const dialog = await openEdit(user);

		await user.click(within(dialog).getByLabelText(/一時的な購入/));
		await user.click(within(dialog).getByRole("button", SAVE));

		await waitFor(() => expect(putBodies).toHaveLength(1));
		expect(putBodies[0]).toEqual({
			name: "牛乳",
			category: "食品",
			unit: "パック",
			days_per_unit: 3,
			buffer_days: 2,
			stock: 2,
			is_temporary: false,
		});
	});
});
