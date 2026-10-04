from pathlib import Path
import subprocess,sys

ROOT=Path(r"F:\Fábrica\Teste\Barbearia")

def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    print(p.stdout); print(p.stderr)
    assert p.returncode==0, p.stderr

def test_apps_compile():
    run([sys.executable,"-m","py_compile","app_cliente.py","app_proprietario.py","shared_db.py"])
