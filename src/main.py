from fastapi import FastAPI
from src.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the EFL Global IDP API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
