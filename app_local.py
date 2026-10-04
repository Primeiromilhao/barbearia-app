import sqlite3, tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
DB = BASE / "barbearia.db"
SERVICES = [("Corte", 30), ("Barba", 20), ("Corte + Barba", 50)]
TIMES = ["09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00"]

class DB:
    def __init__(self, path=DB):
        self.path = path
        self.cx = sqlite3.connect(path)
        self.cx.row_factory = sqlite3.Row
        self.cx.execute("PRAGMA foreign_keys=ON")
        self.cx.executescript("""
        CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS services(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, duration INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS appointments(
          id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL, service_id INTEGER NOT NULL,
          date TEXT NOT NULL, time TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'confirmed',
          created_at TEXT NOT NULL, FOREIGN KEY(client_id) REFERENCES clients(id), FOREIGN KEY(service_id) REFERENCES services(id));
        CREATE UNIQUE INDEX IF NOT EXISTS ux_active_slot ON appointments(date,time) WHERE status IN ('confirmed','pending');
        """)
        for name,dur in SERVICES: self.cx.execute("INSERT OR IGNORE INTO services(name,duration) VALUES(?,?)",(name,dur))
        self.cx.commit()
    def client(self,name,phone):
        row=self.cx.execute("SELECT * FROM clients WHERE phone=?",(phone,)).fetchone() if phone else None
        if row: return row["id"]
        cur=self.cx.execute("INSERT INTO clients(name,phone,created_at) VALUES(?,?,?)",(name,phone,datetime.now().isoformat(timespec='seconds'))); self.cx.commit(); return cur.lastrowid
    def book(self,name,phone,service,date,time):
        if self.cx.execute("SELECT 1 FROM appointments WHERE date=? AND time=? AND status IN ('confirmed','pending')",(date,time)).fetchone():
            return False,"Este horário já está ocupado."
        cid=self.client(name,phone); sid=self.cx.execute("SELECT id FROM services WHERE name=?",(service,)).fetchone()["id"]
        self.cx.execute("INSERT INTO appointments(client_id,service_id,date,time,status,created_at) VALUES(?,?,?,?,?,?)",(cid,sid,date,time,'confirmed',datetime.now().isoformat(timespec='seconds'))); self.cx.commit()
        return True,"Agendamento confirmado!"
    def all_appointments(self):
        return self.cx.execute("""SELECT a.id,c.name,c.phone,s.name service,a.date,a.time,a.status FROM appointments a JOIN clients c ON c.id=a.client_id JOIN services s ON s.id=a.service_id ORDER BY a.date,a.time""").fetchall()
    def cancel(self,aid): self.cx.execute("UPDATE appointments SET status='cancelled' WHERE id=?",(aid,)); self.cx.commit()
    def close(self): self.cx.close()

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Barbearia • Agendamento"); self.geometry("1050x680"); self.minsize(900,600); self.db=DB(); self.style=ttk.Style(self); self._login()
        self.protocol("WM_DELETE_WINDOW",self._close)
    def _clear(self):
        for w in self.winfo_children(): w.destroy()
    def _login(self):
        self._clear(); box=ttk.Frame(self,padding=35); box.place(relx=.5,rely=.5,anchor='center')
        ttk.Label(box,text="BARBEARIA",font=("Segoe UI",26,"bold")).pack(pady=10); ttk.Label(box,text="Sistema local de agendamento",font=("Segoe UI",12)).pack(pady=(0,25))
        ttk.Button(box,text="ENTRAR COMO CLIENTE",command=self.client_view,width=30).pack(pady=6); ttk.Button(box,text="PAINEL DO PROPRIETÁRIO",command=self.owner_view,width=30).pack(pady=6)
        ttk.Label(box,text="Acesso demonstrativo local — sem dependência de internet",font=("Segoe UI",9)).pack(pady=18)
    def client_view(self):
        self._clear(); self.title("Barbearia • Cliente")
        head=ttk.Frame(self,padding=15); head.pack(fill='x'); ttk.Label(head,text="Olá! Agende seu horário",font=("Segoe UI",20,"bold")).pack(side='left'); ttk.Button(head,text="Painel inicial",command=self._login).pack(side='right')
        form=ttk.LabelFrame(self,text="Novo agendamento",padding=20); form.pack(fill='x',padx=25,pady=10)
        self.name=tk.StringVar(); self.phone=tk.StringVar(); self.service=tk.StringVar(value=SERVICES[0][0]); self.date=tk.StringVar(value=datetime.now().strftime('%Y-%m-%d')); self.time=tk.StringVar(value=TIMES[0])
        for i,(lab,var) in enumerate([("Nome",self.name),("Telefone",self.phone),("Data (AAAA-MM-DD)",self.date)]): ttk.Label(form,text=lab).grid(row=0,column=i*2,sticky='w',padx=5); ttk.Entry(form,textvariable=var,width=24).grid(row=1,column=i*2,sticky='ew',padx=5)
        ttk.Label(form,text="Serviço").grid(row=2,column=0,sticky='w',padx=5,pady=(15,0)); ttk.Combobox(form,textvariable=self.service,values=[x[0] for x in SERVICES],state='readonly',width=22).grid(row=3,column=0,padx=5)
        ttk.Label(form,text="Horário").grid(row=2,column=2,sticky='w',padx=5,pady=(15,0)); ttk.Combobox(form,textvariable=self.time,values=TIMES,state='readonly',width=22).grid(row=3,column=2,padx=5)
        ttk.Button(form,text="CONFIRMAR AGENDAMENTO",command=self.book,width=30).grid(row=3,column=4,padx=20)
        self.msg=ttk.Label(self,text="",font=("Segoe UI",12)); self.msg.pack(pady=15)
        box=ttk.LabelFrame(self,text="Agendamentos registrados",padding=10); box.pack(fill='both',expand=True,padx=25,pady=10)
        self.tree=ttk.Treeview(box,columns=('id','cliente','servico','data','hora','status'),show='headings');
        for c,t in zip(self.tree['columns'],['ID','Cliente','Serviço','Data','Hora','Status']): self.tree.heading(c,text=t); self.tree.column(c,width=130)
        self.tree.pack(fill='both',expand=True); self.refresh()
    def book(self):
        if not self.name.get().strip(): self.msg.config(text="Informe seu nome."); return
        ok,msg=self.db.book(self.name.get().strip(),self.phone.get().strip(),self.service.get(),self.date.get().strip(),self.time.get())
        self.msg.config(text=("✓ "+msg) if ok else ("⚠ "+msg)); self.refresh()
    def refresh(self):
        if not hasattr(self,'tree'): return
        for x in self.tree.get_children(): self.tree.delete(x)
        for r in self.db.all_appointments(): self.tree.insert('', 'end', values=(r['id'],r['name'],r['service'],r['date'],r['time'],r['status']))
    def owner_view(self):
        self._clear(); self.title("Barbearia • Painel do Proprietário")
        head=ttk.Frame(self,padding=15); head.pack(fill='x'); ttk.Label(head,text="PAINEL DO PROPRIETÁRIO",font=("Segoe UI",22,"bold")).pack(side='left'); ttk.Button(head,text="Voltar",command=self._login).pack(side='right')
        stats=ttk.Frame(self,padding=10); stats.pack(fill='x');
        rows=self.db.all_appointments(); active=[r for r in rows if r['status'] in ('confirmed','pending')]; clients=self.db.cx.execute("SELECT COUNT(*) n FROM clients").fetchone()['n']
        for title,val in [("Agendamentos",len(active)),("Clientes",clients),("Concluídos",sum(r['status']=='completed' for r in rows)),("Cancelados",sum(r['status']=='cancelled' for r in rows))]:
            f=ttk.LabelFrame(stats,text=title,padding=18); f.pack(side='left',fill='x',expand=True,padx=5); ttk.Label(f,text=str(val),font=("Segoe UI",22,"bold")).pack()
        body=ttk.LabelFrame(self,text="Agenda completa — todos os clientes",padding=10); body.pack(fill='both',expand=True,padx=25,pady=10)
        self.otree=ttk.Treeview(body,columns=('id','cliente','telefone','servico','data','hora','status'),show='headings')
        for c,t in zip(self.otree['columns'],['ID','Cliente','Telefone','Serviço','Data','Hora','Status']): self.otree.heading(c,text=t); self.otree.column(c,width=125)
        self.otree.pack(fill='both',expand=True); self.refresh_owner()
        actions=ttk.Frame(self,padding=10); actions.pack(fill='x'); ttk.Button(actions,text="Cancelar selecionado",command=self.cancel_selected).pack(side='left'); ttk.Button(actions,text="Atualizar",command=self.owner_view).pack(side='left',padx=8)
    def refresh_owner(self):
        for x in self.otree.get_children(): self.otree.delete(x)
        for r in self.db.all_appointments(): self.otree.insert('', 'end', iid=str(r['id']), values=(r['id'],r['name'],r['phone'] or '',r['service'],r['date'],r['time'],r['status']))
    def cancel_selected(self):
        sel=self.otree.selection()
        if sel: self.db.cancel(int(sel[0])); self.owner_view()
    def _close(self): self.db.close(); self.destroy()

if __name__=='__main__': App().mainloop()
