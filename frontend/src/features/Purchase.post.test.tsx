// Post-implementation coverage for the purchase-create flow on the list screen.
// The HTTP layer is replaced at `fetch`, so the real API client, React Query
// hooks, dialog, and list are exercised together. Expected results come from
// docs/specs/purchase-create-test-cases.md only.
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

const fetchMock = vi.hoisted(() => {
	const mock = vi.fn<(request: Request) => Promise<Response>>();
	globalThis.fetch = mock as unknown as typeof fetch;
	return mock;
});

import { queryClient } from "@/api/queryClient";
import { Purchase } from "@/features/Purchase";

type Item = {
	id: string;
	name: string;
	category: string;
	speed: number;
	stock: number;
	is_temporary: boolean;
	created_at: string;
	updated_at: string;
};

const created: Item = {
	id: "aef5de6b-046d-48d2-a84b-df6c989643d0",
	name: "牛乳",
	category: "食品",
	speed: 3,
	stock: 4,
	is_temporary: true,
	created_at: "2026-09-27T00:00:00Z",
	updated_at: "2026-09-27T00:00:00Z",
};

const SECRET =
	"Traceback (most recent call last): secret-internal-table arn:aws";

let listResponses: Item[][];
let postHandlers: Array<() => Promise<Response>>;
let postBodies: unknown[];

function json(status: number, body: unknown): Promise<Response> {
	return Promise.resolve(
		new Response(JSON.stringify(body), {
			status,
			headers: { "Content-Type": "application/json" },
		}),
	);
}

beforeEach(() => {
	listResponses = [[]];
	postHandlers = [];
	postBodies = [];
	fetchMock.mockImplementation(async (request: Request) => {
		const url = new URL(request.url);
		if (url.pathname !== "/purchases") throw new Error(`unexpected ${url}`);
		if (request.method === "GET") {
			const next =
				listResponses.length > 1 ? listResponses.shift() : listResponses[0];
			return json(200, next);
		}
		if (request.method === "POST") {
			postBodies.push(JSON.parse(await request.clone().text()));
			const handler = postHandlers.shift();
			if (!handler) throw new Error("unexpected POST");
			return handler();
		}
		throw new Error(`unexpected ${request.method}`);
	});
});

afterEach(() => {
	cleanup();
	queryClient.clear();
	fetchMock.mockReset();
});

type User = ReturnType<typeof userEvent.setup>;

function renderList() {
	render(
		<QueryClientProvider client={queryClient}>
			<Purchase />
		</QueryClientProvider>,
	);
}

function postCount() {
	return fetchMock.mock.calls.filter(([request]) => request.method === "POST")
		.length;
}

function getCount() {
	return fetchMock.mock.calls.filter(([request]) => request.method === "GET")
		.length;
}

async function openDialog(user: User) {
	await user.click(await screen.findByRole("button", { name: "追加" }));
	return screen.findByRole("dialog");
}

function inputs(dialog: HTMLElement) {
	return {
		name: within(dialog).getByLabelText(/^名前$/),
		category: within(dialog).getByLabelText(/^カテゴリ$/),
		speed: within(dialog).getByLabelText(/消費スピード/),
		stock: within(dialog).getByLabelText(/現在の在庫/),
		isTemporary: within(dialog).getByLabelText(/一時的な購入/),
	};
}

async function fillAllFive(user: User, dialog: HTMLElement) {
	const field = inputs(dialog);
	await user.type(field.name, created.name);
	await user.type(field.category, created.category);
	await user.clear(field.speed);
	await user.type(field.speed, String(created.speed));
	await user.clear(field.stock);
	await user.type(field.stock, String(created.stock));
	await user.click(field.isTemporary);
}

function expectAllFiveRetained(dialog: HTMLElement) {
	const field = inputs(dialog);
	expect(field.name).toHaveValue(created.name);
	expect(field.category).toHaveValue(created.category);
	expect(field.speed).toHaveValue(created.speed);
	expect(field.stock).toHaveValue(created.stock);
	expect(field.isTemporary).toBeChecked();
}

