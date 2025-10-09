
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import ai


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai.router)

@app.get("/health", status_code=200)
def read_root():
    return {"status": "healthy"}


