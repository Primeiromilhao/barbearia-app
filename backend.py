from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import sqlite3, threading, time, os

BASE = Path(__file__).resolve().parent
WEB = BASE / "web"
DB = BASE / "shared_web.db"
LOCK = threading.Lock()

app = Flask(__name__, static_folder=str(WEB), static_url_path="")
CORS(app)
app.config["JSON_AS_ASCII"] = False

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with LOCK, db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS clients(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          phone TEXT NOT NULL UNIQUE,
          created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS services(
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          price REAL NOT NULL,
          duration INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS appointments(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          client_id INTEGER NOT NULL,
          service_id INTEGER NOT NULL,
          date TEXT NOT NULL,
          time TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN
            ('pending','confirmed','rejected','cancelled','completed')),
          created_at REAL NOT NULL,
          updated_at REAL NOT NULL,
          FOREIGN KEY(client_id) REFERENCES clients(id),
          FOREIGN KEY(service_id) REFERENCES services(id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_confirmed_slot
          ON appointments(date,time) WHERE status='confirmed';
        CREATE TABLE IF NOT EXISTS notifications(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          appointment_id INTEGER NOT NULL,
          channel TEXT NOT NULL CHECK(channel IN ('whatsapp','sms')),
          status TEXT NOT NULL DEFAULT 'pending',
          phone TEXT NOT NULL,
          message TEXT NOT NULL,
          created_at REAL NOT NULL,
          sent_at REAL,
          FOREIGN KEY(appointment_id) REFERENCES appointments(id)
        );
        """)
        services = [
          (1,"Corte de Cabelo",15,30),
          (2,"Barba",10,20),
          (3,"Corte + Barba",22,50)
        ]
        c.executemany("INSERT OR IGNORE INTO services VALUES(?,?,?,?)", services)

def rowdict(r):
    return dict(r) if r else None

def appointment_row(c, aid):
    return c.execute("""
      SELECT a.id,a.date,a.time,a.status,a.created_at,a.updated_at,
             cl.name client,cl.phone,
             s.name service,s.price,s.duration
      FROM appointments a
      JOIN clients cl ON cl.id=a.client_id
      JOIN services s ON s.id=a.service_id
      WHERE a.id=?
    """,(aid,)).fetchone()

def notification_message(appt, action):
    if action == "confirmed":
        return (f"Barbearia: seu agendamento foi CONFIRMADO. "
                f"{appt['service']} em {appt['date']} às {appt['time']}.")
    return (f"Barbearia: sua solicitação de {appt['service']} em "
            f"{appt['date']} às {appt['time']} foi RECUSADA.")

def queue_notifications(c, appt, action):
    msg = notification_message(appt, action)
    for channel in ("whatsapp","sms"):
        c.execute("""INSERT INTO notifications
          (appointment_id,channel,status,phone,message,created_at)
          VALUES(?,?,?,?,?,?)""",
          (appt["id"],channel,"pending",appt["phone"],msg,time.time()))

@app.get("/")
def index():
    return send_from_directory(WEB,"index.html")

@app.get("/proprietario.html")
def owner_page():
    return send_from_directory(WEB,"proprietario.html")

@app.get("/<path:path>")
def assets(path):
    return send_from_directory(WEB,path)

@app.get("/api/health")
def health():
    return jsonify({"status":"ok","database":str(DB),"mode":"local-shared-backend"})

@app.post("/api/client/register")
def register():
    data=request.get_json(force=True)
    name=str(data.get("name","")).strip()
    phone=str(data.get("phone","")).strip()
    if not name or not phone:
        return jsonify({"error":"Nome e telefone são obrigatórios"}),400
    with LOCK, db() as c:
        c.execute("""INSERT INTO clients(name,phone,created_at)
                     VALUES(?,?,?) ON CONFLICT(phone) DO UPDATE SET name=excluded.name""",
                  (name,phone,time.time()))
        r=c.execute("SELECT id,name,phone FROM clients WHERE phone=?",(phone,)).fetchone()
    return jsonify(rowdict(r))

@app.get("/api/services")
def services():
    with db() as c:
        return jsonify([rowdict(x) for x in c.execute("SELECT * FROM services ORDER BY id")])

@app.post("/api/appointments")
def create_appointment():
    data=request.get_json(force=True)
    phone=str(data.get("phone","")).strip()
    service_id=int(data.get("service_id",0))
    date=str(data.get("date","")).strip()
    tm=str(data.get("time","")).strip()
    if not all([phone,service_id,date,tm]):
        return jsonify({"error":"Dados incompletos"}),400
    with LOCK, db() as c:
        client=c.execute("SELECT * FROM clients WHERE phone=?",(phone,)).fetchone()
        if not client:
            return jsonify({"error":"Cliente não cadastrado"}),404
        if not c.execute("SELECT 1 FROM services WHERE id=?",(service_id,)).fetchone():
            return jsonify({"error":"Serviço inválido"}),400
        # Requests may coexist as pending. Only confirmed appointments block the slot.
        cur=cur=c.execute("""INSERT INTO appointments
          (client_id,service_id,date,time,status,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?)""",
          (client["id"],service_id,date,tm,"pending",time.time(),time.time()))
        aid=cur.lastrowid
        appt=appointment_row(c,aid)
    return jsonify(rowdict(appt)),201

@app.get("/api/appointments")
def client_appointments():
    phone=request.args.get("phone","").strip()
    with db() as c:
        rows=c.execute("""
          SELECT a.id,a.date,a.time,a.status,a.created_at,a.updated_at,
                 cl.name client,cl.phone,s.id service_id,s.name service,
                 s.price,s.duration
          FROM appointments a JOIN clients cl ON cl.id=a.client_id
          JOIN services s ON s.id=a.service_id
          WHERE cl.phone=? ORDER BY a.date DESC,a.time DESC,a.id DESC
        """,(phone,)).fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.post("/api/appointments/<int:aid>/cancel")
def cancel_appointment(aid):
    with LOCK, db() as c:
        r=c.execute("SELECT status FROM appointments WHERE id=?",(aid,)).fetchone()
        if not r: return jsonify({"error":"Agendamento não encontrado"}),404
        if r["status"] not in ("pending","confirmed"):
            return jsonify({"error":"Agendamento não pode ser cancelado"}),409
        c.execute("UPDATE appointments SET status='cancelled',updated_at=? WHERE id=?",
                  (time.time(),aid))
        appt=appointment_row(c,aid)
    return jsonify(rowdict(appt))

@app.get("/api/owner/appointments")
def owner_appointments():
    status=request.args.get("status")
    q="""SELECT a.id,a.date,a.time,a.status,a.created_at,a.updated_at,
                cl.name client,cl.phone,s.name service,s.price,s.duration
         FROM appointments a JOIN clients cl ON cl.id=a.client_id
         JOIN services s ON s.id=a.service_id"""
    params=[]
    if status:
        q+=" WHERE a.status=?"; params.append(status)
    q+=" ORDER BY CASE a.status WHEN 'pending' THEN 0 WHEN 'confirmed' THEN 1 ELSE 2 END, a.date,a.time,a.id"
    with db() as c:
        rows=c.execute(q,params).fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.get("/api/owner/clients")
def owner_clients():
    with db() as c:
        rows=c.execute("""SELECT cl.id,cl.name,cl.phone,cl.created_at,
                          COUNT(a.id) appointments
                          FROM clients cl LEFT JOIN appointments a
                          ON a.client_id=cl.id
                          GROUP BY cl.id ORDER BY cl.name""").fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.post("/api/owner/appointments/<int:aid>/confirm")
def confirm_appointment(aid):
    with LOCK, db() as c:
        appt=appointment_row(c,aid)
        if not appt: return jsonify({"error":"Agendamento não encontrado"}),404
        if appt["status"] != "pending":
            return jsonify({"error":"Somente pendentes podem ser confirmados"}),409
        # Transactionally enforce one confirmed appointment per slot.
        occupied=c.execute("""SELECT id FROM appointments
                              WHERE date=? AND time=? AND status='confirmed'
                              AND id<>?""",
                           (appt["date"],appt["time"],aid)).fetchone()
        if occupied:
            return jsonify({"error":"Horário já confirmado para outro cliente"}),409
        c.execute("UPDATE appointments SET status='confirmed',updated_at=? WHERE id=?",
                  (time.time(),aid))
        appt=appointment_row(c,aid)
        queue_notifications(c,appt,"confirmed")
    return jsonify({"appointment":rowdict(appt),
                    "notifications":["whatsapp","sms"],
                    "notification_status":"pending"})

@app.post("/api/owner/appointments/<int:aid>/reject")
def reject_appointment(aid):
    with LOCK, db() as c:
        appt=appointment_row(c,aid)
        if not appt: return jsonify({"error":"Agendamento não encontrado"}),404
        if appt["status"] != "pending":
            return jsonify({"error":"Somente pendentes podem ser recusados"}),409
        c.execute("UPDATE appointments SET status='rejected',updated_at=? WHERE id=?",
                  (time.time(),aid))
        appt=appointment_row(c,aid)
        queue_notifications(c,appt,"rejected")
    return jsonify({"appointment":rowdict(appt),
                    "notifications":["whatsapp","sms"],
                    "notification_status":"pending"})

@app.get("/api/notifications")
def notifications():
    with db() as c:
        rows=c.execute("SELECT * FROM notifications ORDER BY id DESC").fetchall()
    return jsonify([rowdict(x) for x in rows])

if __name__ == "__main__":
    init_db()
    print(f"BARBEARIA_BACKEND http://127.0.0.1:8787 DB={DB}")
    app.run(host="127.0.0.1",port=8787,debug=False)
