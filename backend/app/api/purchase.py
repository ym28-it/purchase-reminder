"""purchaseのルーティング。HTTPのリクエスト/レスポンス変換のみを担い、
ビジネスロジックはservicesに委譲する。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user_id
from app.api.schemas.purchase import PurchaseCreateRequest, PurchasePutRequest, PurchaseResponse
from app.services.purchase_service import (
    create_purchase,
    delete_purchase,
    get_all_purchases,
    put_purchase,
)

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.get("", response_model=list[PurchaseResponse], status_code=status.HTTP_200_OK)
def get_all_purchase_endpoint(
    user_id: str = Depends(get_current_user_id),
) -> list[PurchaseResponse]:
    purchases = get_all_purchases(user_id)
    return [PurchaseResponse.model_validate(purchase) for purchase in purchases]


@router.post("", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_endpoint(
    request: PurchaseCreateRequest,
    user_id: str = Depends(get_current_user_id),
) -> PurchaseResponse:
    purchase = create_purchase(
        user_id=user_id,
        name=request.name,
        category=request.category,
        speed=request.speed,
        stock=request.stock,
        is_temporary=request.is_temporary,
    )
    return PurchaseResponse.model_validate(purchase)


@router.put("/{purchase_id}", response_model=PurchaseResponse, status_code=status.HTTP_200_OK)
def put_purchase_endpoint(
    purchase_id: UUID,
    request: PurchasePutRequest,
    user_id: str = Depends(get_current_user_id),
) -> PurchaseResponse:
    purchase = put_purchase(
        user_id=user_id,
        id=purchase_id,
        name=request.name,
        category=request.category,
        speed=request.speed,
        stock=request.stock,
        is_temporary=request.is_temporary,
    )
    return PurchaseResponse.model_validate(purchase)


@router.delete("/{purchase_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_endpoint(
    purchase_id: UUID,
    user_id: str = Depends(get_current_user_id),
) -> None:
    delete_purchase(user_id, purchase_id)
