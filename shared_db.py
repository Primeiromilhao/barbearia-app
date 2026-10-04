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
    db = sqlite3.connect(DB_PATH, timeout=1)
    db.execute("""CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL UNIQUE)""")
    db.execute("""CREATE TABLE IF NOT EXISTS services(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, duration INTEGER NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL, service_id INTEGER NOT NULL,
        date TEXT NOT NULL, time TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'confirmed',
        FOREIGN KEY(client_id) REFERENCES clients(id),
        FOREIGN KEY(service_id) REFERENCES services(id))""")
    db.execute("""UPDATE appointments SET service_id=(
        SELECT MIN(s2.id) FROM services s2 WHERE s2.name=(SELECT s1.name FROM services s1 WHERE s1.id=appointments.service_id)
    ) WHERE service_id IN (SELECT id FROM services WHERE id NOT IN (SELECT MIN(id) FROM services GROUP BY name))""")
    db.execute("DELETE FROM services WHERE id NOT IN (SELECT MIN(id) FROM services GROUP BY name)")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_service_name ON services(name)")
    db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS uq_active_slot
        ON appointments(date,time) WHERE status IN ('confirmed','pending')""")
    for name,duration in SERVICES:
        db.execute("INSERT OR IGNORE INTO services(name,duration) VALUES(?,?)",(name,duration))
    db.commit()
    return db

def book(name, phone, service, date, time):
    db=connect()
    try:
        cur=db.execute("INSERT OR IGNORE INTO clients(name,phone) VALUES(?,?)",(name.strip(),phone.strip()))
        row=db.execute("SELECT id FROM clients WHERE phone=?",(phone.strip(),)).fetchone()
        service_row=db.execute("SELECT id FROM services WHERE name=?",(service,)).fetchone()
        if not row or not service_row: return False, "Dados inválidos."
        try:
            db.execute("INSERT INTO appointments(client_id,service_id,date,time,status) VALUES(?,?,?,?,?)",
                       (row[0],service_row[0],date,time,"confirmed"))
            db.commit(); return True, "Agendamento confirmado."
        except sqlite3.IntegrityError:
            db.rollback(); return False, "Horário indisponível."
    finally: db.close()

def appointments(phone=None):
    db=connect()
    q="""SELECT a.id,c.name,c.phone,s.name,a.date,a.time,a.status
         FROM appointments a JOIN clients c ON c.id=a.client_id
         JOIN services s ON s.id=a.service_id"""
    args=()
    if phone: q += " WHERE c.phone=?"; args=(phone,)
    q += " ORDER BY a.date,a.time"
    rows=db.execute(q,args).fetchall(); db.close(); return rows

def cancel(appointment_id):
    db=connect(); db.execute("UPDATE appointments SET status='cancelled' WHERE id=?",(appointment_id,)); db.commit(); db.close()

def complete(appointment_id):
    db=connect(); db.execute("UPDATE appointments SET status='completed' WHERE id=?",(appointment_id,)); db.commit(); db.close()
