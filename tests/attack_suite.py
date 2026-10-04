import os, tempfile, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["BARBEARIA_OWNER_PASSWORD"]="TEST-OWNER-ONLY"
import backend

def setup():
    fd,path=tempfile.mkstemp(suffix=".sqlite"); os.close(fd); backend.DB=Path(path); backend.init_db()

def result(name, ok, detail): print(("PASS " if ok else "FAIL ")+name+" :: "+detail)

setup(); owner=backend.app.test_client(); a=backend.app.test_client(); b=backend.app.test_client()
# registration and client sessions
ra=a.post("/api/client/register",json={"name":"A","phone":"+351910000401"}); rb=b.post("/api/client/register",json={"name":"B","phone":"+351910000402"})
result("client registration",ra.status_code==200 and rb.status_code==200,f"{ra.status_code}/{rb.status_code}")
# client impersonation / duplicate phone
r=b.post("/api/client/register",json={"name":"ATTACK","phone":"+351910000401"}); result("duplicate phone takeover",r.status_code==409,str(r.status_code))
# create records
ap=a.post("/api/appointments",json={"phone":"+351910000401","service_id":1,"date":"2026-12-10","time":"10:00"}).json
bp=b.post("/api/appointments",json={"phone":"+351910000402","service_id":1,"date":"2026-12-10","time":"11:00"}).json
# IDOR
r=a.get("/api/appointments?phone=%2B351910000402"); result("IDOR read",r.status_code==403,str(r.status_code))
r=a.post(f"/api/appointments/{bp['id']}/cancel"); result("IDOR cancel",r.status_code==403,str(r.status_code))
# owner auth
r=owner.get("/api/owner/appointments"); result("owner unauth",r.status_code==401,str(r.status_code))
r=owner.post("/api/owner/login",json={"password":"wrong"}); result("owner bad password",r.status_code==401,str(r.status_code))
r=owner.post("/api/owner/login",json={"password":"TEST-OWNER-ONLY"}); result("owner login",r.status_code==200,str(r.status_code))
r=owner.get("/api/owner/appointments"); result("owner auth",r.status_code==200,str(r.status_code))
# invalid and replay
r=owner.post(f"/api/owner/appointments/{ap['id']}/confirm"); result("confirm",r.status_code==200,str(r.status_code))
r=owner.post(f"/api/owner/appointments/{ap['id']}/confirm"); result("replay confirm blocked",r.status_code==409,str(r.status_code))
r=owner.post(f"/api/owner/appointments/{bp['id']}/reject"); result("reject",r.status_code==200,str(r.status_code))
r=owner.post(f"/api/owner/appointments/{bp['id']}/reject"); result("replay reject blocked",r.status_code==409,str(r.status_code))
# invalid IDs/payloads
r=owner.post("/api/owner/appointments/999999/confirm"); result("unknown appointment",r.status_code==404,str(r.status_code))
r=owner.post("/api/owner/appointments/not-an-id/confirm"); result("invalid path id",r.status_code in (404,405),str(r.status_code))
r=owner.post("/api/owner/appointments/1/confirm",json={"unexpected":"x"}); result("unexpected payload no privilege bypass",r.status_code in (409,404),str(r.status_code))
# method
r=owner.delete("/api/owner/appointments"); result("unexpected method",r.status_code==405,str(r.status_code))
# logout/session
r=owner.post("/api/owner/logout"); result("owner logout",r.status_code==200,str(r.status_code))
r=owner.get("/api/owner/appointments"); result("post-logout blocked",r.status_code==401,str(r.status_code))
# client logout
r=a.get("/api/client/me"); result("client session",r.status_code==200 and r.json.get("authenticated") is True,str(r.json))
r=a.post("/api/client/logout"); result("client logout",r.status_code==200,str(r.status_code))
r=a.get("/api/appointments?phone=%2B351910000401"); result("post-client-logout blocked",r.status_code==401,str(r.status_code))
# CORS
with backend.app.test_client() as c:
    r=c.options("/api/owner/appointments",headers={"Origin":"https://evil.example","Access-Control-Request-Method":"GET"})
    result("CORS evil origin", "https://evil.example" not in str(r.headers.get("Access-Control-Allow-Origin","")), str(r.status_code))
