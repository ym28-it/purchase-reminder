// Pre-implementation TDD tests for purchase-create rev2 (PURC-TDD-012 to PURC-TDD-014).
// Approved inputs: docs/specs/purchase-create.md (rev2), docs/specs/purchase-create-test-cases.md
// (section 9a, PURC-016-TC1) and docs/specs/purchase-create-tdd-plan.md (第2版の追加).
// Expected results come from the logical test cases only. The HTTP layer is mocked
// (globalThis.fetch), so the real api/hooks/component chain is exercised.
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
	const mock = vi.fn();
	globalThis.fetch = mock;
	return mock;
});

import { queryClient } from "@/api/queryClient";
import { Purchase } from "@/features/Purchase";

type FieldKey = "name" | "category" | "speed" | "stock";
type User = ReturnType<typeof userEvent.setup>;

const label: Record<FieldKey, RegExp> = {
	name: /^名前$/,
	category: /^カテゴリ$/,
	speed: /消費スピード/,
	stock: /現在の在庫/,
};

function jsonResponse(status: number, body: unknown): Response {
	return new Response(JSON.stringify(body), {
		status,
		headers: { "Content-Type": "application/json" },
	});
}

function requestMethod(input: unknown, init?: RequestInit): string {
	if (init?.method) return init.method.toUpperCase();
	if (input && typeof input === "object" && "method" in input) {
		return String((input as Request).method).toUpperCase();
	}
	return "GET";
}

/** GET /purchases returns an empty list; POST /purchases returns `post`. */
function mockApi(post: () => Response) {
	fetchMock.mockImplementation(async (input: unknown, init?: RequestInit) => {
		const method = requestMethod(input, init);
		if (method === "POST") return post();
		return jsonResponse(200, []);
	});
}

function postCalls(): number {
	return fetchMock.mock.calls.filter(
		([input, init]) => requestMethod(input, init) === "POST",
	).length;
}

beforeEach(() => {
	queryClient.clear();
	fetchMock.mockReset();
});

afterEach(() => {
	cleanup();
	queryClient.clear();
	fetchMock.mockReset();
});

function renderPage() {
	render(
		<QueryClientProvider client={queryClient}>
			<Purchase />
		</QueryClientProvider>,
	);
}

async function openDialog(user: User): Promise<HTMLElement> {
	await user.click(await screen.findByRole("button", { name: "追加" }));
	return screen.findByRole("dialog");
}

function field(key: FieldKey): HTMLInputElement {
	return within(screen.getByRole("dialog")).getByLabelText(
		label[key],
	) as HTMLInputElement;
}

function temporary(): HTMLInputElement {
	return within(screen.getByRole("dialog")).getByLabelText(
		/一時的な購入/,
	) as HTMLInputElement;
}

async function setValue(user: User, key: FieldKey, value: string) {
	const input = field(key);
	await user.clear(input);
	await user.click(input);
	await user.paste(value);
}

async function fillValid(user: User) {
	await setValue(user, "name", "牛乳");
	await setValue(user, "category", "食品");
	await setValue(user, "speed", "3");
	await setValue(user, "stock", "4");
	await user.click(temporary());
}

function expectFilledValuesKept() {
	expect(field("name")).toHaveValue("牛乳");
	expect(field("category")).toHaveValue("食品");
	expect(field("speed")).toHaveValue(3);
	expect(field("stock")).toHaveValue(4);
	expect(temporary()).toBeChecked();
}

async function submit(user: User) {
	await user.click(
		within(screen.getByRole("dialog")).getByRole("button", {
			name: "登録する",
		}),
	);
}

/** Text shown in a field's container other than its label (i.e. the field's error). */
function fieldErrorText(key: FieldKey): string {
	const input = field(key);
	const container = input.parentElement;
	if (!container) return "";
	const labelText = Array.from(container.querySelectorAll("label"))
		.map((element) => element.textContent ?? "")
		.join("");
	return (container.textContent ?? "").replace(labelText, "").trim();
}

test("PURC-TDD-012 (PURC-020-TC1; CORE-005): reopening after a failed registration shows no failure and initial values", async () => {
	const user = userEvent.setup();
	mockApi(() => jsonResponse(500, { detail: "Internal Server Error" }));
	renderPage();

	const freshDialog = await openDialog(user);
	const freshText = freshDialog.textContent;
	await fillValid(user);
	await submit(user);
	await waitFor(() => expect(postCalls()).toBe(1));
	// Precondition: a failure is displayed in the registration dialog.
	await waitFor(() =>
		expect(screen.getByRole("dialog").textContent).not.toBe(freshText),
	);

	await user.click(
		within(screen.getByRole("dialog")).getByRole("button", { name: "Close" }),
	);
	await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
	const reopened = await openDialog(user);

	expect(reopened.textContent).toBe(freshText);
	expect(field("name")).toHaveValue("");
	expect(field("category")).toHaveValue("");
	expect(field("speed")).toHaveValue(0);
	expect(field("stock")).toHaveValue(0);
	expect(temporary()).not.toBeChecked();
});

test("PURC-TDD-013 (PURC-021-TC1; CORE-005): an API 422 for name keeps the dialog and inputs and marks the name field", async () => {
	const user = userEvent.setup();
	mockApi(() =>
		jsonResponse(422, {
			detail: [
				{
					loc: ["body", "name"],
					msg: "String should have at most 50 characters",
					type: "string_too_long",
				},
			],
		}),
	);
	renderPage();

	await openDialog(user);
	await fillValid(user);
	expect(fieldErrorText("name")).toBe("");
	await submit(user);
	await waitFor(() => expect(postCalls()).toBe(1));

	await waitFor(() => expect(fieldErrorText("name")).not.toBe(""));
	expect(screen.getByRole("dialog")).toBeInTheDocument();
	expectFilledValuesKept();
	expect(fieldErrorText("category")).toBe("");
	expect(fieldErrorText("speed")).toBe("");
	expect(fieldErrorText("stock")).toBe("");
});

test("PURC-TDD-014 (PURC-016-TC1; CORE-005): a 409 is shown as a duplicate requiring a name/category change regardless of detail wording", async () => {
	const user = userEvent.setup();
	mockApi(() => jsonResponse(409, { detail: "conflict" }));
	renderPage();

	await openDialog(user);
	await fillValid(user);
	await submit(user);
	await waitFor(() => expect(postCalls()).toBe(1));

	const duplicate = /重複|既に/;
	// The innermost element that carries the duplicate wording.
	const message = await waitFor(() => {
		const found = within(screen.getByRole("dialog")).queryAllByText(
			(_content, element) =>
				!!element &&
				duplicate.test(element.textContent ?? "") &&
				!Array.from(element.children).some((child) =>
					duplicate.test(child.textContent ?? ""),
				),
		);
		expect(found.length).toBeGreaterThan(0);
		return found[0];
	});
	expect(message.textContent).toMatch(/名前|カテゴリ/);
});
