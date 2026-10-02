// Post-implementation coverage for purchase-create rev2 failure paths
// (docs/specs/purchase-create.md rev2 §6/§7, PURC-015〜018, PURC-020, PURC-021).
// Expected results come from the approved spec and logical test cases only; the
// frozen rev2 TDD scenarios (CreatePurchaseDialog.rev2.test.tsx) are not repeated.
// Only `fetch` is replaced, so the real API client, hooks, dialog and list run.
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

type FieldKey = "name" | "category" | "speed" | "stock";
type User = ReturnType<typeof userEvent.setup>;
type Respond = () => Promise<Response>;

const label: Record<FieldKey, RegExp> = {
	name: /^名前$/,
	category: /^カテゴリ$/,
	speed: /消費スピード/,
	stock: /現在の在庫/,
};
const FIELD_KEYS: FieldKey[] = ["name", "category", "speed", "stock"];
const DUPLICATE = /既に存在|重複/;
const SECRET = "Traceback secret-internal-table arn:aws ConditionalCheckFailed";
const LEAKS = [
	"Traceback",
	"secret-internal-table",
	"arn:aws",
	"ConditionalCheckFailed",
	"Internal Server Error",
	"Failed to fetch",
	"TypeError",
	"json_invalid",
	"extra_forbidden",
	"user_id",
	"<html",
];

let postHandlers: Respond[];

function json(status: number, body: unknown): Promise<Response> {
	return Promise.resolve(
		new Response(JSON.stringify(body), {
			status,
			headers: { "Content-Type": "application/json" },
		}),
	);
}

function text(
	status: number,
	body: string,
	type = "text/plain",
): Promise<Response> {
	return Promise.resolve(
		new Response(body, { status, headers: { "Content-Type": type } }),
	);
}

function unprocessable(...locs: unknown[][]): Respond {
	return () =>
		json(422, {
			detail: locs.map((loc) => ({ loc, msg: "invalid", type: "value_error" })),
		});
}

