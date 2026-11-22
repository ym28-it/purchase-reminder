"""Post-implementation unit coverage for ``apply_edit`` (purchase-timing-fields).

Expected results come from the approved logical test cases
(docs/superpowers/specs/2026-11-12-purchase-timing-fields-test-cases.md) and the
plan Review Focus only.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.purchase import Purchase, apply_edit

REGISTERED_AT = datetime(2026, 11, 22, 0, 0, 0, tzinfo=UTC)
EDITED_AT = REGISTERED_AT + timedelta(hours=1)


def registered(stock: float = 2) -> Purchase:
    return Purchase(
        id=uuid4(),
        user_id="user-a",
        name="牛乳",
        category="食品",
        unit="パック",
        days_per_unit=3,
        buffer_days=2,
        stock=stock,
        is_temporary=False,
        stock_counted_at=REGISTERED_AT,
        created_at=REGISTERED_AT,
        updated_at=REGISTERED_AT,
    )


def edit(current: Purchase, **overrides: object) -> Purchase:
    values: dict[str, object] = {
        "name": current.name,
        "category": current.category,
        "unit": current.unit,
        "buffer_days": current.buffer_days,
        "days_per_unit": current.days_per_unit,
        "stock": current.stock,
        "is_temporary": current.is_temporary,
        "now": EDITED_AT,
    }
    values.update(overrides)
    return apply_edit(current, **values)  # type: ignore[arg-type]


def test_ptf_013_tc1_stock_change_recounts_at_the_edit_time() -> None:
    edited = edit(registered(stock=2), stock=5)

    assert edited.stock_counted_at == edited.updated_at == EDITED_AT


def test_ptf_013_tc2_and_007_tc1_same_stock_keeps_stock_counted_at() -> None:
    edited = edit(registered(stock=2), name="豆乳", category="飲料")

    assert edited.stock_counted_at == REGISTERED_AT
    assert edited.updated_at == EDITED_AT


@pytest.mark.parametrize(("stored", "sent"), [(2, 2.0), (2.0, 2), (0, 0.0)])
def test_review_focus_5_integer_and_float_stock_are_the_same_stock(
    stored: float, sent: float
) -> None:
    edited = edit(registered(stock=stored), stock=sent)

    assert edited.stock_counted_at == REGISTERED_AT


def test_review_focus_1_and_ptf_012_edit_keeps_created_at_replaces_unit_buffer() -> None:
    current = registered()

    edited = edit(current, unit="個", buffer_days=7, days_per_unit=5, stock=9)

    assert edited.created_at == REGISTERED_AT
    assert (edited.unit, edited.buffer_days) == ("個", 7)
    assert edited.days_per_unit == 5
    assert edited.id == current.id
    assert edited.user_id == current.user_id
