from fastapi import FastAPI
from app.routers import tenants, api_key, internal

app = FastAPI(title="Sentinel Platform API")
app.include_router(tenants.router)
app.include_router(api_key.router)
app.include_router(internal.router)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "platform-api"
    }