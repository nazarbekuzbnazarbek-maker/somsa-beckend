from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Any
import sqlite3
import json

app = FastAPI(title="Somsa Xona POS API", version="3.1")

# CORS xavfsizligini ochish (HTML bilan ulanishi uchun)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "somsa_xona.db"

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        phone TEXT PRIMARY KEY,
        pass_hash TEXT,
        role TEXT,
        name TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS somsa_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER
    )''')
    
    cursor.execute("SELECT COUNT(*) FROM somsa_types")
    if cursor.fetchone()[0] == 0:
        defaults = [
            ("Mol go'shtli", 10000),
            ("Qo'y go'shtli", 12000),
            ("Avashnoy", 6000),
            ("Qiyma", 8000),
            ("Kartoshkali", 5000),
            ("Qovoqli", 5000),
            ("Tovuqli", 8000)
        ]
        cursor.executemany("INSERT INTO somsa_types (name, price) VALUES (?, ?)", defaults)

    cursor.execute('''CREATE TABLE IF NOT EXISTS production_logs (
        id INTEGER PRIMARY KEY,
        date TEXT,
        time TEXT,
        worker TEXT,
        status TEXT,
        somsa_id INTEGER,
        somsa_name TEXT,
        qty INTEGER,
        price INTEGER,
        worker_fee INTEGER
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS sales_logs (
        id INTEGER PRIMARY KEY,
        date TEXT,
        time TEXT,
        seller TEXT,
        customer TEXT,
        payment_type TEXT,
        total INTEGER,
        items TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_requests (
        id INTEGER PRIMARY KEY,
        type TEXT,
        action TEXT,
        target_id INTEGER,
        phone TEXT,
        new_pass_hash TEXT,
        new_qty INTEGER,
        new_items TEXT,
        requested_by TEXT,
        reason TEXT,
        status TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

class UserIn(BaseModel):
    phone: str
    pass_hash: str
    role: str
    name: str

class ProductionIn(BaseModel):
    id: int
    date: str
    time: str
    worker: str
    status: str
    somsa_id: int
    somsa_name: str
    qty: int
    price: int
    worker_fee: int

class SaleIn(BaseModel):
    id: int
    date: str
    time: str
    seller: str
    customer: str
    payment_type: str
    total: int
    items: List[Any]

class AuditIn(BaseModel):
    id: int
    type: str
    action: str
    target_id: Optional[int] = None
    phone: Optional[str] = None
    new_pass_hash: Optional[str] = None
    new_qty: Optional[int] = None
    new_items: Optional[List[Any]] = None
    requested_by: str
    reason: str
    status: str

class SettingIn(BaseModel):
    key: str
    value: str

@app.get("/api/init-data")
def get_all_data():
    conn = get_db()
    cursor = conn.cursor()
    
    users = [dict(row) for row in cursor.execute("SELECT * FROM users").fetchall()]
    somsa_types = [dict(row) for row in cursor.execute("SELECT * FROM somsa_types").fetchall()]
    production_logs = [dict(row) for row in cursor.execute("SELECT * FROM production_logs ORDER BY id DESC").fetchall()]
    
    sales_raw = cursor.execute("SELECT * FROM sales_logs ORDER BY id DESC").fetchall()
    sales_logs = []
    for r in sales_raw:
        item = dict(r)
        item["items"] = json.loads(item["items"])
        sales_logs.append(item)
        
    audit_raw = cursor.execute("SELECT * FROM audit_requests ORDER BY id DESC").fetchall()
    audit_requests = []
    for r in audit_raw:
        item = dict(r)
        if item["new_items"]:
            item["new_items"] = json.loads(item["new_items"])
        audit_requests.append(item)
        
    card_res = cursor.execute("SELECT value FROM settings WHERE key='card_number'").fetchone()
    card_number = card_res["value"] if card_res else ""
    
    conn.close()
    return {
        "users": users,
        "somsaTypes": somsa_types,
        "productionLogs": production_logs,
        "salesLogs": sales_logs,
        "auditRequests": audit_requests,
        "cardNumber": card_number
    }

@app.post("/api/users")
def save_user(user: UserIn):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (phone, pass_hash, role, name) VALUES (?, ?, ?, ?)",
                   (user.phone, user.pass_hash, user.role, user.name))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/users/{phone}")
def delete_user(phone: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/production")
def add_production(prod: ProductionIn):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO production_logs 
        (id, date, time, worker, status, somsa_id, somsa_name, qty, price, worker_fee) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (prod.id, prod.date, prod.time, prod.worker, prod.status, prod.somsa_id, prod.somsa_name, prod.qty, prod.price, prod.worker_fee))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/sales")
def add_sale(sale: SaleIn):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO sales_logs 
        (id, date, time, seller, customer, payment_type, total, items) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (sale.id, sale.date, sale.time, sale.seller, sale.customer, sale.payment_type, sale.total, json.dumps(sale.items)))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/audit")
def add_audit(audit: AuditIn):
    conn = get_db()
    cursor = conn.cursor()
    items_json = json.dumps(audit.new_items) if audit.new_items else None
    cursor.execute("""INSERT INTO audit_requests 
        (id, type, action, target_id, phone, new_pass_hash, new_qty, new_items, requested_by, reason, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (audit.id, audit.type, audit.action, audit.target_id, audit.phone, audit.new_pass_hash, audit.new_qty, items_json, audit.requested_by, audit.reason, audit.status))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.put("/api/audit/{audit_id}")
def update_audit_status(audit_id: int, status_data: dict):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE audit_requests SET status = ? WHERE id = ?", (status_data.get("status"), audit_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/settings/card")
def save_card(setting: SettingIn):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('card_number', ?)", (setting.value,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/somsa-types/update")
def update_prices(prices: List[dict]):
    conn = get_db()
    cursor = conn.cursor()
    for p in prices:
        cursor.execute("UPDATE somsa_types SET price = ? WHERE id = ?", (p["price"], p["id"]))
    conn.commit()
    conn.close()
    return {"status": "success"}
