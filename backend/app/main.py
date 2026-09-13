from fastapi import FastAPI

app = FastAPI(title="GameScope API")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
