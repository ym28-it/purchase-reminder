import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCreatePurchase } from "@/hooks/usePurchases";

const purchaseFormSchema = z.object({
	name: z.string().min(1, "名前を入力してください"),
	category: z.string().min(1, "カテゴリを入力してください"),
	speed: z.coerce.number().positive("0より大きい値を入力してください"),
	stock: z.coerce.number().min(0, "0以上を入力してください"),
	isTemporary: z.boolean(),
});

export function Purchase() {
	const {
		register,
		handleSubmit,
		reset,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(purchaseFormSchema),
		defaultValues: {
			name: "",
			category: "",
			speed: 0,
			stock: 0,
			isTemporary: false,
		},
	});
	const createPurchase = useCreatePurchase();

	const onSubmit = handleSubmit((values) => {
		createPurchase.mutate(
			{
				name: values.name,
				category: values.category,
				speed: values.speed,
				stock: values.stock,
				is_temporary: values.isTemporary,
			},
			{ onSuccess: () => reset() },
		);
	});

	return (
		<form
			onSubmit={onSubmit}
			className="mx-auto flex max-w-sm flex-col gap-4 p-6"
		>
			<div className="flex flex-col gap-1.5">
				<Label htmlFor="name">名前</Label>
				<Input id="name" {...register("name")} />
				{errors.name && (
					<p className="text-destructive text-sm">{errors.name.message}</p>
				)}
			</div>

			<div className="flex flex-col gap-1.5">
				<Label htmlFor="category">カテゴリ</Label>
				<Input id="category" {...register("category")} />
				{errors.category && (
					<p className="text-destructive text-sm">{errors.category.message}</p>
				)}
			</div>

			<div className="flex flex-col gap-1.5">
				<Label htmlFor="speed">消費スピード（個/日）</Label>
				<Input id="speed" type="number" step="any" {...register("speed")} />
				{errors.speed && (
					<p className="text-destructive text-sm">{errors.speed.message}</p>
				)}
			</div>

			<div className="flex flex-col gap-1.5">
				<Label htmlFor="stock">現在の在庫</Label>
				<Input id="stock" type="number" step="any" {...register("stock")} />
				{errors.stock && (
					<p className="text-destructive text-sm">{errors.stock.message}</p>
				)}
			</div>

			<label className="flex items-center gap-2 text-sm">
				<input type="checkbox" {...register("isTemporary")} />
				一時的な購入（定期購入しない）
			</label>

			<Button type="submit" disabled={createPurchase.isPending}>
				{createPurchase.isPending ? "登録中..." : "登録する"}
			</Button>

			{createPurchase.isSuccess && (
				<p className="text-emerald-600 text-sm">登録しました</p>
			)}
			{createPurchase.isError && (
				<p className="text-destructive text-sm">登録に失敗しました</p>
			)}
		</form>
	);
}
