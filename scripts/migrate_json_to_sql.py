
from __future__ import annotations
import json, pathlib, asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import engine, SessionLocal
from db.models import Base, User, Subscription, Referral, Signal, Trade
from common.time import utcnow

DATA_DIR = pathlib.Path("data")

async def migrate():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as s:
        # users.json
        p = DATA_DIR / "users.json"
        if p.exists():
            users = json.loads(p.read_text())
            for u in users:
                tg = str(u.get("telegram_id") or u.get("id"))
                user = User(telegram_id=tg, username=u.get("username"))
                s.add(user)
        await s.commit()

        # subscriptions.json (optional)
        p = DATA_DIR / "subscriptions.json"
        if p.exists():
            subs = json.loads(p.read_text())
            for sub in subs:
                # naive example
                pass
        await s.commit()

if __name__ == "__main__":
    asyncio.run(migrate())
