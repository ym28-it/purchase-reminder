from fastapi import FastAPI

from app.api.purchase import router as purchase_router

app = FastAPI(title="Purchase Reminder API")
app.include_router(purchase_router)
