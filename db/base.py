
from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)
