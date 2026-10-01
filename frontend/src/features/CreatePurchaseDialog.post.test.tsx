// Post-implementation component coverage for purchase-create input validation.
// Expected results come from docs/specs/purchase-create-test-cases.md only.
import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { createPurchase } from "@/api/purchases";
import { queryClient } from "@/api/queryClient";
import { CreatePurchaseDialog } from "@/features/CreatePurchaseDialog";

vi.mock("@/api/purchases", () => ({ createPurchase: vi.fn() }));

const SURROGATE = "\u{20BB7}"; // 𠮷: one character, two UTF-16 code units
const IDEOGRAPHIC_SPACE = "　";

type FieldKey = "name" | "category" | "speed" | "stock";

const label: Record<FieldKey, RegExp> = {
	name: /^名前$/,
	category: /^カテゴリ$/,
	speed: /消費スピード/,
	stock: /現在の在庫/,
};

const validInput: Record<FieldKey, string> = {
	name: "牛乳",
	category: "食品",
	speed: "1",
	stock: "2",
};

type User = ReturnType<typeof userEvent.setup>;

beforeEach(() => {
	vi.mocked(createPurchase).mockImplementation(async (input) => ({
		...input,
		is_temporary: input.is_temporary ?? false,
		id: "aef5de6b-046d-48d2-a84b-df6c989643d0",
		created_at: "2026-09-27T00:00:00Z",
		updated_at: "2026-09-27T00:00:00Z",
	}));
});

afterEach(() => {
	cleanup();
	queryClient.clear();
	vi.clearAllMocks();
});

function renderDialog() {
	render(
		<QueryClientProvider client={queryClient}>
			<CreatePurchaseDialog open onOpenChange={vi.fn()} />
		</QueryClientProvider>,
	);
}

function field(key: FieldKey): HTMLInputElement {
	return screen.getByLabelText(label[key]) as HTMLInputElement;
}

async function setValue(user: User, key: FieldKey, value: string) {
	const input = field(key);
	await user.clear(input);
	if (value !== "") {
		await user.click(input);
		await user.paste(value);
	}
}

async function fill(
	user: User,
	overrides: Partial<Record<FieldKey, string>> = {},
	isTemporary = false,
) {
	const values = { ...validInput, ...overrides };
	for (const key of Object.keys(values) as FieldKey[]) {
		await setValue(user, key, values[key]);
	}
	if (isTemporary) await user.click(screen.getByLabelText(/一時的な購入/));
}

async function submit(user: User) {
	await user.click(screen.getByRole("button", { name: "登録する" }));
}

function fieldError(key: FieldKey): HTMLElement | null {
	return field(key).parentElement?.querySelector("p") ?? null;
}

async function expectRejected(key: FieldKey) {
	await waitFor(() => expect(fieldError(key)).not.toBeNull());
	for (const other of Object.keys(label) as FieldKey[]) {
		if (other !== key) expect(fieldError(other)).toBeNull();
	}
	// Give a would-be submission time to happen before asserting it did not.
	await new Promise((resolve) => setTimeout(resolve, 50));
	expect(createPurchase).not.toHaveBeenCalled();
}

describe("PURC-002: registration form", () => {
	test("PURC-002-TC1/TC2: five inputs exist with the approved initial values", () => {
		renderDialog();
		expect(field("name")).toHaveValue("");
		expect(field("category")).toHaveValue("");
		expect(field("speed")).toHaveValue(0);
		expect(field("stock")).toHaveValue(0);
		expect(screen.getByLabelText(/一時的な購入/)).not.toBeChecked();
	});
});

