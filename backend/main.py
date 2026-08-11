from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.purchase import router as purchase_router

app = FastAPI(title="Purchase Reminder API")
app.add_middleware(
    CORSMiddleware,
    # devサーバー(Vite)はポートが埋まっていると別ポートにフォールバックするため、
    # localhostの任意ポートを許可する。本番のオリジン(CloudFrontドメイン)は
    # デプロイ構成が固まった時点で明示的なallow_originsに切り替える。
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(purchase_router)
