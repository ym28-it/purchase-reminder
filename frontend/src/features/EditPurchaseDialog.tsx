import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import type { PurchaseResponse } from "@/api/purchases";
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
import { usePutPurchase } from "@/hooks/usePurchases";

const editPurchaseFormSchema = z.object({
	name: z.string().min(1, "名前を入力してください"),
	category: z.string().min(1, "カテゴリを入力してください"),
	speed: z.coerce.number().positive("0より大きい値を入力してください"),
	stock: z.coerce.number().min(0, "0以上を入力してください"),
	isTemporary: z.boolean(),
});

export function EditPurchaseDialog({
	purchase,
	onOpenChange,
}: {
	purchase: PurchaseResponse | null;
	onOpenChange: (open: boolean) => void;
}) {
	const {
		register,
		handleSubmit,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(editPurchaseFormSchema),
		// purchaseが変わる（別の行を編集し始める）たびにこの値でフォームを再初期化する。
		// react-hook-formのvaluesオプションが、参照が変わった時の再同期を面倒見てくれるので
		// useEffectで手動リセットする必要はない。
		values: purchase
			? {
					name: purchase.name,
					category: purchase.category,
					speed: purchase.speed,
					stock: purchase.stock,
					isTemporary: purchase.is_temporary,
				}
			: undefined,
	});
	const putPurchase = usePutPurchase();

	const onSubmit = handleSubmit((values) => {
		if (!purchase) return;
		putPurchase.mutate(
			{
				purchaseId: purchase.id,
				input: {
					name: values.name,
					category: values.category,
					speed: values.speed,
					stock: values.stock,
					is_temporary: values.isTemporary,
				},
			},
			{ onSuccess: () => onOpenChange(false) },
		);
	});

	return (
		<Dialog open={purchase !== null} onOpenChange={onOpenChange}>
			<DialogContent>
				<DialogHeader>
					<DialogTitle>購入物を編集</DialogTitle>
				</DialogHeader>

				<form onSubmit={onSubmit} className="flex flex-col gap-4">
					<div className="flex flex-col gap-1.5">
						<Label htmlFor="edit-name">名前</Label>
						<Input id="edit-name" {...register("name")} />
						{errors.name && (
							<p className="text-destructive text-sm">{errors.name.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="edit-category">カテゴリ</Label>
						<Input id="edit-category" {...register("category")} />
						{errors.category && (
							<p className="text-destructive text-sm">
								{errors.category.message}
							</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="edit-speed">消費スピード（個/日）</Label>
						<Input
							id="edit-speed"
							type="number"
							step="any"
							{...register("speed")}
						/>
						{errors.speed && (
							<p className="text-destructive text-sm">{errors.speed.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="edit-stock">現在の在庫</Label>
						<Input
							id="edit-stock"
							type="number"
							step="any"
							{...register("stock")}
						/>
						{errors.stock && (
							<p className="text-destructive text-sm">{errors.stock.message}</p>
						)}
					</div>

					<label className="flex items-center gap-2 text-sm">
						<input type="checkbox" {...register("isTemporary")} />
						一時的な購入（定期購入しない）
					</label>

					{putPurchase.isError && (
						<p className="text-destructive text-sm">更新に失敗しました</p>
					)}

					<DialogFooter>
						<Button type="submit" disabled={putPurchase.isPending}>
							{putPurchase.isPending ? "更新中..." : "更新する"}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}