function expectInitialValues(dialog: HTMLElement) {
	const field = inputs(dialog);
	expect(field.name).toHaveValue("");
	expect(field.category).toHaveValue("");
	expect(field.speed).toHaveValue(0);
	expect(field.stock).toHaveValue(0);
	expect(field.isTemporary).not.toBeChecked();
}

function submitButton(dialog: HTMLElement) {
	return within(dialog).getByRole("button", { name: /登録/ });
}

const sentBody = {
	name: created.name,
	category: created.category,
	speed: created.speed,
	stock: created.stock,
	is_temporary: true,
};

describe("PURC-001 / PURC-012: list screen", () => {
	test("PURC-001-TC1: the add action on the list opens the registration screen", async () => {
		const user = userEvent.setup();
		renderList();
		const dialog = await openDialog(user);
		expect(
			within(dialog).getByRole("heading", { name: "購入物を追加" }),
		).toBeInTheDocument();
		expectInitialValues(dialog);
	});

	test("PURC-012-TC2/TC3: only the temporary purchase is marked temporary", async () => {
		listResponses = [
			[
				{ ...created, name: "旅行用シャンプー", category: "日用品" },
				{
					...created,
					id: "b1fd5e6b-046d-48d2-a84b-df6c989643d0",
					is_temporary: false,
				},
			],
		];
		renderList();
		const temporaryItem = (await screen.findByText("旅行用シャンプー")).closest(
			"li",
		);
		const regularItem = screen.getByText("牛乳").closest("li");
		expect(temporaryItem).toHaveTextContent("一時的");
		expect(regularItem).not.toBeNull();
		expect(regularItem).not.toHaveTextContent("一時的");
	});
});

describe("PURC-010 / PURC-011 / PURC-012-TC4: successful registration", () => {
	test("closes, refetches, shows no extra success message, and reopens with initial values", async () => {
		const user = userEvent.setup();
		listResponses = [[], [created]];
		postHandlers = [() => json(201, created)];
		renderList();
		await screen.findByText("まだ登録されていません");

		const dialog = await openDialog(user);
		await fillAllFive(user, dialog);
		await user.click(submitButton(dialog));

		await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
		const item = (await screen.findByText("牛乳")).closest("li");
		expect(item).toHaveTextContent("一時的");
		expect(postBodies).toEqual([sentBody]);
		expect(getCount()).toBe(2);
		// PURC-012-TC4: no toast / success message beyond the list update.
		expect(screen.queryByRole("status")).toBeNull();
		expect(screen.queryByRole("alert")).toBeNull();
		expect(
			screen.queryByText(/成功|完了|登録しました|追加しました/),
		).toBeNull();

		// PURC-010-TC2
		const reopened = await openDialog(user);
		expectInitialValues(reopened);
	});
});

describe("PURC-013: duplicate submission from the same screen operation", () => {
	test("PURC-013-TC1: the submit action is disabled while the request is pending", async () => {
		const user = userEvent.setup();
		postHandlers = [() => new Promise<Response>(() => undefined)];
		renderList();
		const dialog = await openDialog(user);
		await fillAllFive(user, dialog);
		await user.click(submitButton(dialog));

		await waitFor(() => expect(submitButton(dialog)).toBeDisabled());
		await user.click(submitButton(dialog));
		await new Promise((resolve) => setTimeout(resolve, 50));
		expect(postCount()).toBe(1);
	});

	test("PURC-013-TC1/TC2: a rapid double click sends exactly one request", async () => {
		const user = userEvent.setup();
		listResponses = [[], [created]];
		postHandlers = [() => json(201, created)];
		renderList();
		const dialog = await openDialog(user);
		await fillAllFive(user, dialog);
		await user.dblClick(submitButton(dialog));

		await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
		expect(postCount()).toBe(1);
	});
});

type Failure = {
	name: string;
	respond: () => Promise<Response>;
	message: RegExp;
};

