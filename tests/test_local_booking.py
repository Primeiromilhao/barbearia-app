import json, sqlite3, tempfile
from pathlib import Path
from datetime import datetime

class BookingStore:
    def __init__(self,path):
        self.cx=sqlite3.connect(path); self.cx.row_factory=sqlite3.Row
        self.cx.executescript("""CREATE TABLE clients(id INTEGER PRIMARY KEY,name TEXT,phone TEXT,created_at TEXT);CREATE TABLE services(id INTEGER PRIMARY KEY,name TEXT,duration INTEGER);CREATE TABLE appointments(id INTEGER PRIMARY KEY,client_id INTEGER,service_id INTEGER,date TEXT,time TEXT,status TEXT,created_at TEXT);CREATE UNIQUE INDEX ux_slot ON appointments(date,time) WHERE status IN ('confirmed','pending');""")
        self.cx.execute("INSERT INTO services(name,duration) VALUES('Corte',30)"); self.cx.commit()
    def client(self,n,p):
        r=self.cx.execute('SELECT id FROM clients WHERE phone=?',(p,)).fetchone()
        if r:return r[0]
        c=self.cx.execute('INSERT INTO clients VALUES(NULL,?,?,?)',(n,p,datetime.now().isoformat())).lastrowid; self.cx.commit(); return c
    def book(self,n,p,date,time):
        if self.cx.execute("SELECT 1 FROM appointments WHERE date=? AND time=? AND status IN ('confirmed','pending')",(date,time)).fetchone():return False
        c=self.client(n,p); s=self.cx.execute("SELECT id FROM services WHERE name='Corte'").fetchone()[0]
        self.cx.execute("INSERT INTO appointments VALUES(NULL,?,?,?,?,?,?)",(c,s,date,time,'confirmed',datetime.now().isoformat()));self.cx.commit();return True
    def cancel(self,aid):self.cx.execute("UPDATE appointments SET status='cancelled' WHERE id=?",(aid,));self.cx.commit()
    def slots(self):return self.cx.execute('SELECT * FROM appointments ORDER BY id').fetchall()

def run():
    with tempfile.TemporaryDirectory() as td:
        db=BookingStore(Path(td)/'test.db'); results=[]
        results.append(('cadastro_cliente',db.client('João','910000000')==1))
        results.append(('agendamento_confirmado',db.book('João','910000000','2026-10-05','15:00')))
        results.append(('confirmacao_salva',len(db.slots())==1 and db.slots()[0]['status']=='confirmed'))
        results.append(('bloqueio_horario_repetido',not db.book('Carlos','920000000','2026-10-05','15:00')))
        aid=db.slots()[0]['id']; db.cancel(aid)
        results.append(('cancelamento_libera_horario',db.slots()[0]['status']=='cancelled' and db.book('Carlos','920000000','2026-10-05','15:00')))
        aid2=db.slots()[-1]['id']; db.cancel(aid2); results.append(('remarcacao_libera_antigo',db.book('Carlos','920000000','2026-10-06','16:00')))
        results.append(('novo_horario_reservado',any(r['date']=='2026-10-06' and r['time']=='16:00' and r['status']=='confirmed' for r in db.slots())))
        db.cx.close()
        return results

if __name__=='__main__':
    r=run(); report={'status':'PASS' if all(ok for _,ok in r) else 'FAIL','tests':[{'name':n,'ok':ok} for n,ok in r]}; print(json.dumps(report,ensure_ascii=False,indent=2)); raise SystemExit(0 if report['status']=='PASS' else 1)
