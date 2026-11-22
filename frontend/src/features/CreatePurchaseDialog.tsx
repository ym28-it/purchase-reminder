import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreatePurchase } from "@/hooks/usePurchases";

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

type CreatePurchaseFormField =
	| "name"
	| "category"
	| "unit"
	| "daysPerUnit"
	| "bufferDays"
	| "stock"
	| "isTemporary";

/** APIのフィールド名（リクエストボディ）から画面の入力項目への対応。 */
const apiFieldToFormField: Record<string, CreatePurchaseFormField> = {
	name: "name",
	category: "category",
	unit: "unit",
	days_per_unit: "daysPerUnit",
	buffer_days: "bufferDays",
	stock: "stock",
	is_temporary: "isTemporary",
};

/** APIの422応答（`detail[].loc`）から、問題のある入力項目を取り出す。 */
function invalidFormFields(error: unknown): CreatePurchaseFormField[] {
	if (!(error instanceof ApiError) || error.status !== 422) return [];
	const body = error.body;
	if (!body || typeof body !== "object" || !("detail" in body)) return [];
	if (!Array.isArray(body.detail)) return [];
	const fields = new Set<CreatePurchaseFormField>();
	for (const entry of body.detail) {
		const loc: unknown = entry?.loc;
		if (!Array.isArray(loc) || loc.length !== 2 || loc[0] !== "body") continue;
		const formField = apiFieldToFormField[String(loc[1])];
		if (formField) fields.add(formField);
	}
	return [...fields];
}

const createPurchaseFormSchema = z.object({
	name: requiredText("名前を入力してください", 50),
	category: requiredText("カテゴリを入力してください", 30),
	unit: requiredText("購入単位を入力してください", 10),
	daysPerUnit: quantity("1単位を使い切る日数を入力してください", 365),
	bufferDays: quantity("余裕日数を入力してください", 30),
	stock: quantity("在庫を入力してください"),
	isTemporary: z.boolean(),
});

export function CreatePurchaseDialog({
	open,
	onOpenChange,
}: {
	open: boolean;
	onOpenChange: (open: boolean) => void;
}) {
	const {
		register,
		handleSubmit,
		reset,
		setError,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(createPurchaseFormSchema),
		defaultValues: {
			name: "",
			category: "",
			unit: "",
			daysPerUnit: 0,
			bufferDays: 0,
			stock: 0,
			isTemporary: false,
		},
	});
	const createPurchase = useCreatePurchase();
	const duplicateError =
		createPurchase.error instanceof ApiError &&
		createPurchase.error.status === 409;
	const fieldError = invalidFormFields(createPurchase.error).length > 0;

	const onSubmit = handleSubmit((values) => {
		createPurchase.mutate(
			{
				name: values.name,
				category: values.category,
				unit: values.unit,
				days_per_unit: values.daysPerUnit,
				buffer_days: values.bufferDays,
				stock: values.stock,
				is_temporary: values.isTemporary,
			},
			{
				onSuccess: () => {
					reset();
					onOpenChange(false);
				},
				onError: (error) => {
					for (const formField of invalidFormFields(error)) {
						setError(formField, { message: "入力内容を修正してください" });
					}
				},
			},
		);
	});

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!next) {
					reset();
					createPurchase.reset();
				}
				onOpenChange(next);
			}}
		>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>購入物を追加</DialogTitle>
				</DialogHeader>

				<form onSubmit={onSubmit} className="flex flex-col gap-4">
					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-name">名前</Label>
						<Input id="create-name" {...register("name")} />
						{errors.name && (
							<p className="text-destructive text-sm">{errors.name.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-category">カテゴリ</Label>
						<Input id="create-category" {...register("category")} />
						{errors.category && (
							<p className="text-destructive text-sm">
								{errors.category.message}
							</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-unit">購入単位（パック、本など）</Label>
						<Input id="create-unit" {...register("unit")} />
						{errors.unit && (
							<p className="text-destructive text-sm">{errors.unit.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-days-per-unit">
							1単位を使い切る日数（日）
						</Label>
						<Input
							id="create-days-per-unit"
							type="number"
							step="any"
							{...register("daysPerUnit", { valueAsNumber: true })}
						/>
						{errors.daysPerUnit && (
							<p className="text-destructive text-sm">
								{errors.daysPerUnit.message}
							</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-buffer-days">余裕日数（日）</Label>
						<Input
							id="create-buffer-days"
							type="number"
							step="any"
							{...register("bufferDays", { valueAsNumber: true })}
						/>
						{errors.bufferDays && (
							<p className="text-destructive text-sm">
								{errors.bufferDays.message}
							</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-stock">在庫（購入単位の数）</Label>
						<Input
							id="create-stock"
							type="number"
							step="any"
							{...register("stock", { valueAsNumber: true })}
						/>
						{errors.stock && (
							<p className="text-destructive text-sm">{errors.stock.message}</p>
						)}
					</div>

					<label className="flex items-center gap-2 text-sm">
						<input type="checkbox" {...register("isTemporary")} />
						一時的な購入（定期購入しない）
					</label>
					{errors.isTemporary && (
						<p className="text-destructive text-sm">
							{errors.isTemporary.message}
						</p>
					)}

					{createPurchase.isError && !fieldError && (
						<p className="text-destructive text-sm">
							{duplicateError
								? "同じ名前とカテゴリの購入物は既に存在します。名前またはカテゴリを変更してください"
								: "登録に失敗しました"}
						</p>
					)}

					<DialogFooter>
						<Button type="submit" disabled={createPurchase.isPending}>
							{createPurchase.isPending ? "登録中..." : "登録する"}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}