beforeEach(() => {
	postHandlers = [];
	fetchMock.mockImplementation(async (request: Request) => {
		const url = new URL(request.url);
		if (url.pathname !== "/purchases") throw new Error(`unexpected ${url}`);
		if (request.method === "GET") return json(200, []);
		if (request.method === "POST") {
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

function renderList() {
	render(
		<QueryClientProvider client={queryClient}>
			<Purchase />
		</QueryClientProvider>,
	);
}

function postCount(): number {
	return fetchMock.mock.calls.filter(([request]) => request.method === "POST")
		.length;
}

async function openDialog(user: User): Promise<HTMLElement> {
	await user.click(await screen.findByRole("button", { name: "追加" }));
	return screen.findByRole("dialog");
}

function dialog(): HTMLElement {
	return screen.getByRole("dialog");
}

function field(key: FieldKey): HTMLInputElement {
	return within(dialog()).getByLabelText(label[key]) as HTMLInputElement;
}

function temporary(): HTMLInputElement {
	return within(dialog()).getByLabelText(/一時的な購入/) as HTMLInputElement;
}

async function fillValid(user: User) {
	await user.type(field("name"), "牛乳");
	await user.type(field("category"), "食品");
	await user.clear(field("speed"));
	await user.type(field("speed"), "3");
	await user.clear(field("stock"));
	await user.type(field("stock"), "4");
	await user.click(temporary());
}

function expectFilledValuesKept() {
	expect(field("name")).toHaveValue("牛乳");
	expect(field("category")).toHaveValue("食品");
	expect(field("speed")).toHaveValue(3);
	expect(field("stock")).toHaveValue(4);
	expect(temporary()).toBeChecked();
}

function expectInitialValues() {
	expect(field("name")).toHaveValue("");
	expect(field("category")).toHaveValue("");
	expect(field("speed")).toHaveValue(0);
	expect(field("stock")).toHaveValue(0);
	expect(temporary()).not.toBeChecked();
}

function submitButton(): HTMLElement {
	return within(dialog()).getByRole("button", { name: /登録/ });
}

/** Text in a field's container other than its label (the field's error). */
function fieldErrorText(key: FieldKey): string {
	const container = field(key).parentElement;
	if (!container) return "";
	const labelText = Array.from(container.querySelectorAll("label"))
		.map((element) => element.textContent ?? "")
		.join("");
	return (container.textContent ?? "").replace(labelText, "").trim();
}

/**
 * Text right after the temporary-purchase checkbox's label (where an error for that
 * input appears), unless that element is another control or the footer.
 */
function textAfterTemporary(): string {
	const checkboxLabel = temporary().closest("label");
	const next = checkboxLabel?.nextElementSibling;
	if (!next || next.querySelector("button, input")) return "";
	return (next.textContent ?? "").trim();
}

/** Text a failure added to the dialog: `before` minus the common prefix and suffix. */
function addedText(before: string): string {
	const after = dialog().textContent ?? "";
	let start = 0;
	while (
		start < before.length &&
		start < after.length &&
		before[start] === after[start]
	)
		start++;
	let end = 0;
	while (
		end < before.length - start &&
		end < after.length - start &&
		before[before.length - 1 - end] === after[after.length - 1 - end]
	)
		end++;
	return after.slice(start, after.length - end).trim();
}

/**
 * A network failure first (the reference common failure of PURC-017-TC1), then a
 * manual retry answered by `respond`. Returns the pre-submit dialog text and the
 * common failure text.
 */
async function failCommonlyThenRetry(
	user: User,
	respond: Respond,
): Promise<{ before: string; common: string }> {
	postHandlers = [
		() => Promise.reject(new TypeError("Failed to fetch")),
		respond,
	];
	renderList();
	await openDialog(user);
	await fillValid(user);
	const before = dialog().textContent ?? "";
	await user.click(submitButton());
	await waitFor(() => expect(addedText(before)).not.toBe(""));
	await waitFor(() => expect(submitButton()).toBeEnabled());
	const common = addedText(before);

	await user.click(submitButton());
	await waitFor(() => expect(postCount()).toBe(2));
	await waitFor(() => expect(submitButton()).toHaveTextContent("登録する"));
	await waitFor(() => expect(submitButton()).toBeEnabled());
	return { before, common };
}

function expectNoLeak() {
	for (const leaked of LEAKS) expect(dialog()).not.toHaveTextContent(leaked);
}

async function expectNoAutomaticResend(sent = 1) {
	await new Promise((resolve) => setTimeout(resolve, 500));
	expect(postCount()).toBe(sent);
}

/** Opens the dialog, fills valid input, submits once and returns the pre-submit text. */
async function submitFailing(user: User, respond: Respond): Promise<string> {
	postHandlers = [respond];
	renderList();
	await openDialog(user);
	await fillValid(user);
	const before = dialog().textContent ?? "";
	await user.click(submitButton());
	await waitFor(() => expect(postCount()).toBe(1));
	return before;
}

describe("PURC-016-TC1: 409 is a duplicate by status, whatever the body says", () => {
	test.each<[string, Respond]>([
		["English detail", () => json(409, { detail: "Conflict" })],
		["no detail", () => json(409, {})],
		["detail with internal details", () => json(409, { detail: SECRET })],
		["plain-text body", () => text(409, "Conflict")],
		["empty body", () => Promise.resolve(new Response(null, { status: 409 }))],
	])("%s", async (_name, respond) => {
		const user = userEvent.setup();
		await submitFailing(user, respond);

		const message = await within(dialog()).findByText(DUPLICATE);
		expect(message.textContent).toMatch(/名前|カテゴリ/);
		expectFilledValuesKept();
		expectNoLeak();
		expect(submitButton()).toBeEnabled();
		await expectNoAutomaticResend();
	});
});

describe("PURC-017: other failures are generic even if the body looks like a known cause", () => {
	test.each<[string, Respond]>([
		[
			"500 whose detail has the duplicate wording",
			() => json(500, { detail: "同じ名前とカテゴリの購入物は既に存在します" }),
		],
		[
			"500 whose body looks like a 422",
			() =>
				json(500, {
					detail: [
						{ loc: ["body", "name"], msg: "invalid", type: "value_error" },
					],
				}),
		],
		[
			"503 HTML body",
			() => text(503, "<html>Service Unavailable</html>", "text/html"),
		],
		["404 with internal details", () => json(404, { detail: SECRET })],
	])("%s", async (_name, respond) => {
		const user = userEvent.setup();
		const { before, common } = await failCommonlyThenRetry(user, respond);

		expect(addedText(before)).toBe(common);
		expect(within(dialog()).queryByText(DUPLICATE)).toBeNull();
		for (const key of FIELD_KEYS) expect(fieldErrorText(key)).toBe("");
		expectFilledValuesKept();
		expectNoLeak();
		await expectNoAutomaticResend(2);
	});
});

describe("PURC-021-TC1: an API 422 is shown on the offending fields", () => {
	test.each<[string, FieldKey[], Respond]>([
		["category", ["category"], unprocessable(["body", "category"])],
		["speed", ["speed"], unprocessable(["body", "speed"])],
		["stock", ["stock"], unprocessable(["body", "stock"])],
		[
			"speed and stock together",
			["speed", "stock"],
			unprocessable(["body", "speed"], ["body", "stock"]),
		],
		[
			"a known field next to an unknown one",
			["name"],
			unprocessable(["body", "user_id"], ["body", "name"]),
		],
	])("%s", async (_name, marked, respond) => {
		const user = userEvent.setup();
		await submitFailing(user, respond);

		await waitFor(() => {
			for (const key of marked) expect(fieldErrorText(key)).not.toBe("");
		});
		for (const key of FIELD_KEYS.filter((key) => !marked.includes(key))) {
			expect(fieldErrorText(key)).toBe("");
		}
		expect(within(dialog()).queryByText(DUPLICATE)).toBeNull();
		expectFilledValuesKept();
		expectNoLeak();
		await expectNoAutomaticResend();
	});

	test("is_temporary: shown at the checkbox and distinct from the common failure", async () => {
		const user = userEvent.setup();
		const { before, common } = await failCommonlyThenRetry(
			user,
			unprocessable(["body", "is_temporary"]),
		);

		const atCheckbox = textAfterTemporary();
		expect(atCheckbox).not.toBe("");
		expect(atCheckbox).not.toBe(common);
		expect(addedText(before)).not.toBe(common);
		for (const key of FIELD_KEYS) expect(fieldErrorText(key)).toBe("");
		expect(within(dialog()).queryByText(DUPLICATE)).toBeNull();
		expectFilledValuesKept();
		expectNoLeak();
		await expectNoAutomaticResend(2);
	});
});

describe("PURC-015 / PURC-017: a 422 that names no input field is a generic failure", () => {
	test.each<[string, Respond]>([
		["unknown body field", unprocessable(["body", "user_id"])],
		["whole body", unprocessable(["body"])],
		["malformed JSON position", unprocessable(["body", 12])],
		["detail is a string", () => json(422, { detail: "Unprocessable" })],
		["detail entries are null", () => json(422, { detail: [null] })],
		["no detail", () => json(422, {})],
		["plain-text body", () => text(422, "Unprocessable Entity")],
	])("%s", async (_name, respond) => {
		const user = userEvent.setup();
		const { before, common } = await failCommonlyThenRetry(user, respond);

		expect(addedText(before)).toBe(common);
		for (const key of FIELD_KEYS) expect(fieldErrorText(key)).toBe("");
		expect(within(dialog()).queryByText(DUPLICATE)).toBeNull();
		expectFilledValuesKept();
		expectNoLeak();
		await expectNoAutomaticResend(2);
	});
});

describe("PURC-020-TC1: reopening clears every kind of failure display", () => {
	test.each<[string, Respond]>([
		["409", () => json(409, { detail: "conflict" })],
		["422 on name", unprocessable(["body", "name"])],
		["422 on is_temporary", unprocessable(["body", "is_temporary"])],
		["422 on an unknown field", unprocessable(["body", "user_id"])],
		["network failure", () => Promise.reject(new TypeError("Failed to fetch"))],
	])("%s", async (_name, respond) => {
		const user = userEvent.setup();
		postHandlers = [respond];
		renderList();
		const fresh = (await openDialog(user)).textContent;
		await fillValid(user);
		const before = dialog().textContent;
		await user.click(submitButton());
		await waitFor(() => expect(dialog().textContent).not.toBe(before));

		await user.click(within(dialog()).getByRole("button", { name: "Close" }));
		await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
		const reopened = await openDialog(user);

		expect(reopened.textContent).toBe(fresh);
		expectInitialValues();
		expect(postCount()).toBe(1);
	});
});

describe("spec §7-6: a manual retry after an API 422 sends one new request", () => {
	test("422 on name, then a manual retry with the same input", async () => {
		const user = userEvent.setup();
		await submitFailing(user, unprocessable(["body", "name"]));
		await waitFor(() => expect(fieldErrorText("name")).not.toBe(""));
		postHandlers = [() => json(409, { detail: "conflict" })];

		await user.click(submitButton());

		await waitFor(() => expect(postCount()).toBe(2));
		await within(dialog()).findByText(DUPLICATE);
		expectFilledValuesKept();
	});
});
