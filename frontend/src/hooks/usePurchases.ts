import { useMutation, useQuery } from "@tanstack/react-query";
import { createPurchase, getAllPurchases } from "@/api/purchases";
import { queryClient } from "@/api/queryClient";

export function useCreatePurchase() {
	return useMutation({
		mutationFn: createPurchase,
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["purchases"] });
		},
	});
}

export function usePurchases() {
	return useQuery({
		queryKey: ["purchases"],
		queryFn: getAllPurchases,
	});
}
