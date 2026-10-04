from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from pathlib import Path
import sqlite3, threading, time, os, secrets, json, base64, hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

BASE = Path(__file__).resolve().parent
WEB = BASE / "web"
DB = Path(os.environ.get("BARBEARIA_DB_PATH", str(BASE / "shared_web.db"))).expanduser()
DEV_SECRET_FILE = BASE / ".dev_secret"
LOCK = threading.Lock()
RATE_LOCK = threading.Lock()
RATE_BUCKETS = {}
RATE_WINDOW = 60
RATE_LIMIT_GENERAL = 120
RATE_LIMIT_AUTH = 12
MAX_BODY_BYTES = 64 * 1024

def client_key():
    return request.remote_addr or "unknown"

def rate_limit(limit, bucket):
    now = time.time()
    key = (client_key(), bucket)
    with RATE_LOCK:
        start, count = RATE_BUCKETS.get(key, (now, 0))
        if now - start >= RATE_WINDOW:
            start, count = now, 0
        count += 1
        RATE_BUCKETS[key] = (start, count)
        if count > limit:
            retry = max(1, int(RATE_WINDOW - (now - start)))
            return jsonify({"error":"Muitas tentativas. Tente novamente mais tarde.","retry_after":retry}), 429, {"Retry-After":str(retry)}
    return None


app = Flask(__name__, static_folder=str(WEB), static_url_path="")
app.config["JSON_AS_ASCII"] = False
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 8

ALLOWED_ORIGINS = [x.strip() for x in os.environ.get("BARBEARIA_ALLOWED_ORIGINS", "https://primeiromilhao.github.io").split(",") if x.strip()]
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True, allow_headers=["Content-Type","X-CSRF-Token"], methods=["GET","POST","OPTIONS"])
app.secret_key = os.environ.get("BARBEARIA_SESSION_SECRET") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

@app.before_request
def security_request_guard():
    if request.path.startswith("/api/"):
        limit = RATE_LIMIT_AUTH if request.path in {
            "/api/dev/login", "/api/owner/device/register",
            "/api/owner/challenge", "/api/owner/login", "/api/client/register"
        } else RATE_LIMIT_GENERAL
        limited = rate_limit(limit, request.path)
        if limited:
            return limited

@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

def get_owner_secret():
    return os.environ.get("BARBEARIA_OWNER_PASSWORD", "").strip()

