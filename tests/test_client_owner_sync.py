from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]

def load_db(tmp_path):
    src=ROOT/"shared_db.py"
    spec=importlib.util.spec_from_file_location("barbearia_shared_db_qa2",src)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.DB_PATH=tmp_path/"shared.db"; return mod

def test_registration_by_phone_and_repeat_entry(tmp_path):
    db=load_db(tmp_path)
    ok,msg,row=db.register_client("Ana QA","+351 910 000 001")
    assert ok and row[1:]==("Ana QA","+351910000001")
    ok,msg,row2=db.register_client("Ana QA","+351 910 000 001")
    assert ok and row2[0]==row[0]
    assert len(db.clients())==1

def test_client_owner_sync_cancel_and_rebook(tmp_path):
    db=load_db(tmp_path)
    ok,msg,aid=db.book("Cliente QA","900000001",db.SERVICES[0][0],"2035-01-10","10:00")
    assert ok and aid
    rows=db.appointments()
    assert rows[0][1:6]==("Cliente QA","900000001",db.SERVICES[0][0],"2035-01-10","10:00")
    assert rows[0][6]=="confirmed"
    notices=db.notifications(aid)
    assert {n[2] for n in notices}=={"whatsapp","sms"}
    db.cancel(aid)
    assert db.appointments()[0][6]=="cancelled"
    ok,msg,aid2=db.book("Cliente QA 2","900000002",db.SERVICES[0][0],"2035-01-10","10:00")
    assert ok and aid2!=aid

def test_owner_sees_all_registered_clients(tmp_path):
    db=load_db(tmp_path)
    db.register_client("A","9001"); db.register_client("B","9002")
    assert [(r[1],r[2]) for r in db.clients()]==[("A","9001"),("B","9002")]

def test_service_catalog_does_not_duplicate_on_refresh(tmp_path):
    db=load_db(tmp_path)
    for _ in range(10): db.connect().close()
    with db.connect() as conn:
        rows=conn.execute("SELECT name,COUNT(*) FROM services GROUP BY name").fetchall()
    assert sorted(rows)==sorted([(name,1) for name,_ in db.SERVICES])
