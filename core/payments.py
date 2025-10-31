
from __future__ import annotations
from core.retry import network_retry
from db.base import SessionLocal
from db.models import Payment
from sqlalchemy import select
import asyncio

class TonClient:
    def __init__(self, api_base: str = "https://toncenter.com/api/v3"):
        self.api_base = api_base

    @network_retry()
    async def fetch_tx(self, tx_hash: str) -> dict:
        # Placeholder: fetch from TON API (disabled offline). In production use aiohttp here.
        # This method is wrapped in retries via tenacity.
        raise RuntimeError("Network disabled in this environment")

async def record_payment(tx_hash: str, from_address: str, amount_ton: float, comment_uid: str | None, confirmed: bool):
    async with SessionLocal() as s:
        q = await s.execute(select(Payment).where(Payment.tx_hash == tx_hash))
        row = q.scalar_one_or_none()
        if row:
            # idempotent update
            row.confirmed = row.confirmed or confirmed
        else:
            row = Payment(tx_hash=tx_hash, from_address=from_address, amount_ton=amount_ton, comment_uid=comment_uid, confirmed=confirmed)
            s.add(row)
        await s.commit()
