import os
os.environ["BARBEARIA_OWNER_PASSWORD"]="TEST-OWNER-ONLY"
import backend

def fresh_db(tmp_path):
    backend.DB = tmp_path / "test.sqlite"
    backend.init_db()

def owner(c):
    assert c.post("/api/owner/login", json={"password":"TEST-OWNER-ONLY"}).status_code == 200

def test_pending_confirm_and_notifications(tmp_path):
    fresh_db(tmp_path); c=backend.app.test_client()
    assert c.post("/api/client/register",json={"name":"A","phone":"+351910000201"}).status_code==200
    r=c.post("/api/appointments",json={"phone":"+351910000201","service_id":1,"date":"2026-10-30","time":"15:00"}); assert r.status_code==201
    owner(c); aid=r.json["id"]
    assert c.get("/api/owner/appointments?status=pending").status_code==200
    r=c.post(f"/api/owner/appointments/{aid}/confirm"); assert r.status_code==200
    assert {x["channel"] for x in c.get("/api/notifications").json if x["appointment_id"]==aid}=={"whatsapp","sms"}

def test_same_slot_cannot_be_confirmed_twice_and_cancel_releases(tmp_path):
    fresh_db(tmp_path); a=backend.app.test_client(); b=backend.app.test_client(); o=backend.app.test_client()
    assert a.post("/api/client/register",json={"name":"A","phone":"+351910000211"}).status_code==200
    assert b.post("/api/client/register",json={"name":"B","phone":"+351910000212"}).status_code==200
    ap=a.post("/api/appointments",json={"phone":"+351910000211","service_id":1,"date":"2026-10-31","time":"16:00"}).json
    bp=b.post("/api/appointments",json={"phone":"+351910000212","service_id":1,"date":"2026-10-31","time":"16:00"}).json
    owner(o); assert o.post(f"/api/owner/appointments/{ap['id']}/confirm").status_code==200
    assert o.post(f"/api/owner/appointments/{bp['id']}/confirm").status_code==409
    assert b.post(f"/api/appointments/{ap['id']}/cancel").status_code==403
    assert a.post(f"/api/appointments/{ap['id']}/cancel").status_code==200
    assert o.post(f"/api/owner/appointments/{bp['id']}/confirm").status_code==200

def test_reject_and_separate_owner_page(tmp_path):
    fresh_db(tmp_path); c=backend.app.test_client()
    c.post("/api/client/register",json={"name":"C","phone":"+351910000221"})
    a=c.post("/api/appointments",json={"phone":"+351910000221","service_id":2,"date":"2026-11-01","time":"10:00"}).json
    owner(c); r=c.post(f"/api/owner/appointments/{a['id']}/reject"); assert r.status_code==200
    assert {x["channel"] for x in c.get("/api/notifications").json if x["appointment_id"]==a["id"]}=={"whatsapp","sms"}
    assert "Sou proprietário" not in c.get("/").get_data(as_text=True)
    assert c.get("/proprietario.html").status_code==200

def test_client_idor_is_blocked(tmp_path):
    fresh_db(tmp_path); a=backend.app.test_client(); b=backend.app.test_client()
    a.post("/api/client/register",json={"name":"A","phone":"+351910000231"})
    b.post("/api/client/register",json={"name":"B","phone":"+351910000232"})
    ap=b.post("/api/appointments",json={"phone":"+351910000232","service_id":1,"date":"2026-11-02","time":"11:00"}).json
    assert a.get("/api/appointments?phone=%2B351910000232").status_code==403
    assert a.post(f"/api/appointments/{ap['id']}/cancel").status_code==403

def test_duplicate_client_registration_is_blocked(tmp_path):
    fresh_db(tmp_path); a=backend.app.test_client(); b=backend.app.test_client()
    assert a.post("/api/client/register",json={"name":"A","phone":"+351910000241"}).status_code==200
    assert b.post("/api/client/register",json={"name":"ATTACKER","phone":"+351910000241"}).status_code==409
