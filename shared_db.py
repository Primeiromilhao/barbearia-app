import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "shared.db"

SERVICES = [
    ("Serviço básico", 30),
    ("Serviço completo", 60),
    ("Serviço premium", 90),
]
TIMES = ["09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00"]

def connect():
    db = sqlite3.connect(DB_PATH, timeout=2)
    db.execute("""CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE)""")
    db.execute("""CREATE TABLE IF NOT EXISTS services(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, duration INTEGER NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL, service_id INTEGER NOT NULL,
        date TEXT NOT NULL, time TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'confirmed',
        FOREIGN KEY(client_id) REFERENCES clients(id),
        FOREIGN KEY(service_id) REFERENCES services(id))""")
    db.execute("""CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER NOT NULL, channel TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        message TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(appointment_id, channel),
        FOREIGN KEY(appointment_id) REFERENCES appointments(id))""")
    db.execute("""UPDATE appointments SET service_id=(
        SELECT MIN(s2.id) FROM services s2 WHERE s2.name=(
            SELECT s1.name FROM services s1 WHERE s1.id=appointments.service_id
        )
    ) WHERE service_id IN (
        SELECT id FROM services WHERE id NOT IN (SELECT MIN(id) FROM services GROUP BY name)
    )""")
    db.execute("DELETE FROM services WHERE id NOT IN (SELECT MIN(id) FROM services GROUP BY name)")
    db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uq_active_slot
        ON appointments(date,time) WHERE status IN ('confirmed','pending')""")
    for name,duration in SERVICES:
        db.execute("INSERT OR IGNORE INTO services(name,duration) VALUES(?,?)",(name,duration))
    db.commit()
    return db

def normalize_phone(phone):
    return "".join(ch for ch in phone.strip() if ch.isdigit() or ch == "+").replace(" ","")

def register_client(name, phone):
    name, phone = name.strip(), normalize_phone(phone)
    if not name or not phone:
        return False, "Nome e telefone são obrigatórios.", None
    db=connect()
    try:
        row=db.execute("SELECT id,name,phone FROM clients WHERE phone=?",(phone,)).fetchone()
        if row:
            if row[1] != name:
                db.execute("UPDATE clients SET name=? WHERE phone=?",(name,phone)); db.commit()
                row=(row[0],name,phone)
            return True, "Cliente identificado.", row
        cur=db.execute("INSERT INTO clients(name,phone) VALUES(?,?)",(name,phone))
        db.commit()
        return True, "Cadastro realizado.", (cur.lastrowid,name,phone)
    finally:
        db.close()

def client_by_phone(phone):
    db=connect()
    row=db.execute("SELECT id,name,phone FROM clients WHERE phone=?",(normalize_phone(phone),)).fetchone()
    db.close()
    return row

def clients():
    db=connect()
    rows=db.execute("SELECT id,name,phone FROM clients ORDER BY name").fetchall()
    db.close(); return rows

def book(name, phone, service, date, time):
    ok,msg,row=register_client(name,phone)
    if not ok: return False,msg,None
    db=connect()
    try:
        service_row=db.execute("SELECT id FROM services WHERE name=?",(service,)).fetchone()
        if not service_row: return False,"Serviço inválido.",None
        try:
            cur=db.execute("INSERT INTO appointments(client_id,service_id,date,time,status) VALUES(?,?,?,?,?)",
                           (row[0],service_row[0],date,time,"confirmed"))
            appointment_id=cur.lastrowid
            msg_text=f"Barbearia: agendamento confirmado para {date} às {time}. Serviço: {service}."
            db.execute("INSERT OR IGNORE INTO notifications(appointment_id,channel,status,message) VALUES(?,?,?,?)",
                       (appointment_id,"whatsapp","pending",msg_text))
            db.execute("INSERT OR IGNORE INTO notifications(appointment_id,channel,status,message) VALUES(?,?,?,?)",
                       (appointment_id,"sms","pending",msg_text))
            db.commit()
            return True,"Agendamento confirmado.",appointment_id
        except sqlite3.IntegrityError:
            db.rollback(); return False,"Horário indisponível.",None
    finally:
        db.close()

def appointments(phone=None):
    db=connect()
    q="""SELECT a.id,c.name,c.phone,s.name,a.date,a.time,a.status
         FROM appointments a JOIN clients c ON c.id=a.client_id
         JOIN services s ON s.id=a.service_id"""
    args=()
    if phone:
        q += " WHERE c.phone=?"; args=(normalize_phone(phone),)
    q += " ORDER BY a.date,a.time"
    rows=db.execute(q,args).fetchall(); db.close(); return rows

def notifications(appointment_id=None):
    db=connect()
    q="SELECT id,appointment_id,channel,status,message,created_at FROM notifications"
    args=()
    if appointment_id: q+=" WHERE appointment_id=?"; args=(appointment_id,)
    q+=" ORDER BY id"
    rows=db.execute(q,args).fetchall(); db.close(); return rows

def cancel(appointment_id):
    db=connect(); db.execute("UPDATE appointments SET status='cancelled' WHERE id=? AND status IN ('confirmed','pending')",(appointment_id,)); db.commit(); db.close()

def complete(appointment_id):
    db=connect(); db.execute("UPDATE appointments SET status='completed' WHERE id=?",(appointment_id,)); db.commit(); db.close()