def get_dev_secret():
    value = os.environ.get("BARBEARIA_DEV_PASSWORD")
    if value:
        return value
    if DEV_SECRET_FILE.exists():
        return DEV_SECRET_FILE.read_text(encoding="utf-8").strip()
    value = secrets.token_urlsafe(24)
    DEV_SECRET_FILE.write_text(value, encoding="utf-8")
    try: os.chmod(DEV_SECRET_FILE, 0o600)
    except OSError: pass
    print("DEV_PASSWORD_GENERATED=" + value)
    return value

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with LOCK, db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS clients(
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          phone TEXT NOT NULL UNIQUE, created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS services(
          id INTEGER PRIMARY KEY, name TEXT NOT NULL, price REAL NOT NULL, duration INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS appointments(
          id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL,
          service_id INTEGER NOT NULL, date TEXT NOT NULL, time TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('pending','confirmed','rejected','cancelled','completed')),
          created_at REAL NOT NULL, updated_at REAL NOT NULL,
          FOREIGN KEY(client_id) REFERENCES clients(id), FOREIGN KEY(service_id) REFERENCES services(id));
        CREATE UNIQUE INDEX IF NOT EXISTS uq_confirmed_slot
          ON appointments(date,time) WHERE status='confirmed';
        CREATE TABLE IF NOT EXISTS notifications(
          id INTEGER PRIMARY KEY AUTOINCREMENT, appointment_id INTEGER NOT NULL,
          channel TEXT NOT NULL CHECK(channel IN ('whatsapp','sms')),
          status TEXT NOT NULL DEFAULT 'pending', phone TEXT NOT NULL, message TEXT NOT NULL,
          created_at REAL NOT NULL, sent_at REAL,
          FOREIGN KEY(appointment_id) REFERENCES appointments(id));
        CREATE TABLE IF NOT EXISTS audit_log(
          id INTEGER PRIMARY KEY AUTOINCREMENT, actor_type TEXT NOT NULL, actor_id TEXT NOT NULL,
          action TEXT NOT NULL, target_type TEXT, target_id TEXT, metadata TEXT, created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS owners(
          id INTEGER PRIMARY KEY AUTOINCREMENT, phone TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
          max_devices INTEGER NOT NULL DEFAULT 1, created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS owner_devices(
          id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL,
          device_id TEXT NOT NULL UNIQUE, public_jwk TEXT NOT NULL,
          created_at REAL NOT NULL, last_seen REAL,
          FOREIGN KEY(owner_id) REFERENCES owners(id) ON DELETE CASCADE);
        """)
        services = [(1,"Corte de Cabelo",15,30),(2,"Barba",10,20),(3,"Corte + Barba",22,50)]
        c.executemany("INSERT OR IGNORE INTO services VALUES(?,?,?,?)", services)

def rowdict(r): return dict(r) if r else None

def audit(c, action, target_type=None, target_id=None, metadata=None, actor_type=None, actor_id=None):
    import json
    actor_type = actor_type or ("developer" if session.get("dev_auth") else "system")
    actor_id = actor_id or ("developer" if session.get("dev_auth") else "system")
    c.execute("""INSERT INTO audit_log(actor_type,actor_id,action,target_type,target_id,metadata,created_at)
                 VALUES(?,?,?,?,?,?,?)""",
              (actor_type,actor_id,action,target_type,str(target_id) if target_id is not None else None,
               json.dumps(metadata or {}, ensure_ascii=False),time.time()))

def appointment_row(c, aid):
    return c.execute("""SELECT a.id,a.date,a.time,a.status,a.created_at,a.updated_at,
      cl.name client,cl.phone,s.name service,s.price,s.duration
      FROM appointments a JOIN clients cl ON cl.id=a.client_id
      JOIN services s ON s.id=a.service_id WHERE a.id=?""",(aid,)).fetchone()

def notification_message(appt, action):
    if action == "confirmed":
        return f"Barbearia: seu agendamento foi CONFIRMADO. {appt['service']} em {appt['date']} às {appt['time']}."
    return f"Barbearia: sua solicitação de {appt['service']} em {appt['date']} às {appt['time']} foi RECUSADA."

def queue_notifications(c, appt, action):
    msg=notification_message(appt,action)
    for channel in ("whatsapp","sms"):
        c.execute("""INSERT INTO notifications(appointment_id,channel,status,phone,message,created_at)
                     VALUES(?,?,?,?,?,?)""",(appt["id"],channel,"pending",appt["phone"],msg,time.time()))

def b64u_decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return "s1$" + base64.urlsafe_b64encode(salt).decode().rstrip("=") + "$" + base64.urlsafe_b64encode(digest).decode().rstrip("=")

def verify_password(password, encoded):
    try:
        _, salt_b64, digest_b64 = encoded.split("$", 2)
        expected = hash_password(password, b64u_decode(salt_b64)).split("$", 2)[2]
        return secrets.compare_digest(expected, digest_b64)
    except Exception:
        return False

def public_key_from_jwk(jwk):
    if not isinstance(jwk, dict) or jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise ValueError("Chave de dispositivo inválida")
    x = int.from_bytes(b64u_decode(jwk["x"]), "big")
    y = int.from_bytes(b64u_decode(jwk["y"]), "big")
    return ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()

def verify_device_signature(public_jwk, challenge_b64, signature_b64):
    key = public_key_from_jwk(public_jwk)
    key.verify(b64u_decode(signature_b64), b64u_decode(challenge_b64), ec.ECDSA(hashes.SHA256()))

def require_csrf():
    token=session.get("csrf_token")
    supplied=request.headers.get("X-CSRF-Token","")
    if not token or not supplied or not secrets.compare_digest(token,supplied):
        return jsonify({"error":"Proteção CSRF inválida"}),403
    return None

def require_dev(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args,**kwargs):
        if not session.get("dev_auth"): return jsonify({"error":"Acesso de desenvolvedor necessário"}),401
        if request.method=="POST":
            csrf=require_csrf()
            if csrf:return csrf
        return fn(*args,**kwargs)
    return wrapper

def require_client(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args,**kwargs):
        phone = session.get("client_phone")
        if not phone:
            return jsonify({"error":"Autenticação do cliente necessária"}),401
        if request.method=="POST":
            csrf=require_csrf()
            if csrf:return csrf
        return fn(*args,**kwargs)
    return wrapper

def require_owner(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args,**kwargs):
        if not (session.get("owner_auth") or session.get("dev_auth")):
            return jsonify({"error":"Autenticação do proprietário necessária"}),401
        if request.method=="POST":
            csrf=require_csrf()
            if csrf:return csrf
        return fn(*args,**kwargs)
    return wrapper

@app.get("/")
def index(): return send_from_directory(WEB,"index.html")
@app.get("/proprietario.html")
def owner_page(): return send_from_directory(WEB,"proprietario.html")
@app.get("/dev.html")
def dev_page(): return send_from_directory(WEB,"dev.html")
@app.get("/<path:path>")
def assets(path): return send_from_directory(WEB,path)

@app.get("/api/health")
def health(): return jsonify({"status":"ok","database":str(DB),"mode":"remote-shared-backend"})

@app.get("/api/csrf")
def csrf_endpoint():
    if not (session.get("client_phone") or session.get("owner_auth") or session.get("dev_auth")):
        return jsonify({"error":"Autenticação necessária"}),401
    session["csrf_token"]=secrets.token_urlsafe(32)
    return jsonify({"csrf_token":session["csrf_token"]})

@app.post("/api/client/register")
def register():
    data=request.get_json(force=True); name=str(data.get("name","")).strip(); phone=str(data.get("phone","")).strip()
    if not name or not phone: return jsonify({"error":"Nome e telefone são obrigatórios"}),400
    with LOCK, db() as c:
        existing=c.execute("SELECT id,name,phone FROM clients WHERE phone=?",(phone,)).fetchone()
        if existing and session.get("client_phone") != phone:
            return jsonify({"error":"Cliente já registrado neste estabelecimento. Autenticação necessária."}),409
        if existing:
            c.execute("UPDATE clients SET name=? WHERE phone=?",(name,phone))
        else:
            c.execute("INSERT INTO clients(name,phone,created_at) VALUES(?,?,?)",(name,phone,time.time()))
        r=c.execute("SELECT id,name,phone FROM clients WHERE phone=?",(phone,)).fetchone()
    session["client_phone"]=phone; session["csrf_token"]=secrets.token_urlsafe(32); session.permanent=True
    return jsonify(rowdict(r))

@app.get("/api/services")
def services():
    with db() as c: return jsonify([rowdict(x) for x in c.execute("SELECT * FROM services ORDER BY id")])

@app.post("/api/appointments")
@require_client
def create_appointment():
    data=request.get_json(force=True); phone=str(data.get("phone","")).strip()
    if phone != session.get("client_phone"):
        return jsonify({"error":"Acesso negado"}),403
    service_id=int(data.get("service_id",0)); date=str(data.get("date","")).strip(); tm=str(data.get("time","")).strip()
    if not all([phone,service_id,date,tm]): return jsonify({"error":"Dados incompletos"}),400
    with LOCK, db() as c:
        client=c.execute("SELECT * FROM clients WHERE phone=?",(phone,)).fetchone()
        if not client: return jsonify({"error":"Cliente não cadastrado"}),404
        if not c.execute("SELECT 1 FROM services WHERE id=?",(service_id,)).fetchone(): return jsonify({"error":"Serviço inválido"}),400
        cur=c.execute("""INSERT INTO appointments(client_id,service_id,date,time,status,created_at,updated_at)
                         VALUES(?,?,?,?,?,?,?)""",(client["id"],service_id,date,tm,"pending",time.time(),time.time()))
        aid=cur.lastrowid; appt=appointment_row(c,aid)
        audit(c,"appointment_created","appointment",aid,{"status":"pending"},actor_type="client",actor_id=phone)
    return jsonify(rowdict(appt)),201

@app.get("/api/appointments")
@require_client
def client_appointments():
    phone=request.args.get("phone","").strip()
    if phone != session.get("client_phone"):
        return jsonify({"error":"Acesso negado"}),403
    with db() as c:
        rows=c.execute("""SELECT a.id,a.date,a.time,a.status,a.created_at,a.updated_at,
          cl.name client,cl.phone,s.id service_id,s.name service,s.price,s.duration
          FROM appointments a JOIN clients cl ON cl.id=a.client_id JOIN services s ON s.id=a.service_id
          WHERE cl.phone=? ORDER BY a.date DESC,a.time DESC,a.id DESC""",(phone,)).fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.post("/api/appointments/<int:aid>/cancel")
@require_client
def cancel_appointment(aid):
    with LOCK, db() as c:
        r=c.execute("""SELECT a.status,cl.phone FROM appointments a JOIN clients cl ON cl.id=a.client_id WHERE a.id=?""",(aid,)).fetchone()
        if not r: return jsonify({"error":"Agendamento não encontrado"}),404
        if r["phone"] != session.get("client_phone"): return jsonify({"error":"Acesso negado"}),403
        if r["status"] not in ("pending","confirmed"): return jsonify({"error":"Agendamento não pode ser cancelado"}),409
        c.execute("UPDATE appointments SET status='cancelled',updated_at=? WHERE id=?",(time.time(),aid))
        appt=appointment_row(c,aid); audit(c,"appointment_cancelled","appointment",aid)
    return jsonify(rowdict(appt))

@app.get("/api/owner/appointments")
@require_owner
def owner_appointments():
    status=request.args.get("status")
    q="""SELECT a.id,a.date,a.time,a.status,a.created_at,a.updated_at,cl.name client,cl.phone,
         s.name service,s.price,s.duration FROM appointments a JOIN clients cl ON cl.id=a.client_id
         JOIN services s ON s.id=a.service_id"""
    params=[]
    if status: q+=" WHERE a.status=?"; params.append(status)
    q+=" ORDER BY CASE a.status WHEN 'pending' THEN 0 WHEN 'confirmed' THEN 1 ELSE 2 END,a.date,a.time,a.id"
    with db() as c: rows=c.execute(q,params).fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.get("/api/owner/clients")
@require_owner
def owner_clients():
    with db() as c:
        rows=c.execute("""SELECT cl.id,cl.name,cl.phone,cl.created_at,COUNT(a.id) appointments
                          FROM clients cl LEFT JOIN appointments a ON a.client_id=cl.id
                          GROUP BY cl.id ORDER BY cl.name""").fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.post("/api/owner/appointments/<int:aid>/confirm")
@require_owner
def confirm_appointment(aid):
    with LOCK, db() as c:
        appt=appointment_row(c,aid)
        if not appt: return jsonify({"error":"Agendamento não encontrado"}),404
        if appt["status"]!="pending": return jsonify({"error":"Somente pendentes podem ser confirmados"}),409
        occupied=c.execute("""SELECT id FROM appointments WHERE date=? AND time=? AND status='confirmed' AND id<>?""",
                           (appt["date"],appt["time"],aid)).fetchone()
        if occupied: return jsonify({"error":"Horário já confirmado para outro cliente"}),409
        c.execute("UPDATE appointments SET status='confirmed',updated_at=? WHERE id=?",(time.time(),aid))
        appt=appointment_row(c,aid); queue_notifications(c,appt,"confirmed")
        audit(c,"appointment_confirmed","appointment",aid)
    return jsonify({"appointment":rowdict(appt),"notifications":["whatsapp","sms"],"notification_status":"pending"})

@app.post("/api/owner/appointments/<int:aid>/reject")
@require_owner
def reject_appointment(aid):
    with LOCK, db() as c:
        appt=appointment_row(c,aid)
        if not appt: return jsonify({"error":"Agendamento não encontrado"}),404
        if appt["status"]!="pending": return jsonify({"error":"Somente pendentes podem ser recusados"}),409
        c.execute("UPDATE appointments SET status='rejected',updated_at=? WHERE id=?",(time.time(),aid))
        appt=appointment_row(c,aid); queue_notifications(c,appt,"rejected"); audit(c,"appointment_rejected","appointment",aid)
    return jsonify({"appointment":rowdict(appt),"notifications":["whatsapp","sms"],"notification_status":"pending"})

@app.get("/api/notifications")
@require_owner
def notifications():
    with db() as c: rows=c.execute("SELECT * FROM notifications ORDER BY id DESC").fetchall()
    return jsonify([rowdict(x) for x in rows])

# ---------- DEVELOPER CONSOLE ----------
@app.post("/api/client/logout")
def client_logout():
    session.pop("client_phone", None)
    return jsonify({"authenticated":False})

@app.get("/api/client/me")
def client_me():
    return jsonify({"authenticated":bool(session.get("client_phone")), "phone":session.get("client_phone")})

@app.post("/api/dev/owners")
@require_dev
def dev_create_owner():
    data=request.get_json(force=True); phone=str(data.get("phone","")).strip(); password=str(data.get("password","")); max_devices=int(data.get("max_devices",1))
    if not phone or len(password) < 12: return jsonify({"error":"Telefone e senha de no mínimo 12 caracteres são obrigatórios"}),400
    if max_devices < 1 or max_devices > 20: return jsonify({"error":"Número de dispositivos inválido"}),400
    with LOCK, db() as c:
        try:
            cur=c.execute("INSERT INTO owners(phone,password_hash,max_devices,created_at) VALUES(?,?,?,?)",(phone,hash_password(password),max_devices,time.time()))
        except sqlite3.IntegrityError:
            return jsonify({"error":"Telefone do proprietário já registrado"}),409
        audit(c,"owner_created","owner",cur.lastrowid,{"phone":phone,"max_devices":max_devices})
        return jsonify({"id":cur.lastrowid,"phone":phone,"max_devices":max_devices}),201

@app.post("/api/owner/device/register")
def owner_device_register():
    data=request.get_json(force=True); phone=str(data.get("phone","")).strip(); password=str(data.get("password","")); device_id=str(data.get("device_id","")).strip(); public_jwk=data.get("public_jwk")
    if not all([phone,password,device_id,public_jwk]): return jsonify({"error":"Dados de ativação incompletos"}),400
    try: public_key_from_jwk(public_jwk)
    except Exception: return jsonify({"error":"Chave pública de dispositivo inválida"}),400
    with LOCK, db() as c:
        owner=c.execute("SELECT * FROM owners WHERE phone=? AND active=1",(phone,)).fetchone()
        if not owner or not verify_password(password,owner["password_hash"]): return jsonify({"error":"Credencial inválida"}),401
        existing=c.execute("SELECT owner_id FROM owner_devices WHERE device_id=?",(device_id,)).fetchone()
        if existing and existing["owner_id"] != owner["id"]: return jsonify({"error":"Dispositivo já vinculado a outro proprietário"}),409
        count=c.execute("SELECT COUNT(*) n FROM owner_devices WHERE owner_id=?",(owner["id"],)).fetchone()["n"]
        if not existing and count >= owner["max_devices"]: return jsonify({"error":"Limite de dispositivos atingido"}),409
        if existing:
            c.execute("UPDATE owner_devices SET public_jwk=?,last_seen=? WHERE device_id=?",(json.dumps(public_jwk,separators=(",",":")),time.time(),device_id))
        else:
            c.execute("INSERT INTO owner_devices(owner_id,device_id,public_jwk,created_at,last_seen) VALUES(?,?,?,?,?)",(owner["id"],device_id,json.dumps(public_jwk,separators=(",",":")),time.time(),time.time()))
        audit(c,"owner_device_registered","owner",owner["id"],{"device_id":device_id})
    return jsonify({"registered":True,"phone":phone,"device_id":device_id})

@app.post("/api/owner/challenge")
def owner_challenge():
    data=request.get_json(force=True); phone=str(data.get("phone","")).strip(); device_id=str(data.get("device_id","")).strip()
    with db() as c:
        row=c.execute("SELECT o.id,o.phone,d.device_id FROM owners o JOIN owner_devices d ON d.owner_id=o.id WHERE o.phone=? AND o.active=1 AND d.device_id=?",(phone,device_id)).fetchone()
    if not row: return jsonify({"error":"Proprietário ou dispositivo não autorizado"}),401
    challenge=secrets.token_bytes(32); challenge_b64=base64.urlsafe_b64encode(challenge).decode().rstrip("=")
    session["owner_challenge"]=challenge_b64; session["owner_challenge_device_id"]=device_id; session["owner_challenge_expires"]=time.time()+120
    return jsonify({"challenge":challenge_b64})

@app.post("/api/owner/login")
def owner_login():
    data=request.get_json(force=True); phone=str(data.get("phone","")).strip(); device_id=str(data.get("device_id","")).strip(); signature=str(data.get("signature","")).strip()
    challenge=session.get("owner_challenge")
    if not challenge or session.get("owner_challenge_device_id") != device_id or time.time() > float(session.get("owner_challenge_expires",0)):
        return jsonify({"error":"Desafio de autenticação ausente ou expirado"}),401
    with LOCK, db() as c:
        row=c.execute("SELECT o.id,o.phone,o.active,d.public_jwk FROM owners o JOIN owner_devices d ON d.owner_id=o.id WHERE o.phone=? AND o.active=1 AND d.device_id=?",(phone,device_id)).fetchone()
        if not row: return jsonify({"error":"Proprietário ou dispositivo não autorizado"}),401
        try: verify_device_signature(json.loads(row["public_jwk"]),challenge,signature)
        except Exception: return jsonify({"error":"Assinatura do dispositivo inválida"}),401
        c.execute("UPDATE owner_devices SET last_seen=? WHERE device_id=?",(time.time(),device_id))
        audit(c,"owner_login",actor_type="owner",actor_id=phone,metadata={"device_id":device_id})
    session.pop("owner_challenge", None); session.pop("owner_challenge_device_id", None); session.pop("owner_challenge_expires", None)
    session.clear(); session["owner_auth"]=True; session["owner_id"]=row["id"]; session["owner_phone"]=row["phone"]; session["owner_device_id"]=device_id; session["csrf_token"]=secrets.token_urlsafe(32); session.permanent=True
    return jsonify({"authenticated":True,"phone":row["phone"],"device_id":device_id})

@app.get("/api/owner/me")
def owner_me():
    return jsonify({"authenticated":bool(session.get("owner_auth") or session.get("dev_auth")),"phone":session.get("owner_phone"),"device_id":session.get("owner_device_id")})

@app.post("/api/owner/logout")
@require_owner
def owner_logout():
    session.clear(); return jsonify({"authenticated":False})

@app.post("/api/dev/login")
def dev_login():
    data=request.get_json(force=True); password=str(data.get("password",""))
    if not secrets.compare_digest(password,get_dev_secret()):
        return jsonify({"error":"Credencial inválida"}),401
    session.clear(); session["dev_auth"]=True; session["csrf_token"]=secrets.token_urlsafe(32); session.permanent=True
    with LOCK, db() as c: audit(c,"developer_login")
    return jsonify({"authenticated":True})

@app.get("/api/dev/me")
def dev_me(): return jsonify({"authenticated":bool(session.get("dev_auth"))})

@app.post("/api/dev/logout")
@require_dev
def dev_logout():
    session.clear(); return jsonify({"authenticated":False})

@app.get("/api/dev/dashboard")
@require_dev
def dev_dashboard():
    with db() as c:
        stats={}
        for table in ("clients","appointments","notifications","audit_log"):
            stats[table]=c.execute(f"SELECT COUNT(*) n FROM {table}").fetchone()["n"]
        pending=c.execute("SELECT COUNT(*) n FROM appointments WHERE status='pending'").fetchone()["n"]
        confirmed=c.execute("SELECT COUNT(*) n FROM appointments WHERE status='confirmed'").fetchone()["n"]
        notif_pending=c.execute("SELECT COUNT(*) n FROM notifications WHERE status='pending'").fetchone()["n"]
    return jsonify({"status":"ok","database":str(DB),"stats":stats,
                    "appointments_pending":pending,"appointments_confirmed":confirmed,
                    "notifications_pending":notif_pending,"developer_access":"authenticated"})

@app.get("/api/dev/system")
@require_dev
def dev_system():
    return jsonify({"python":"3.x","backend":"Flask","database":str(DB),
                    "dev_secret":"externalized","source_contains_password":False,
                    "session_auth":True,"test_reset_available":True})

@app.get("/api/dev/clients")
@require_dev
def dev_clients():
    with db() as c:
        rows=c.execute("""SELECT cl.id,cl.name,cl.phone,cl.created_at,COUNT(a.id) appointments
                          FROM clients cl LEFT JOIN appointments a ON a.client_id=cl.id
                          GROUP BY cl.id ORDER BY cl.id DESC""").fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.get("/api/dev/appointments")
@require_dev
def dev_appointments():
    with db() as c:
        rows=c.execute("""SELECT a.id,a.date,a.time,a.status,a.created_at,a.updated_at,
          cl.name client,cl.phone,s.name service,s.price,s.duration
          FROM appointments a JOIN clients cl ON cl.id=a.client_id JOIN services s ON s.id=a.service_id
          ORDER BY a.id DESC""").fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.get("/api/dev/notifications")
@require_dev
def dev_notifications():
    with db() as c: rows=c.execute("SELECT * FROM notifications ORDER BY id DESC").fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.get("/api/dev/services")
@require_dev
def dev_services():
    with db() as c: rows=c.execute("SELECT * FROM services ORDER BY id").fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.get("/api/dev/audit")
@require_dev
def dev_audit():
    with db() as c: rows=c.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 500").fetchall()
    return jsonify([rowdict(x) for x in rows])

@app.post("/api/dev/test/reset")
@require_dev
def dev_test_reset():
    data=request.get_json(silent=True) or {}
    if data.get("confirm")!="RESET_TEST_ENVIRONMENT": return jsonify({"error":"Confirmação inválida"}),400
    with LOCK, db() as c:
        c.execute("DELETE FROM notifications"); c.execute("DELETE FROM appointments"); c.execute("DELETE FROM clients")
        audit(c,"test_environment_reset")
    return jsonify({"status":"reset","environment":"local test database","message":"Dados de teste removidos"})

init_db()

if __name__=="__main__":
    port=int(os.environ.get("PORT","8787"))
    host=os.environ.get("HOST","127.0.0.1")
    print(f"BARBEARIA_BACKEND http://{host}:{port} DB={DB}")
    app.run(host=host,port=port,debug=False)
