"""永続化層（models）の例外をHTTPレスポンスへ変換する。

api層の責務（HTTPのリクエスト/レスポンス変換）の一部。エンティティ固有ではなく
``app/models/exceptions.py``の汎用例外に対応するため、特定のルーター
（``app/api/purchase.py``など）ではなくアプリ全体に対して一括登録する。
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.models.exceptions import DuplicatePurchaseError, ItemAlreadyExistsError, ItemNotFoundError


async def _item_not_found_handler(_request: Request, exc: ItemNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def _item_already_exists_handler(
    _request: Request, exc: ItemAlreadyExistsError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


async def _duplicate_purchase_handler(
    _request: Request, exc: DuplicatePurchaseError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    """永続化層の例外に対するハンドラをアプリへ登録する。"""
    app.add_exception_handler(ItemNotFoundError, _item_not_found_handler)
    app.add_exception_handler(ItemAlreadyExistsError, _item_already_exists_handler)
    app.add_exception_handler(DuplicatePurchaseError, _duplicate_purchase_handler)
