import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
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
		reset,
		formState: { errors },
	} = useForm({
		resolver: zodResolver(purchaseFormSchema),
		// purchaseの中身が変わる（別の行を編集し始める）たびにこの値でフォームを再初期化する。
		// 同じ購入物を開き直す場合は値が変わらず再同期されないため、下のeffectで開くたびにリセットする。
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

	// 開くたびに保存済みの値へ戻す（閉じる前の未保存・不正な入力を持ち越さない）。
	// reset()はvaluesオプション由来の保存済みの値へ戻す。
	const isOpen = purchase !== null;
	useEffect(() => {
		if (isOpen) reset();
	}, [isOpen, reset]);

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
