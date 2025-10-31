
from __future__ import annotations
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.config import settings
from api.health import router as health_router
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from passlib.hash import bcrypt
from typing import Optional
import pathlib

app = FastAPI(title="QuantumTrader Dashboard (Secure)")
app.include_router(health_router)

# CORS (tighten as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET","POST"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key=settings.DASHBOARD_SECRET_KEY)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

templates = Jinja2Templates(directory=str(pathlib.Path(__file__).parent / "templates"))

def verify_password_hash(pw_plain: str, pw_hash: str) -> bool:
    try:
        return bcrypt.verify(pw_plain, pw_hash)
    except Exception:
        return False

def require_auth(request: Request):
    if not request.session.get("auth_ok"):
        return RedirectResponse(url="/login", status_code=302)

@app.get("/", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def index(request: Request):
    if not request.session.get("auth_ok"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == settings.ADMIN_USERNAME and verify_password_hash(password, settings.ADMIN_PASSWORD_HASH):
        request.session["auth_ok"] = True
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверные данные"})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)