const failures: Failure[] = [
	{
		name: "PURC-016-TC1 409 duplicate shows the duplicate cause",
		respond: () =>
			json(409, { detail: "同じ名前とカテゴリの購入物は既に存在します" }),
		message: /名前.*カテゴリ.*(既に存在|重複)/,
	},
	{
		name: "PURC-017-TC1/TC2 500 with internal details shows a generic error",
		respond: () => json(500, { detail: SECRET }),
		message: /失敗/,
	},
	{
		name: "PURC-017-TC1/TC2 500 plain text shows a generic error",
		respond: () =>
			Promise.resolve(new Response("Internal Server Error", { status: 500 })),
		message: /失敗/,
	},
	{
		name: "PURC-017-TC1 / PURC-018-TC1 network failure shows a generic error",
		respond: () => Promise.reject(new TypeError("Failed to fetch")),
		message: /失敗/,
	},
	{
		name: "PURC-015-TC1 422 from the API keeps the dialog and input",
		respond: () =>
			json(422, {
				detail: [
					{
						loc: ["body", "name"],
						msg: "Value error, 空白だけの入力はできません",
						type: "value_error",
					},
				],
			}),
		message: /失敗|修正|エラー|できません/,
	},
];

describe("PURC-015 / PURC-016 / PURC-017 / PURC-018: failed registration", () => {
	test.each(failures)(
		"$name; keeps all five inputs and does not auto-retry",
		async ({ respond, message }) => {
			const user = userEvent.setup();
			postHandlers = [respond];
			renderList();
			const dialog = await openDialog(user);
			await fillAllFive(user, dialog);
			await user.click(submitButton(dialog));

			expect(await within(dialog).findByText(message)).toBeInTheDocument();
			expect(screen.getByRole("dialog")).toBe(dialog);
			expectAllFiveRetained(dialog);
			for (const leaked of [
				"Traceback",
				"secret-internal-table",
				"arn:aws",
				"Internal Server Error",
				"Failed to fetch",
				"TypeError",
				"value_error",
			]) {
				expect(dialog).not.toHaveTextContent(leaked);
			}
			expect(submitButton(dialog)).toBeEnabled();

			// PURC-018-TC1: no automatic resend while the user does nothing.
			await new Promise((resolve) => setTimeout(resolve, 1500));
			expect(postCount()).toBe(1);
			expect(screen.getByRole("dialog")).toBe(dialog);
		},
	);

	test("PURC-016-TC1: duplicate and generic failures are distinguishable", async () => {
		const user = userEvent.setup();
		postHandlers = [
			() => json(409, { detail: "同じ名前とカテゴリの購入物は既に存在します" }),
			() => json(500, { detail: SECRET }),
		];
		renderList();
		const dialog = await openDialog(user);
		await fillAllFive(user, dialog);
		await user.click(submitButton(dialog));
		const duplicate = (await within(dialog).findByText(/既に存在|重複/))
			.textContent;
		await user.click(submitButton(dialog));
		await waitFor(() => expect(postCount()).toBe(2));
		await waitFor(() =>
			expect(within(dialog).queryByText(/既に存在|重複/)).toBeNull(),
		);
		const generic = within(dialog).getByText(/失敗/).textContent;
		expect(generic).not.toBe(duplicate);
	});

	test("PURC-018-TC2: after a network failure a manual retry sends exactly one new request", async () => {
		const user = userEvent.setup();
		listResponses = [[], [created]];
		postHandlers = [
			() => Promise.reject(new TypeError("Failed to fetch")),
			() => json(201, created),
		];
		renderList();
		const dialog = await openDialog(user);
		await fillAllFive(user, dialog);
		await user.click(submitButton(dialog));
		await within(dialog).findByText(/失敗/);
		expect(postCount()).toBe(1);

		await user.click(submitButton(dialog));

		await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
		expect(postCount()).toBe(2);
		expect(postBodies).toEqual([sentBody, sentBody]);
		expect(await screen.findByText("牛乳")).toBeInTheDocument();
	});
});
