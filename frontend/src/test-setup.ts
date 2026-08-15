import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// vitest.config.ts で test.globals を有効にしていないため、@testing-library/react の
// 自動afterEachクリーンアップ検出が働かない。手動で登録しないとPortal経由でmountされる
// ダイアログ（Radix）が次のテストに残り、pointer-events:none等の副作用でテストが壊れる。
afterEach(() => {
	cleanup();
});
