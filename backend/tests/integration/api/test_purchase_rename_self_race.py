"""同じ購入物を同じ組へ改名する要求が競合した場合の回帰テスト（局所変更）。

PURC-023は「変更後の組が同じ利用者の**別の**購入物と完全一致する場合」だけを409と定める。
2つの要求がどちらも改名前のPを読み、同じ組Yへ改名すると、後の要求は自分自身の予約Yと
衝突する。これは別の購入物との重複ではないため、409ではなく編集を反映して成功する。

競合はPURC-TDD-008/009と同じ方法で決定的に再現する（改名の確定後、製品内での次のPの
読み取りだけを改名前のスナップショットに差し替える）。最終コードレビュー（第2版）Minor 1。
"""

import pytest
from fastapi.testclient import TestClient

from tests.integration.api.test_purchase_uniqueness_rev2 import (
    PAIR_Y,
    client,  # noqa: F401  # pytestフィクスチャとして使う
    create_and_rename,
    inject_stale_read,
    payload,
    purchases,
    register,
)

pytestmark = pytest.mark.integration


def test_purc_023_same_rename_racing_itself_is_not_a_duplicate(
    client: TestClient,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    purchase_id, snapshot = create_and_rename(client)

    inject_stale_read(monkeypatch, snapshot)
    renamed_again = client.put(f"/purchases/{purchase_id}", json=payload(PAIR_Y, stock=5))
    monkeypatch.undo()

    assert renamed_again.status_code == 200
    listed = purchases(client)
    assert [(item["id"], item["name"], item["category"], item["stock"]) for item in listed] == [
        (purchase_id, PAIR_Y[0], PAIR_Y[1], 5)
    ]
    assert register(client, PAIR_Y).status_code == 409
