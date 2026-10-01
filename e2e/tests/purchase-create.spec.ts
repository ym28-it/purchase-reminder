// Representative E2E for purchase-create (docs/specs/purchase-create-test-cases.md).
// Each test runs against the shared, initially empty DynamoDB Local table and
// uses distinct names, so tests are executed serially (workers: 1).
import { expect, type Page, test } from "@playwright/test";

const API = `http://localhost:${process.env.E2E_API_PORT ?? 8000}`;

type Input = {
	name: string;
	category: string;
	speed: string;
	stock: string;
	isTemporary: boolean;
};

async function openAndFill(page: Page, input: Input) {
	await page.getByRole("button", { name: "追加" }).click();
	const dialog = page.getByRole("dialog");
	await expect(dialog).toBeVisible();
	await dialog.getByLabel("名前", { exact: true }).fill(input.name);
	await dialog.getByLabel("カテゴリ", { exact: true }).fill(input.category);
	await dialog.getByLabel(/消費スピード/).fill(input.speed);
	await dialog.getByLabel(/現在の在庫/).fill(input.stock);
	if (input.isTemporary) await dialog.getByLabel(/一時的な購入/).check();
	return dialog;
}

async function storedPurchases(page: Page) {
	const response = await page.request.get(`${API}/purchases`);
	expect(response.status()).toBe(200);
	return (await response.json()) as Array<Record<string, unknown>>;
}

test("PURC-009-TC2 (+PURC-001/005/010/011/012, PURC-014-TC1/016-TC1): register, reload, and reject the duplicate", async ({
	page,
}) => {
	const milk: Input = {
		name: "牛乳",
		category: "食品",
		speed: "3",
		stock: "4",
		isTemporary: true,
	};
	await page.goto("/");
	await expect(page.getByText("まだ登録されていません")).toBeVisible();

	const dialog = await openAndFill(page, milk);
	await dialog.getByRole("button", { name: "登録する" }).click();

	await expect(dialog).toBeHidden();
	const item = page.getByRole("listitem").filter({ hasText: "牛乳" });
	await expect(item).toHaveCount(1);
	await expect(item).toContainText("食品");
	await expect(item).toContainText(/消費スピード\s*3/);
	await expect(item).toContainText(/在庫\s*4/);
	await expect(item).toContainText("一時的");

	// PURC-009-TC2: the purchase survives a full page reload (re-fetched from storage).
	await page.reload();
	await expect(page.getByRole("listitem").filter({ hasText: "牛乳" })).toHaveCount(1);
	const stored = await storedPurchases(page);
	expect(stored).toHaveLength(1);
	expect(stored[0]).toMatchObject({
		name: "牛乳",
		category: "食品",
		speed: 3,
		stock: 4,
		is_temporary: true,
	});

	// PURC-014-TC1 / PURC-015-TC1 / PURC-016-TC1 across the real API: duplicate is
	// rejected, the dialog keeps every input, and the cause is shown.
	const duplicateDialog = await openAndFill(page, { ...milk, speed: "9" });
	await duplicateDialog.getByRole("button", { name: "登録する" }).click();
	await expect(duplicateDialog.getByText(/既に存在|重複/)).toBeVisible();
	await expect(duplicateDialog.getByLabel("名前", { exact: true })).toHaveValue("牛乳");
	await expect(duplicateDialog.getByLabel(/消費スピード/)).toHaveValue("9");
	await expect(duplicateDialog.getByLabel(/一時的な購入/)).toBeChecked();
	expect(await storedPurchases(page)).toHaveLength(1);
});

test("PURC-013-TC2: a rapid double submit persists exactly one purchase", async ({
	page,
}) => {
	await page.goto("/");
	await expect(page.getByRole("button", { name: "追加" })).toBeVisible();
	const posts: string[] = [];
	page.on("request", (request) => {
		if (request.method() === "POST" && request.url().endsWith("/purchases")) {
			posts.push(request.url());
		}
	});

	const dialog = await openAndFill(page, {
		name: "卵",
		category: "食品",
		speed: "1",
		stock: "10",
		isTemporary: false,
	});
	await dialog.getByRole("button", { name: "登録する" }).dblclick();

	await expect(dialog).toBeHidden();
	await expect(page.getByRole("listitem").filter({ hasText: "卵" })).toHaveCount(1);
	const eggs = (await storedPurchases(page)).filter((p) => p.name === "卵");
	expect(eggs).toHaveLength(1);
	expect(posts).toHaveLength(1);
});
