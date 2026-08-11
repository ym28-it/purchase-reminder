import { useMutation, useQuery } from "@tanstack/react-query";
import {
	createPurchase,
	getAllPurchases,
	type PurchasePutRequest,
	putPurchase,
} from "@/api/purchases";
import { queryClient } from "@/api/queryClient";

export function useCreatePurchase() {
	return useMutation({
		mutationFn: createPurchase,
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["purchases"] });
		},
	});
}

export function usePutPurchase() {
	return useMutation({
		mutationFn: ({
			purchaseId,
			input,
		}: {
			purchaseId: string;
			input: PurchasePutRequest;
		}) => putPurchase(purchaseId, input),
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
