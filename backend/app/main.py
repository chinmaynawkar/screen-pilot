from fastapi import FastAPI

from backend.app.api.routes import router as api_router


app = FastAPI(title="ScreenPilot Backend")

app.include_router(api_router, prefix="/api")

