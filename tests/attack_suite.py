import os,tempfile,sys,secrets,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
os.environ["BARBEARIA_DEV_PASSWORD"]="TEST-DEV-ONLY"
import backend

def b64u(b): return base64.urlsafe_b64encode(b).decode().rstrip("=")
def jwk(pub):
 n=pub.public_numbers(); return {"kty":"EC","crv":"P-256","x":b64u(n.x.to_bytes(32,"big")),"y":b64u(n.y.to_bytes(32,"big")),"alg":"ES256"}
def result(name,ok,detail): print(("PASS " if ok else "FAIL ")+name+" :: "+detail)
def post(client,path,**kwargs):
    token=client.get("/api/csrf").json.get("csrf_token")
    headers=kwargs.pop("headers",{});headers["X-CSRF-Token"]=token
    return client.post(path,headers=headers,**kwargs)
fd,path=tempfile.mkstemp(suffix=".sqlite");os.close(fd);backend.DB=Path(path);backend.init_db()
owner=backend.app.test_client();a=backend.app.test_client();b=backend.app.test_client()
ra=a.post("/api/client/register",json={"name":"A","phone":"+351910000401"});rb=b.post("/api/client/register",json={"name":"B","phone":"+351910000402"})
result("client registration",ra.status_code==200 and rb.status_code==200,f"{ra.status_code}/{rb.status_code}")
r=b.post("/api/client/register",json={"name":"ATTACK","phone":"+351910000401"});result("duplicate phone takeover",r.status_code==409,str(r.status_code))
ap=post(a,"/api/appointments",json={"phone":"+351910000401","service_id":1,"date":"2026-12-10","time":"10:00"}).json
bp=post(b,"/api/appointments",json={"phone":"+351910000402","service_id":1,"date":"2026-12-10","time":"11:00"}).json
r=a.get("/api/appointments?phone=%2B351910000402");result("IDOR read",r.status_code==403,str(r.status_code))
r=post(a,f"/api/appointments/{bp['id']}/cancel");result("IDOR cancel",r.status_code==403,str(r.status_code))
r=owner.get("/api/owner/appointments");result("owner unauth",r.status_code==401,str(r.status_code))
phone="+351930000401";password="TEST-OWNER-SECURE-2026"
r=owner.post("/api/dev/login",json={"password":"TEST-DEV-ONLY"});result("dev login",r.status_code==200,str(r.status_code))
r=post(owner,"/api/dev/owners",json={"phone":phone,"password":password,"max_devices":1});result("owner provision",r.status_code==201,str(r.status_code))
did="device-"+secrets.token_hex(8);k=ec.generate_private_key(ec.SECP256R1());pub=jwk(k.public_key())
r=owner.post("/api/owner/device/register",json={"phone":phone,"password":password,"device_id":did,"public_jwk":pub});result("device registration",r.status_code==200,str(r.status_code))
r=owner.post("/api/owner/challenge",json={"phone":phone,"device_id":did});ch=r.json.get("challenge");result("owner challenge",r.status_code==200,str(r.status_code))
sig=k.sign(base64.urlsafe_b64decode(ch+"="*(-len(ch)%4)),ec.ECDSA(hashes.SHA256()))
r=owner.post("/api/owner/login",json={"phone":phone,"device_id":did,"signature":b64u(sig)});result("owner login",r.status_code==200,str(r.status_code))
r=owner.get("/api/owner/appointments");result("owner auth",r.status_code==200,str(r.status_code))
r=post(owner,f"/api/owner/appointments/{ap['id']}/confirm");result("confirm",r.status_code==200,str(r.status_code))
r=post(owner,f"/api/owner/appointments/{ap['id']}/confirm");result("replay confirm blocked",r.status_code==409,str(r.status_code))
r=post(owner,f"/api/owner/appointments/{bp['id']}/reject");result("reject",r.status_code==200,str(r.status_code))
r=post(owner,f"/api/owner/appointments/{bp['id']}/reject");result("replay reject blocked",r.status_code==409,str(r.status_code))
r=post(owner,"/api/owner/appointments/999999/confirm");result("unknown appointment",r.status_code==404,str(r.status_code))
r=post(owner,"/api/owner/appointments/not-an-id/confirm");result("invalid path id",r.status_code in (404,405),str(r.status_code))
r=owner.delete("/api/owner/appointments");result("unexpected method",r.status_code==405,str(r.status_code))
r=post(owner,"/api/owner/logout");result("owner logout",r.status_code==200,str(r.status_code))
r=owner.get("/api/owner/appointments");result("post-logout blocked",r.status_code==401,str(r.status_code))
r=a.post("/api/client/logout");result("client logout",r.status_code==200,str(r.status_code))
r=a.get("/api/appointments?phone=%2B351910000401");result("post-client-logout blocked",r.status_code==401,str(r.status_code))
k2=ec.generate_private_key(ec.SECP256R1());did2="device-"+secrets.token_hex(8)
r=owner.post("/api/owner/device/register",json={"phone":phone,"password":password,"device_id":did2,"public_jwk":jwk(k2.public_key())});result("clone second device blocked",r.status_code==409,str(r.status_code))
with backend.app.test_client() as c:
 r=c.options("/api/owner/appointments",headers={"Origin":"https://evil.example","Access-Control-Request-Method":"GET"})
 result("CORS evil origin","https://evil.example" not in str(r.headers.get("Access-Control-Allow-Origin","")),str(r.status_code))
