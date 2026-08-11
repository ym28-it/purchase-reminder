import { apiClient } from "./client";
import type { components } from "./schema";

export type PurchaseCreateRequest =
	components["schemas"]["PurchaseCreateRequest"];
export type PurchaseResponse = components["schemas"]["PurchaseResponse"];

export async function createPurchase(
	input: PurchaseCreateRequest,
): Promise<PurchaseResponse> {
	const { data, error } = await apiClient.POST("/purchases", { body: input });
	if (error) throw error;
	return data;
}
