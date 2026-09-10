import os
from pathlib import Path

from app.models.complaint import Complaint
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv

from app.models.user import User


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

MONGODB_URL = os.getenv("MONGODB_URL")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")

# Add your Beanie Document models here as you create them.
DOCUMENT_MODELS = [User,Complaint]

client: AsyncIOMotorClient | None = None


async def init_db():
    global client

    if not MONGODB_URL:
        raise ValueError("MONGODB_URL is not set in .env")

    if not MONGODB_DB_NAME:
        raise ValueError("MONGODB_DB_NAME is not set in .env")

    client = AsyncIOMotorClient(MONGODB_URL)

    # Verify MongoDB connection
    await client.admin.command("ping")

    database = client[MONGODB_DB_NAME]

    await init_beanie(
        database=database,
        document_models=DOCUMENT_MODELS,
    )

    print("MongoDB connected successfully")


async def close_db():
    if client:
        client.close()