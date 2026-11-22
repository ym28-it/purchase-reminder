import { z } from "zod";

/** API（Python）と同じくコードポイント単位で文字数を数える。 */
function codePointLength(value: string): number {
	return [...value].length;
}

function requiredText(emptyMessage: string, maxLength: number) {
	return z
		.string()
		.refine((value) => value.trim().length > 0, emptyMessage)
		.refine(
			(value) => codePointLength(value) <= maxLength,
			`${maxLength}文字以内で入力してください`,
		);
}

/** 空欄はNaNになり、0として送らずに入力エラーにする。 */
function quantity(emptyMessage: string, max = 100000) {
	return z
		.number({ error: emptyMessage })
		.int("整数を入力してください")
		.min(0, "0以上を入力してください")
		.max(max, `${max}以下を入力してください`);
}

/** 登録・編集ダイアログが共有する7項目の入力検証。 */
export const purchaseFormSchema = z.object({
	name: requiredText("名前を入力してください", 50),
	category: requiredText("カテゴリを入力してください", 30),
	unit: requiredText("購入単位を入力してください", 10),
	daysPerUnit: quantity("1単位を使い切る日数を入力してください", 365),
	bufferDays: quantity("余裕日数を入力してください", 30),
	stock: quantity("在庫を入力してください"),
	isTemporary: z.boolean(),
});
