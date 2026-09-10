import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes.main import api_router
from core.config import DEBUG, FRONTEND_DIR, HOST, PORT
from core.db import init_db

app = FastAPI(title="MAX Mini App API", debug=DEBUG)
app.include_router(api_router)


@app.on_event("startup")
async def startup() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
