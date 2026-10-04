import os,sys
sys.path.insert(0, r"F:\Fábrica\Teste\Barbearia")
os.environ["BARBEARIA_OWNER_PASSWORD"]="TEST-OWNER-ONLY"
import backend
c=backend.app.test_client()
paths=["/api/owner/appointments","/api/owner/clients","/api/notifications","/api/owner/me"]
print("UNAUTH", [(p,c.get(p).status_code) for p in paths])
print("BAD_LOGIN", c.post("/api/owner/login", json={"password":"wrong"}).status_code)
print("GOOD_LOGIN", c.post("/api/owner/login", json={"password":"TEST-OWNER-ONLY"}).status_code)
print("AUTH", [(p,c.get(p).status_code) for p in paths])
print("LOGOUT", c.post("/api/owner/logout").status_code)
print("POST_LOGOUT", c.get("/api/owner/appointments").status_code)
