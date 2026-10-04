import os
import sqlite3
import tempfile
import backend

def fresh_db(tmp_path):
    backend.DB = tmp_path / "test.sqlite"
    backend.init_db()

def test_pending_confirm_and_notifications(tmp_path):
    fresh_db(tmp_path)
    c = backend.app.test_client()
    assert c.post("/api/client/register", json={"name":"A","phone":"+351910000201"}).status_code == 200
    r = c.post("/api/appointments", json={"phone":"+351910000201","service_id":1,"date":"2026-10-30","time":"15:00"})
    assert r.status_code == 201
    aid = r.json["id"]
    assert r.json["status"] == "pending"
    assert len(c.get("/api/owner/appointments?status=pending").json) == 1
    r = c.post(f"/api/owner/appointments/{aid}/confirm")
    assert r.status_code == 200
    assert r.json["appointment"]["status"] == "confirmed"
    notes = c.get("/api/notifications").json
    assert {x["channel"] for x in notes if x["appointment_id"] == aid} == {"whatsapp","sms"}

def test_same_slot_cannot_be_confirmed_twice_and_cancel_releases(tmp_path):
    fresh_db(tmp_path)
    c = backend.app.test_client()
    for n,p in [("A","+351910000211"),("B","+351910000212")]:
        assert c.post("/api/client/register", json={"name":n,"phone":p}).status_code == 200
    payload=lambda p: {"phone":p,"service_id":1,"date":"2026-10-31","time":"16:00"}
    a=c.post("/api/appointments",json=payload("+351910000211")).json
    b=c.post("/api/appointments",json=payload("+351910000212")).json
    assert c.post(f"/api/owner/appointments/{a['id']}/confirm").status_code == 200
    assert c.post(f"/api/owner/appointments/{b['id']}/confirm").status_code == 409
    assert c.post(f"/api/appointments/{a['id']}/cancel").status_code == 200
    assert c.post(f"/api/owner/appointments/{b['id']}/confirm").status_code == 200

def test_reject_and_separate_owner_page(tmp_path):
    fresh_db(tmp_path)
    c = backend.app.test_client()
    c.post("/api/client/register", json={"name":"C","phone":"+351910000221"})
    a=c.post("/api/appointments",json={"phone":"+351910000221","service_id":2,"date":"2026-11-01","time":"10:00"}).json
    assert c.post(f"/api/owner/appointments/{a['id']}/reject").json["appointment"]["status"] == "rejected"
    notes=[x for x in c.get("/api/notifications").json if x["appointment_id"]==a["id"]]
    assert {x["channel"] for x in notes} == {"whatsapp","sms"}
    assert "Sou proprietário" not in c.get("/").get_data(as_text=True)
    assert c.get("/proprietario.html").status_code == 200