describe("PURC-003-TC1 / PURC-004 / PURC-016-TC2: invalid input is not sent", () => {
	test.each<[string, FieldKey, string]>([
		["PURC-004-TC1 empty name", "name", ""],
		["PURC-004-TC1 ASCII spaces name", "name", "   "],
		["PURC-004-TC1 U+3000 name", "name", IDEOGRAPHIC_SPACE],
		["PURC-004-TC1 mixed whitespace name", "name", ` ${IDEOGRAPHIC_SPACE}\t`],
		["PURC-004-TC2 empty category", "category", ""],
		["PURC-004-TC2 ASCII spaces category", "category", "   "],
		["PURC-004-TC2 U+3000 category", "category", IDEOGRAPHIC_SPACE.repeat(2)],
		["PURC-004-TC4 51 ASCII name", "name", "x".repeat(51)],
		["PURC-004-TC4 51 surrogate name", "name", SURROGATE.repeat(51)],
		["PURC-004-TC6 31 ASCII category", "category", "x".repeat(31)],
		["PURC-004-TC6 31 surrogate category", "category", SURROGATE.repeat(31)],
		["PURC-004-TC8 negative speed", "speed", "-1"],
		["PURC-004-TC8 decimal speed", "speed", "1.5"],
		["PURC-004-TC8 over-limit speed", "speed", "100001"],
		["PURC-004-TC10 negative stock", "stock", "-1"],
		["PURC-004-TC10 decimal stock", "stock", "1.5"],
		["PURC-004-TC10 over-limit stock", "stock", "100001"],
	])("%s is rejected at the field and not sent", async (_name, key, value) => {
		const user = userEvent.setup();
		renderDialog();
		await fill(user, { [key]: value });
		await submit(user);
		await expectRejected(key);
	});

	// DEFECT-002: an emptied required numeric input is coerced to 0 and sent.
	test.fails.each<[string, FieldKey]>([
		["PURC-003-TC1 emptied speed", "speed"],
		["PURC-003-TC1 emptied stock", "stock"],
	])("%s is rejected at the field and not sent", async (_name, key) => {
		const user = userEvent.setup();
		renderDialog();
		await fill(user, { [key]: "" });
		await submit(user);
		await expectRejected(key);
	});
});

describe("PURC-004: accepted boundaries are sent unchanged", () => {
	test.each<[string, Partial<Record<FieldKey, string>>, boolean]>([
		["PURC-004-TC3 50 ASCII name", { name: "x".repeat(50) }, false],
		["PURC-004-TC5 30 ASCII category", { category: "x".repeat(30) }, false],
		["PURC-004-TC7 speed 0", { speed: "0" }, false],
		["PURC-004-TC7 speed 100000", { speed: "100000" }, false],
		["PURC-004-TC9 stock 0", { stock: "0" }, false],
		["PURC-004-TC9 stock 100000", { stock: "100000" }, false],
		["PURC-004-TC11 temporary with speed 0", { speed: "0" }, true],
		["PURC-004-TC12 regular with speed 0", { speed: "0" }, false],
		[
			"spec §3 / PURC-014-TC5 surrounding spaces are not trimmed",
			{ name: " 牛乳 ", category: ` 食品${IDEOGRAPHIC_SPACE}` },
			false,
		],
		[
			"PURC-014-TC6 full-width name is not normalized",
			{ name: "Ｍｉｌｋ" },
			false,
		],
	])("%s", async (_name, overrides, isTemporary) => {
		const user = userEvent.setup();
		renderDialog();
		await fill(user, overrides, isTemporary);
		await submit(user);
		const values = { ...validInput, ...overrides };
		await waitFor(() =>
			expect(createPurchase).toHaveBeenCalledWith({
				name: values.name,
				category: values.category,
				speed: Number(values.speed),
				stock: Number(values.stock),
				is_temporary: isTemporary,
			}),
		);
		expect(createPurchase).toHaveBeenCalledTimes(1);
	});

	// DEFECT-003: the UI counts UTF-16 code units, so 50 (30) surrogate-pair
	// characters are rejected although the spec limit is 50 (30) characters and
	// the API accepts them.
	test.fails.each<[string, Partial<Record<FieldKey, string>>]>([
		["PURC-004-TC3 50 surrogate name", { name: SURROGATE.repeat(50) }],
		["PURC-004-TC5 30 surrogate category", { category: SURROGATE.repeat(30) }],
	])("%s", async (_name, overrides) => {
		const user = userEvent.setup();
		renderDialog();
		await fill(user, overrides);
		await submit(user);
		const values = { ...validInput, ...overrides };
		await waitFor(() =>
			expect(createPurchase).toHaveBeenCalledWith({
				name: values.name,
				category: values.category,
				speed: 1,
				stock: 2,
				is_temporary: false,
			}),
		);
	});
});
