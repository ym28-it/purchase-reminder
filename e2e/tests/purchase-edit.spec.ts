// Representative E2E for purchase-edit-fields (PEDT; docs/superpowers/specs/2026-11-22-purchase-edit-fields-test-cases.md).
// Boundaries and rejections are covered by the API integration and component tests;
// this runs the main flow once: change the purchase unit and buffer days in the edit
// dialog, see them on the list, and confirm them after a reload and in storage.
import { expect, test } from "@playwright/test";

const API = `http://localhost:${process.env.E2E_API_PORT ?? 8000}`;

test("PEDT-007-TC4 / PEDT-005-TC1 / PEDT-006-TC2: change unit and buffer days, see them on the list and after reload", async ({
	page,
}) => {
	await page.goto("/");
	await page.getByRole("button", { name: "追加" }).click();
	const createDialog = page.getByRole("dialog");
	await createDialog.getByLabel("名前", { exact: true }).fill("編集用の牛乳");
	await createDialog.getByLabel("カテゴリ", { exact: true }).fill("食品");
	await createDialog.getByLabel(/^購入単位/).fill("パック");
	await createDialog.getByLabel(/使い切る日数/).fill("3");
	await createDialog.getByLabel(/余裕日数/).fill("0");
	await createDialog.getByLabel(/^在庫/).fill("2");
	await createDialog.getByRole("button", { name: "登録する" }).click();
	await expect(createDialog).toBeHidden();

	const item = page.getByRole("listitem").filter({ hasText: "編集用の牛乳" });
	await expect(item).toContainText("1パック3日");
	await expect(item).toContainText(/余裕\s*0日/);
	const before = (
		(await (await page.request.get(`${API}/purchases`)).json()) as Array<
			Record<string, unknown>
		>
	).find((p) => p.name === "編集用の牛乳");
	expect(before).toBeDefined();

	await item.getByRole("button", { name: "編集" }).click();
	const dialog = page.getByRole("dialog");
	await expect(dialog.getByLabel(/^購入単位/)).toHaveValue("パック");
	await dialog.getByLabel(/^購入単位/).fill("本");
	await dialog.getByLabel(/余裕日数/).fill("2");
	await dialog.getByRole("button", { name: "更新する" }).click();

	await expect(dialog).toBeHidden();
	await expect(item).toContainText("1本3日");
	await expect(item).toContainText(/余裕\s*2日/);
	await expect(item).toContainText("2本");

	await page.reload();
	const reloaded = page.getByRole("listitem").filter({ hasText: "編集用の牛乳" });
	await expect(reloaded).toContainText("1本3日");
	await expect(reloaded).toContainText(/余裕\s*2日/);

	const after = (
		(await (await page.request.get(`${API}/purchases`)).json()) as Array<
			Record<string, unknown>
		>
	).find((p) => p.name === "編集用の牛乳");
	expect(after).toMatchObject({ unit: "本", buffer_days: 2, stock: 2 });
	expect(after?.created_at).toBe(before?.created_at);
	// stock was not edited, so the stock count time stays at registration (PEDT-006-TC2)
	expect(after?.stock_counted_at).toBe(before?.stock_counted_at);
});
