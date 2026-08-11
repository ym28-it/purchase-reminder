import { useMutation } from "@tanstack/react-query";
import { createPurchase } from "@/api/purchases";
import { queryClient } from "@/api/queryClient";

export function useCreatePurchase() {
	return useMutation({
		mutationFn: createPurchase,
		onSuccess: () => {
			// GET /purchases が実装されたら、この queryKey で一覧を取得するようになる想定
			queryClient.invalidateQueries({ queryKey: ["purchases"] });
		},
	});
}
