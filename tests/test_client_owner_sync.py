from pathlib import Path
import importlib.util
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def load_db(tmp_path):
    src = ROOT / "shared_db.py"
    spec = importlib.util.spec_from_file_location("barbearia_shared_db_qa", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.DB_PATH = tmp_path / "shared.db"
    return mod

def test_client_actions_are_visible_to_owner_view(tmp_path):
    db = load_db(tmp_path)

    # Cliente agenda.
    ok, _ = db.book("Cliente QA", "900000001", db.SERVICES[0][0], "2035-01-10", "10:00")
    assert ok

    # Proprietário consulta o mesmo banco.
    owner_rows = db.appointments()
    assert len(owner_rows) == 1
    assert owner_rows[0][1:6] == (
        "Cliente QA", "900000001", db.SERVICES[0][0], "2035-01-10", "10:00"
    )
    assert owner_rows[0][6] == "confirmed"

    # Cliente cancela; proprietário passa a ver o cancelamento.
    db.cancel(owner_rows[0][0])
    owner_rows = db.appointments()
    assert owner_rows[0][6] == "cancelled"

    # O horário fica livre e uma nova reserva aparece para o proprietário.
    ok, _ = db.book("Cliente QA 2", "900000002", db.SERVICES[0][0], "2035-01-10", "10:00")
    assert ok
    owner_rows = db.appointments()
    assert len(owner_rows) == 2
    assert owner_rows[-1][1] == "Cliente QA 2"
    assert owner_rows[-1][6] == "confirmed"

def test_service_catalog_does_not_duplicate_on_refresh(tmp_path):
    db = load_db(tmp_path)
    for _ in range(10):
        db.connect().close()
    with db.connect() as conn:
        rows = conn.execute("SELECT name, COUNT(*) FROM services GROUP BY name").fetchall()
    assert sorted(rows) == sorted([(name, 1) for name, _ in db.SERVICES])
