from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from places import router as places_router

app = FastAPI(title="Hearth API")

# Allow the frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Fine for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Hearth backend is running!"
    }


app.include_router(
    places_router,
    prefix="/api",
)