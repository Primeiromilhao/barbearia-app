import sys, pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import json,base64,secrets
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from backend import app,get_dev_secret,DB
def b64u(b): return base64.urlsafe_b64encode(b).decode().rstrip("=")
def jwk(pub):
 n=pub.public_numbers(); return {"kty":"EC","crv":"P-256","x":b64u(n.x.to_bytes(32,"big")),"y":b64u(n.y.to_bytes(32,"big")),"alg":"ES256"}
def main():
 app.config.update(TESTING=True)
 phone="+351920000901"; password="TestOwner!2026Secure"
 with app.test_client() as c:
  assert c.post("/api/dev/login",json={"password":get_dev_secret()}).status_code==200
  c.post("/api/dev/owners",json={"phone":phone,"password":password,"max_devices":1})
  k=ec.generate_private_key(ec.SECP256R1()); pub=jwk(k.public_key()); did="device-"+secrets.token_hex(8)
  r=c.post("/api/owner/device/register",json={"phone":phone,"password":password,"device_id":did,"public_jwk":pub}); assert r.status_code==200,r.data
  r=c.post("/api/owner/challenge",json={"phone":phone,"device_id":did}); assert r.status_code==200
  ch=r.json["challenge"]; sig=k.sign(base64.urlsafe_b64decode(ch+"="*(-len(ch)%4)),ec.ECDSA(hashes.SHA256()))
  r=c.post("/api/owner/login",json={"phone":phone,"device_id":did,"signature":b64u(sig)}); assert r.status_code==200,r.data
  assert c.get("/api/owner/me").json["authenticated"]
  r=c.post("/api/owner/login",json={"phone":phone,"device_id":did,"signature":b64u(sig)}); assert r.status_code==401
  k2=ec.generate_private_key(ec.SECP256R1()); did2="device-"+secrets.token_hex(8)
  r=c.post("/api/owner/device/register",json={"phone":phone,"password":password,"device_id":did2,"public_jwk":jwk(k2.public_key())}); assert r.status_code==409,r.data
  print("DEVICE_BINDING_TEST_PASS")
if __name__=="__main__": main()
