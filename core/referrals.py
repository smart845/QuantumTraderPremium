
import os, json, datetime

USERS_FILE = os.getenv("USERS_FILE","data/users.json")
REF_FILE = os.getenv("REFERRALS_FILE","data/referrals.json")

def _load_json(path):
    if os.path.exists(path):
        with open(path,"r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: json.dump(data,f,indent=2,ensure_ascii=False)

def load_users(): return _load_json(USERS_FILE)
def save_users(d): _save_json(USERS_FILE, d)
def load_refs(): return _load_json(REF_FILE)
def save_refs(d): _save_json(REF_FILE, d)

def set_user_referrer(user_id: int, referrer_id: int, username: str = ""):
    """Mark that user_id was referred by referrer_id; status pending until paid."""
    refs = load_refs()
    referrer_key = str(referrer_id)
    user_key = str(user_id)
    refs.setdefault(referrer_key, {"earned": 0.0, "address":"", "referrals": {}})
    if user_key not in refs[referrer_key]["referrals"]:
        refs[referrer_key]["referrals"][user_key] = {
            "status": "pending",
            "registered": datetime.datetime.now().isoformat(),
            "username": username or "",
            "paid_at": None,
            "bonus_sent": False
        }
        save_refs(refs)

def set_referrer_address(referrer_id: int, ton_address: str):
    refs = load_refs()
    refs.setdefault(str(referrer_id), {"earned":0.0, "address":"", "referrals":{}})
    refs[str(referrer_id)]["address"] = ton_address
    save_refs(refs)

def mark_referral_paid(referrer_id: int, user_id: int, bonus_ton: float = 1.0):
    refs = load_refs()
    ref = refs.setdefault(str(referrer_id), {"earned":0.0, "address":"", "referrals":{}})
    u = ref["referrals"].setdefault(str(user_id), {})
    u["status"] = "paid"
    u["paid_at"] = datetime.datetime.now().isoformat()
    # Keep bonus_sent False until admin marks paid
    ref["earned"] = round(ref.get("earned",0.0) + bonus_ton, 3)
    save_refs(refs)

def mark_bonus_sent(referrer_id: int, user_id: int):
    refs = load_refs()
    r = refs.get(str(referrer_id),{}).get("referrals",{}).get(str(user_id))
    if r:
        r["bonus_sent"] = True
        save_refs(refs)

def expire_old_pending(days=7):
    refs = load_refs()
    now = datetime.datetime.now()
    changed = False
    for rid, data in refs.items():
        for uid, info in data.get("referrals",{}).items():
            if info.get("status") == "pending":
                try:
                    dt = datetime.datetime.fromisoformat(info.get("registered"))
                    if (now - dt).days > days:
                        info["status"] = "expired"
                        changed = True
                except: pass
    if changed: save_refs(refs)

def build_share_text(bot_username: str, referrer_id: int):
    return (f"📣 Приглашаю в Quantum AI Trader!\n"
            f"Реферальный бонус: 1 TON за годовую подписку друга 💎\n"
            f"Заходи по ссылке: https://t.me/{bot_username}?start=ref{referrer_id}")

def stats_summary():
    refs = load_refs()
    lines = ["👑 Реферальная статистика",""]
    total_earned = 0.0
    waiting = 0.0
    for rid, data in refs.items():
        addr = data.get("address","—")
        paid = sum(1 for r in data.get("referrals",{}).values() if r.get("status")=="paid" and not r.get("bonus_sent"))
        pend = sum(1 for r in data.get("referrals",{}).values() if r.get("status")=="pending")
        earned = data.get("earned",0.0)
        total_earned += earned
        waiting += paid * 1.0
        lines.append(f"@{rid} — оплачено (ожидает выплаты): {paid}, ждут оплаты: {pend}, TON-адрес: {addr}")
    lines.append("")
    lines.append(f"Всего начислено: {total_earned:.2f} TON")
    lines.append(f"Ожидает выплат: {waiting:.2f} TON")
    return "\n".join(lines)
