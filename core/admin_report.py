
import os, json, datetime, time, requests
from croniter import croniter

USERS_FILE = os.getenv("USERS_FILE","data/users.json")
REFS_FILE = os.getenv("REFERRALS_FILE","data/referrals.json")
TRADES_FILE = os.getenv("TRADES_FILE","data/trades.json")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("TELEGRAM_TOKEN",""))
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()]
ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID","")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def load(path):
    if os.path.exists(path):
        with open(path,"r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def build_report():
    now = datetime.datetime.now()
    day_ago = now - datetime.timedelta(days=1)
    users = load(USERS_FILE)
    refs = load(REFS_FILE)
    trades = load(TRADES_FILE)

    # Users stats
    total = len([k for k in users if not k.startswith("_")])
    active = sum(1 for k,v in users.items() if isinstance(v,dict) and v.get("plan") in ("month","year"))
    new_users = [k for k,v in users.items() if isinstance(v,dict) and datetime.datetime.fromisoformat(v.get("start", now.isoformat())) >= day_ago]
    renewals = [k for k,v in users.items() if isinstance(v,dict) and v.get("expires") and datetime.datetime.fromisoformat(v["expires"]) >= day_ago]

    # Revenue rough (count of month/year activations in last 24h)
    # This is approximate; for precise sum scan TON tx history and persist events.
    revenue_ton = 5*sum(1 for k,v in users.items() if isinstance(v,dict) and v.get("plan")=="month" and datetime.datetime.fromisoformat(v.get("start", now.isoformat()))>=day_ago) \
                 +39*sum(1 for k,v in users.items() if isinstance(v,dict) and v.get("plan")=="year" and datetime.datetime.fromisoformat(v.get("start", now.isoformat()))>=day_ago)

    # Referrals
    new_paid_refs = 0
    waiting = 0
    for rid, data in refs.items():
        if rid.startswith("_"): continue
        for uid, r in data.get("referrals",{}).items():
            if r.get("status")=="paid" and r.get("paid_at"):
                if datetime.datetime.fromisoformat(r["paid_at"]) >= day_ago:
                    new_paid_refs += 1
            if r.get("status")=="paid" and not r.get("bonus_sent", False):
                waiting += 1

    # PnL
    pnl_points = trades.get("pnl_by_day",[])
    pnl_last = pnl_points[-1]["pnl"] if pnl_points else 0
    win_rate = trades.get("win_rate", 0)
    avg_rr = trades.get("avg_rr", 0)

    text = (
        "📊 *Ежедневный отчёт QuantumTrader*\n"
        f"Дата: {now.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"👥 Пользователи: {total} (активных {active})\n"
        f"🆕 Новые за 24ч: {len(new_users)}\n"
        f"🔁 Продления за 24ч: {len(renewals)}\n"
        f"💰 Доход (оценка): {revenue_ton} TON\n\n"
        f"🤝 Реферал-оплаты за 24ч: {new_paid_refs}\n"
        f"💎 Ожидает выплат: {waiting} шт.\n\n"
        f"📈 PnL вчера: {pnl_last}\n"
        f"🏆 Win-rate: {win_rate*100:.1f}%  •  Avg RR: {avg_rr:.2f}\n"
    )
    return text

def send_report(text: str):
    if not BOT_TOKEN: 
        print("No BOT TOKEN for admin report"); 
        return
    targets = list(ADMIN_IDS)
    if ADMIN_CHANNEL_ID:
        try:
            targets.append(int(ADMIN_CHANNEL_ID))
        except: pass
    for tid in targets:
        try:
            requests.post(TELEGRAM_API, json={"chat_id": tid, "text": text, "parse_mode":"Markdown"}, timeout=15)
        except Exception as e:
            print("Send report error:", e)

def run_cron_loop(cron_expr="0 9 * * *"):
    print("Admin daily report loop started with CRON:", cron_expr)
    base = datetime.datetime.now()
    itr = croniter(cron_expr, base)
    next_time = itr.get_next(datetime.datetime)
    while True:
        now = datetime.datetime.now()
        if now >= next_time:
            text = build_report()
            send_report(text)
            next_time = itr.get_next(datetime.datetime)
        time.sleep(30)

if __name__ == "__main__":
    cron = os.getenv("ADMIN_REPORT_CRON","0 9 * * *")  # default 09:00 daily
    run_cron_loop(cron)
