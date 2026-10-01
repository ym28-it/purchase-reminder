import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
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
function quantity(emptyMessage: string) {
	return z
		.number({ error: emptyMessage })
		.int("整数を入力してください")
		.min(0, "0以上を入力してください")
		.max(100000, "100000以下を入力してください");
}

const createPurchaseFormSchema = z.object({
	name: requiredText("名前を入力してください", 50),
	category: requiredText("カテゴリを入力してください", 30),
	speed: quantity("消費スピードを入力してください"),
	stock: quantity("現在の在庫を入力してください"),
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
		formState: { errors },
	} = useForm({
		resolver: zodResolver(createPurchaseFormSchema),
		defaultValues: {
			name: "",
			category: "",
			speed: 0,
			stock: 0,
			isTemporary: false,
		},
	});
	const createPurchase = useCreatePurchase();
	const duplicateError =
		createPurchase.error &&
		typeof createPurchase.error === "object" &&
		"detail" in createPurchase.error &&
		createPurchase.error.detail ===
			"同じ名前とカテゴリの購入物は既に存在します";

	const onSubmit = handleSubmit((values) => {
		createPurchase.mutate(
			{
				name: values.name,
				category: values.category,
				speed: values.speed,
				stock: values.stock,
				is_temporary: values.isTemporary,
			},
			{
				onSuccess: () => {
					reset();
					onOpenChange(false);
				},
			},
		);
	});

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!next) reset();
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
						<Label htmlFor="create-speed">消費スピード（個/日）</Label>
						<Input
							id="create-speed"
							type="number"
							step="any"
							{...register("speed", { valueAsNumber: true })}
						/>
						{errors.speed && (
							<p className="text-destructive text-sm">{errors.speed.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="create-stock">現在の在庫</Label>
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

					{createPurchase.isError && (
						<p className="text-destructive text-sm">
							{duplicateError
								? "同じ名前とカテゴリの購入物は既に存在します"
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
