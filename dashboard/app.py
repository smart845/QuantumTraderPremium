import os, json, datetime, csv, io
from fastapi import FastAPI, Depends, Request, Response, HTTPException, status, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse

from fastapi import UploadFile, File
from fastapi.staticfiles import StaticFiles

DATA_TRADES = os.getenv("TRADES_FILE","data/trades.json")
DATA_SIGNALS = os.getenv("SIGNALS_FILE","data/signals.json")
ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID","")

app.mount("/static", StaticFiles(directory="static"), name="static")

def read_json_safe(path: str):
    if os.path.exists(path):
        with open(path,"r") as f:
            try: return json.load(f)
            except: return {}
    return {}

@app.get("/signals", response_class=HTMLResponse)
def signals_page(request: Request, authorized: bool = Depends(auth)):
    trades = read_json_safe(DATA_TRADES)
    signals = read_json_safe(DATA_SIGNALS).get("last_signals", [])
    return templates.TemplateResponse("signals.html", {"request": request, "signals": signals, "trades": trades})

@app.get("/api/metrics")
def api_metrics(authorized: bool = Depends(auth)):
    trades = read_json_safe(DATA_TRADES)
    return trades

@app.post("/backup/import")
def import_backup(file: UploadFile = File(...), authorized: bool = Depends(auth)):
    content = json.loads(file.file.read().decode("utf-8"))
    # Accept keys users/referrals/trades/signals
    if "users" in content:
        with open(DATA_USERS,"w") as f: json.dump(content["users"], f, indent=2, ensure_ascii=False)
    if "refs" in content:
        with open(DATA_REFS,"w") as f: json.dump(content["refs"], f, indent=2, ensure_ascii=False)
    if "trades" in content:
        with open(DATA_TRADES,"w") as f: json.dump(content["trades"], f, indent=2, ensure_ascii=False)
    if "signals" in content:
        with open(DATA_SIGNALS,"w") as f: json.dump(content["signals"], f, indent=2, ensure_ascii=False)
    return RedirectResponse(url="/", status_code=302)

@app.get("/backup/export.json")
def export_backup(authorized: bool = Depends(auth)):
    blob = {
        "users": read_json(DATA_USERS),
        "refs": read_json(DATA_REFS),
        "trades": read_json_safe(DATA_TRADES),
        "signals": read_json_safe(DATA_SIGNALS)
    }
    data = json.dumps(blob, ensure_ascii=False, indent=2)
    return StreamingResponse(iter([data]), media_type="application/json")

from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Dict, Any

TEMPLATES_DIR = os.getenv("TEMPLATES_DIR","templates")
DATA_USERS = os.getenv("USERS_FILE","data/users.json")
DATA_REFS  = os.getenv("REFERRALS_FILE","data/referrals.json")
ADMIN_USER = os.getenv("ADMIN_USER","admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD","changeme")

app = FastAPI(title="QuantumTrader Admin Dashboard")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
security = HTTPBasic()

def read_json(path: str) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path,"r") as f:
            try: return json.load(f)
            except: return {}
    return {}

def write_json(path: str, data: Dict[str, Any]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: json.dump(data,f,indent=2,ensure_ascii=False)

def auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct = (credentials.username == ADMIN_USER and credentials.password == ADMIN_PASS)
    if not correct:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized",
                            headers={"WWW-Authenticate":"Basic"})
    return True

@app.get("/", response_class=HTMLResponse)
def index(request: Request, authorized: bool = Depends(auth)):
    users = read_json(DATA_USERS)
    refs  = read_json(DATA_REFS)
    # stats
    total = len([k for k in users if not k.startswith("_")])
    active = sum(1 for k,v in users.items() if isinstance(v,dict) and v.get("plan") in ("month","year"))
    trial  = sum(1 for k,v in users.items() if isinstance(v,dict) and v.get("plan")=="trial")
    blocked= sum(1 for k,v in users.items() if isinstance(v,dict) and v.get("plan")=="blocked")
    # referral stats
    total_earned = 0.0
    waiting_payouts = 0
    for rid, data in refs.items():
        if rid.startswith("_"): continue
        total_earned += float(data.get("earned",0.0))
        waiting_payouts += sum(1 for r in data.get("referrals",{}).values() if r.get("status")=="paid" and not r.get("bonus_sent"))
    return templates.TemplateResponse("index.html", {
        "request": request,
        "total": total, "active": active, "trial": trial, "blocked": blocked,
        "total_earned": total_earned, "waiting_payouts": waiting_payouts
    })

