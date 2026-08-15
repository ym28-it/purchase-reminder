import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { afterEach, beforeEach } from "vitest";
import { queryClient } from "@/api/queryClient";

// usePurchases.ts は @/api/queryClient のシングルトンを直接 invalidateQueries するため、
// テスト側の QueryClientProvider にも同じシングルトンを渡す必要がある（別インスタンスだと
// invalidateがコンポーネントの購読しているクライアントに届かない）。
export function queryClientWrapper({ children }: { children: ReactNode }) {
	return (
		<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
	);
}

export function setUpIsolatedQueryClient() {
	beforeEach(() => {
		queryClient.setDefaultOptions({
			queries: { retry: false },
			mutations: { retry: false },
		});
	});

	afterEach(() => {
		queryClient.clear();
	});
}
