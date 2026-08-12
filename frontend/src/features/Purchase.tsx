import {
	Loader2,
	Package,
	PackageOpen,
	Pencil,
	Plus,
	Trash2,
} from "lucide-react";
import { useState } from "react";
import type { PurchaseResponse } from "@/api/purchases";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardAction,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { CreatePurchaseDialog } from "@/features/CreatePurchaseDialog";
import { DeletePurchaseDialog } from "@/features/DeletePurchaseDialog";
import { EditPurchaseDialog } from "@/features/EditPurchaseDialog";
import { usePurchases } from "@/hooks/usePurchases";

export function Purchase() {
	const { data: purchases, isPending: isPurchasesPending } = usePurchases();
	const [editingPurchase, setEditingPurchase] =
		useState<PurchaseResponse | null>(null);
	const [deletingPurchase, setDeletingPurchase] =
		useState<PurchaseResponse | null>(null);
	const [isCreateOpen, setIsCreateOpen] = useState(false);

	return (
		<div className="mx-auto flex max-w-sm flex-col gap-8 p-6">
			<Card>
				<CardHeader>
					<CardTitle>登録済みの購入物</CardTitle>
					<CardDescription>
						{isPurchasesPending
							? "読み込み中..."
							: `${purchases?.length ?? 0}件`}
					</CardDescription>
					<CardAction>
						<Button
							type="button"
							size="sm"
							onClick={() => setIsCreateOpen(true)}
						>
							<Plus className="size-4" />
							追加
						</Button>
					</CardAction>
				</CardHeader>
				<CardContent>
					{isPurchasesPending && (
						<div className="flex items-center justify-center gap-2 py-8 text-muted-foreground text-sm">
							<Loader2 className="size-4 animate-spin" />
							読み込み中...
						</div>
					)}

					{!isPurchasesPending && purchases?.length === 0 && (
						<div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
							<PackageOpen className="size-8" />
							<p className="text-sm">まだ登録されていません</p>
						</div>
					)}

					<ul className="flex flex-col gap-2">
						{purchases?.map((purchase) => (
							<li
								key={purchase.id}
								className="flex items-center justify-between gap-3 rounded-lg border p-3"
							>
								<div className="flex items-center gap-3">
									<div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-muted">
										<Package className="size-4 text-muted-foreground" />
									</div>
									<div>
										<p className="font-medium text-sm">{purchase.name}</p>
										<p className="text-muted-foreground text-xs">
											{purchase.category}
										</p>
									</div>
								</div>
								<div className="flex shrink-0 items-center gap-1.5">
									{purchase.is_temporary && (
										<Badge variant="secondary">一時的</Badge>
									)}
									<Badge variant="outline">在庫 {purchase.stock}</Badge>
									<Button
										type="button"
										variant="ghost"
										size="icon-sm"
										aria-label="編集"
										onClick={() => setEditingPurchase(purchase)}
									>
										<Pencil className="size-4" />
									</Button>
									<Button
										type="button"
										variant="ghost"
										size="icon-sm"
										aria-label="削除"
										onClick={() => setDeletingPurchase(purchase)}
									>
										<Trash2 className="size-4" />
									</Button>
								</div>
							</li>
						))}
					</ul>
				</CardContent>
			</Card>

			<CreatePurchaseDialog
				open={isCreateOpen}
				onOpenChange={setIsCreateOpen}
			/>

			<EditPurchaseDialog
				purchase={editingPurchase}
				onOpenChange={(open) => {
					if (!open) setEditingPurchase(null);
				}}
			/>

			<DeletePurchaseDialog
				purchase={deletingPurchase}
				onOpenChange={(open) => {
					if (!open) setDeletingPurchase(null);
				}}
			/>
		</div>
	);
}
