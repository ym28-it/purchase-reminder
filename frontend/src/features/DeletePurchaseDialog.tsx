import type { PurchaseResponse } from "@/api/purchases";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useDeletePurchase } from "@/hooks/usePurchases";

export function DeletePurchaseDialog({
	purchase,
	onOpenChange,
}: {
	purchase: PurchaseResponse | null;
	onOpenChange: (open: boolean) => void;
}) {
	const deletePurchase = useDeletePurchase();

	return (
		<AlertDialog open={purchase !== null} onOpenChange={onOpenChange}>
			<AlertDialogContent>
				<AlertDialogHeader>
					<AlertDialogTitle>購入物を削除しますか？</AlertDialogTitle>
					<AlertDialogDescription>
						「{purchase?.name}」を削除します。この操作は取り消せません。
					</AlertDialogDescription>
				</AlertDialogHeader>
				{deletePurchase.isError && (
					<p className="text-destructive text-sm">削除に失敗しました</p>
				)}
				<AlertDialogFooter>
					<AlertDialogCancel disabled={deletePurchase.isPending}>
						キャンセル
					</AlertDialogCancel>
					<AlertDialogAction
						disabled={deletePurchase.isPending}
						onClick={(event) => {
							event.preventDefault();
							if (!purchase) return;
							deletePurchase.mutate(purchase.id, {
								onSuccess: () => onOpenChange(false),
							});
						}}
					>
						{deletePurchase.isPending ? "削除中..." : "削除する"}
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
