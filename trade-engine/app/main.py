from fastapi import FastAPI

app = FastAPI(title="Sentinel Service")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "trade-engine running"}