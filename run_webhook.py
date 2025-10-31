import os, asyncio
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from telegram_app.bot import dp, bot

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH","/webhook")
PORT = int(os.getenv("PORT","8080"))

async def on_startup(app):
    if not WEBHOOK_URL:
        print("❌ WEBHOOK_URL is not set")
        return
    await bot.set_webhook(WEBHOOK_URL.rstrip('/') + WEBHOOK_PATH)

async def app_factory():
    app = web.Application()
    SimpleRequestHandler(dp, bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    app.on_startup.append(on_startup)
    return app

if __name__ == "__main__":
    web.run_app(asyncio.run(app_factory()), port=PORT)
