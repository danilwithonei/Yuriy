from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import create_db_and_tables
from routers import assist, auth, cases, intake, internal, ws


@asynccontextmanager
async def lifespan(app):
    create_db_and_tables()
    yield


app = FastAPI(title="Yuriy Lawyer Dashboard Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(internal.router)
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(intake.router)
app.include_router(assist.router)
app.include_router(ws.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
