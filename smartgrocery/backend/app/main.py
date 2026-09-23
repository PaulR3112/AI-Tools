import logging

from fastapi import FastAPI

from app.api.v1 import admin, router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="SmartGrocery API",
    version="0.1.0",
    description="Čo, kde a za koľko kúpim – ponuky zo supermarketov v ČR s jednotkovou cenou a zdrojom.",
)
app.include_router(router)
app.include_router(admin)


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok"}
