import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
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
import { purchaseFormSchema } from "./purchaseFormSchema";

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
		resolver: zodResolver(purchaseFormSchema),
		// purchaseが変わる（別の行を編集し始める）たびにこの値でフォームを再初期化する。
		// react-hook-formのvaluesオプションが、参照が変わった時の再同期を面倒見てくれるので
		// useEffectで手動リセットする必要はない。
		values: purchase
			? {
					name: purchase.name,
					category: purchase.category,
					unit: purchase.unit,
					daysPerUnit: purchase.days_per_unit,
					bufferDays: purchase.buffer_days,
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
					unit: values.unit,
					days_per_unit: values.daysPerUnit,
					buffer_days: values.bufferDays,
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
						<Label htmlFor="edit-unit">購入単位（パック、本など）</Label>
						<Input id="edit-unit" {...register("unit")} />
						{errors.unit && (
							<p className="text-destructive text-sm">{errors.unit.message}</p>
						)}
					</div>

					<div className="flex flex-col gap-1.5">
						<Label htmlFor="edit-days-per-unit">
							1単位を使い切る日数（日）
						</Label>
						<Input
							id="edit-days-per-unit"
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
						<Label htmlFor="edit-buffer-days">余裕日数（日）</Label>
						<Input
							id="edit-buffer-days"
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
						<Label htmlFor="edit-stock">在庫（購入単位の数）</Label>
						<Input
							id="edit-stock"
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
