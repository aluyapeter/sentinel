from fastapi import FastAPI
from app.routers import users, kyc, webhooks, internal

app = FastAPI(title="Sentinel Service")
app.include_router(users.router)
app.include_router(kyc.router)
app.include_router(webhooks.router)
app.include_router(internal.router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "identity-service running"}