@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request, authorized: bool = Depends(auth)):
    users = read_json(DATA_USERS)
    q = request.query_params.get('q','').lower()
    plan_filter = request.query_params.get('plan','').lower()
    items = []
    for uid, info in users.items():
        if uid.startswith("_"): continue
        if not isinstance(info, dict): continue
        rec = {
            "uid": uid,
            "plan": info.get("plan"),
            "start": info.get("start"),
            "expires": info.get("expires",""),
            "referrer_id": info.get("referrer_id",""),
            "username": info.get("username","")
        }
        if q and not (q in uid.lower() or q in str(rec.get('username','')).lower()):
            continue
        if plan_filter and plan_filter != str(rec.get('plan','')).lower():
            continue
        items.append(rec)
    items.sort(key=lambda x: x["uid"])
    return templates.TemplateResponse("users.html", {"request": request, "users": items})

@app.get("/referrals", response_class=HTMLResponse)
def referrals_page(request: Request, authorized: bool = Depends(auth)):
    refs = read_json(DATA_REFS)
    s_rid = request.query_params.get('rid','')
    s_uid = request.query_params.get('uid','')
    s_status = request.query_params.get('status','')
    rows = []
    for rid, data in refs.items():
        if rid.startswith("_"): continue
        address = data.get("address","")
        for uid, r in data.get("referrals",{}).items():
            rec = {
                "referrer_id": rid,
                "referred_id": uid,
                "status": r.get("status"),
                "registered": r.get("registered"),
                "paid_at": r.get("paid_at",""),
                "bonus_sent": r.get("bonus_sent", False),
                "address": address,
                "username": r.get("username","")
            }
        if q and not (q in uid.lower() or q in str(rec.get('username','')).lower()):
            continue
        if plan_filter and plan_filter != str(rec.get('plan','')).lower():
            continue
        items.append(rec)
    rows.sort(key=lambda x: (x["status"], x["referrer_id"], x["referred_id"]))
    return templates.TemplateResponse("referrals.html", {"request": request, "rows": rows})

@app.get("/export/users.csv")
def export_users(authorized: bool = Depends(auth)):
    users = read_json(DATA_USERS)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["uid","plan","start","expires","referrer_id","username"])
    for uid, info in users.items():
        if uid.startswith("_"): continue
        if not isinstance(info, dict): continue
        writer.writerow([uid, info.get("plan"), info.get("start"), info.get("expires",""), info.get("referrer_id",""), info.get("username","")])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv")

@app.get("/export/referrals.csv")
def export_refs(authorized: bool = Depends(auth)):
    refs = read_json(DATA_REFS)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["referrer_id","referred_id","status","registered","paid_at","bonus_sent","address","username"])
    for rid, data in refs.items():
        if rid.startswith("_"): continue
        address = data.get("address","")
        for uid, r in data.get("referrals",{}).items():
            writer.writerow([rid, uid, r.get("status"), r.get("registered"), r.get("paid_at",""), r.get("bonus_sent",False), address, r.get("username","")])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv")

@app.post("/mark-paid")
def mark_paid(referrer_id: str = Form(...), referred_id: str = Form(...), authorized: bool = Depends(auth)):
    refs = read_json(DATA_REFS)
    r = refs.get(referrer_id,{}).get("referrals",{}).get(referred_id)
    if not r:
        raise HTTPException(404, "Referral not found")
    r["bonus_sent"] = True
    write_json(DATA_REFS, refs)
    return RedirectResponse(url="/referrals", status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("DASHBOARD_PORT","8090")), reload=False)


DATA_AI_INSIGHT = os.getenv("AI_INSIGHT_FILE","data/ai_insight.json")

@app.get("/ai/insight", response_class=HTMLResponse)
def ai_insight_page(request: Request, authorized: bool = Depends(auth)):
    data = read_json_safe(DATA_AI_INSIGHT)
    return templates.TemplateResponse("ai_insight.html", {"request": request, "data": data})
