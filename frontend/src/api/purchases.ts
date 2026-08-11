import { apiClient } from "./client";
import type { components } from "./schema";

export type PurchaseCreateRequest =
	components["schemas"]["PurchaseCreateRequest"];
export type PurchasePutRequest = components["schemas"]["PurchasePutRequest"];
export type PurchaseResponse = components["schemas"]["PurchaseResponse"];

export async function createPurchase(
	input: PurchaseCreateRequest,
): Promise<PurchaseResponse> {
	const { data, error } = await apiClient.POST("/purchases", { body: input });
	if (error) throw error;
	return data;
}

export async function putPurchase(
	purchaseId: string,
	input: PurchasePutRequest,
): Promise<PurchaseResponse> {
	const { data, error } = await apiClient.PUT("/purchases/{purchase_id}", {
		params: { path: { purchase_id: purchaseId } },
		body: input,
	});
	if (error) throw error;
	return data;
}

export async function getAllPurchases(): Promise<PurchaseResponse[]> {
	const { data, error } = await apiClient.GET("/purchases");
	if (error) throw error;
	return data;
}

export async function deletePurchase(purchaseId: string): Promise<void> {
	const { error } = await apiClient.DELETE("/purchases/{purchase_id}", {
		params: { path: { purchase_id: purchaseId } },
	});
	if (error) throw error;
}
