
import os, time, json, datetime, requests, re

import re
from core.referrals import load_users, save_users, load_refs, save_refs, mark_referral_paid

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_TOKEN",""))

ADMIN_IDS = set(int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit())

def notify_admins(text: str):
    if not BOT_TOKEN or not ADMIN_IDS:
        return
    for admin_id in ADMIN_IDS:
        try:
            requests.post(f"{TELEGRAM_API}/sendMessage", json={
                "chat_id": admin_id,
                "text": text,
                "parse_mode": "Markdown"
            }, timeout=10)
        except Exception as e:
            print("Admin notify error:", e)

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


USERS_FILE = os.getenv("USERS_FILE","data/users.json")
TON_ADDRESS = os.getenv("TON_ADDRESS","UQC3Pro8kBw5LGpD3uxTwrHn6rKP-MMw8sNgFt5IhhDdYZMG")
TONCENTER_API = os.getenv("TONCENTER_API","https://toncenter.com/api/v2/getTransactions")
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY","")  # optional
INTERVAL_SEC = int(os.getenv("SUBSCRIPTION_CHECK_INTERVAL","600"))  # 10 min default

UID_RE = re.compile(r"UID[:\s]+(\d+)", re.IGNORECASE)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE,"r") as f: 
            try: return json.load(f)
            except: return {}
    return {}

def save_users(d):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE,"w") as f: json.dump(d,f,indent=2,ensure_ascii=False)

def is_active(plan_info: dict) -> bool:
    """Check if subscription entry is active now."""
    if not plan_info: return False
    plan = plan_info.get("plan","trial")
    if plan == "trial":
        # handled in bot
        return True
    if plan in ("month","year"):
        exp = plan_info.get("expires")
        if not exp: return False
        try:
            return datetime.datetime.fromisoformat(exp) > datetime.datetime.now()
        except:
            return False
    return False


def notify_referrer(referrer_id: str, referred_user_id: str, referred_username: str = ""):
    """Send Telegram message to referrer about 1 TON bonus accrued; ask for TON address if not set."""
    if not BOT_TOKEN: 
        return
    refs = load_refs()
    addr = refs.get(referrer_id,{}).get("address","")
    text = (f"💎 По вашей ссылке пользователь {referred_username or referred_user_id} оформил годовую подписку!\n"
            f"Вам начислен бонус *1 TON*.\n"
            f"{'Ваш TON-адрес уже сохранён.' if addr else 'Пожалуйста укажите адрес TON командой /set_ton_address <адрес>'}")
    try:
        requests.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": int(referrer_id),
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        print("Telegram notify error:", e)


def grant_plan(uid: str, plan: str = "month", days: int = 30):
    users = load_users()
    now = datetime.datetime.now()
    exp = now + datetime.timedelta(days=days)
    users.setdefault(uid, {"start": now.isoformat()})
    users[uid]["plan"] = plan
    users[uid]["start"] = now.isoformat()
    users[uid]["expires"] = exp.isoformat()
    save_users(users)
    print(f"✅ Granted {plan} to {uid} until {exp.isoformat()}")

def parse_uid_from_comment(comment: str):
    if not comment: return None
    m = UID_RE.search(comment)
    if m: return m.group(1)
    return None

def check_transactions():
    params = {"address": TON_ADDRESS, "limit": 50}
    headers = {}
    if TONCENTER_API_KEY:
        headers["X-API-Key"] = TONCENTER_API_KEY
    try:
        r = requests.get(TONCENTER_API, params=params, headers=headers, timeout=20)
        j = r.json()
        txs = j.get("result", [])
    except Exception as e:
        print("❌ TON API error:", e)
        return

    users = load_users()
    seen = set()
    # Keep simple dedupe by storing tx hash in users.json history
    history = set(users.get("_tx_seen", []))

    updated = False
    for tx in txs:
        tx_hash = tx.get("transaction_id", {}).get("hash")
        if tx_hash and tx_hash in history: 
            continue
        in_msg = tx.get("in_msg", {})
        # value in nanotons:
        val = float(in_msg.get("value", 0))/1e9
        comment = in_msg.get("message","") or in_msg.get("msg_data_text","")
        uid = parse_uid_from_comment(comment)
        if not uid:
            continue
        # Determine plan by amount

        if val >= 38.5:
            plan, days = "year", 365
        elif val >= 4.9:
            plan, days = "month", 30
        else:
            continue  # too small payment

            plan, days = "year", 365
        elif val >= 4.9:
            plan, days = "month", 30
        else:
            continue  # too small payment

        grant_plan(uid, plan=plan, days=days)

        # Handle referral bonus if yearly
        if plan == "year":
            users_all = load_users()
            user_info = users_all.get(uid, {})
            referrer_id = user_info.get("referrer_id")
            if referrer_id:
                # Mark referral as paid and notify referrer
                mark_referral_paid(int(referrer_id), int(uid), bonus_ton=1.0)
                notify_referrer(str(referrer_id), uid, user_info.get("username",""))

        if tx_hash:
            history.add(tx_hash)
            updated = True

    if updated:
        users = load_users()
        users["_tx_seen"] = list(history)
        save_users(users)


def notify_expired_pendings():
    # Soft notify: count of expired pending referrals (handled in referrals.py expire), here we just log placeholder
    pass


def run_loop():
    print("🔁 TON subscription checker started")
    print("Address:", TON_ADDRESS)
    while True:
        check_transactions()
        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    run_loop()
