
from fastapi import APIRouter
from common.time import utcnow

router = APIRouter()

@router.get("/healthz")
async def healthz():
    return {"status":"ok","ts":utcnow().isoformat()}
