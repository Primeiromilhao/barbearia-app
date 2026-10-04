from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def test_dual_app_artifacts():
    assert (ROOT/"app_cliente.py").exists()
    assert (ROOT/"app_proprietario.py").exists()
    assert (ROOT/"shared_db.py").exists()

def test_shared_database_cycle():
    with tempfile.TemporaryDirectory() as td:
        db_path=Path(td)/"shared.db"
        code = (ROOT/"shared_db.py").read_text(encoding="utf-8")
        ns={"__name__":"shared_db","__file__":str(db_path)}
        exec(compile(code,str(ROOT/"shared_db.py"),"exec"),ns)
        ns["DB_PATH"]=db_path
        ok,msg,_=ns["book"]("Cliente Teste","999","Serviço básico","2030-01-02","10:00")
        assert ok and "confirm" in msg.lower()
        rows=ns["appointments"]()
        assert len(rows)==1 and rows[0][2]=="999"
        ok,_,_=ns["book"]("Outro","888","Serviço básico","2030-01-02","10:00")
        assert not ok
        ns["cancel"](rows[0][0])
        ok,_,_=ns["book"]("Outro","888","Serviço básico","2030-01-02","10:00")
        assert ok
        rows=ns["appointments"]()
        assert len(rows)==2 and rows[0][6]=="cancelled"
