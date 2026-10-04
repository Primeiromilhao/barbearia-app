import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import shared_db

APP_TITLE = "Barbearia • App Cliente"

class ClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE); self.geometry("560x720")
        self.configure(padx=18,pady=18)
        self.name=tk.StringVar(); self.phone=tk.StringVar()
        self.service=tk.StringVar(value=shared_db.SERVICES[0][0])
        self.day=tk.StringVar(value=date.today().isoformat())
        self.hour=tk.StringVar(value=shared_db.TIMES[0])
        tk.Label(self,text="Barbearia",font=("Segoe UI",22,"bold")).pack(anchor="w")
        tk.Label(self,text="Área do Cliente",font=("Segoe UI",14)).pack(anchor="w",pady=(0,14))
        box=tk.LabelFrame(self,text="1. Cadastro / Entrada",padx=10,pady=10); box.pack(fill="x")
        for label,var in [("Nome",self.name),("Telefone",self.phone)]:
            tk.Label(box,text=label).pack(anchor="w"); tk.Entry(box,textvariable=var,font=("Segoe UI",12)).pack(fill="x",pady=(0,8))
        tk.Button(box,text="ENTRAR / CADASTRAR",command=self.enter,font=("Segoe UI",11,"bold")).pack(fill="x")
        self.status=tk.StringVar(value="Informe nome e telefone para entrar.")
        tk.Label(self,textvariable=self.status,anchor="w").pack(fill="x",pady=8)
        box2=tk.LabelFrame(self,text="2. Ambiente do Cliente",padx=10,pady=10); box2.pack(fill="both",expand=True)
        tk.Label(box2,text="Serviço").pack(anchor="w")
        ttk.Combobox(box2,textvariable=self.service,values=[x[0] for x in shared_db.SERVICES],state="readonly").pack(fill="x",pady=(0,8))
        tk.Label(box2,text="Data").pack(anchor="w"); tk.Entry(box2,textvariable=self.day).pack(fill="x",pady=(0,8))
        tk.Label(box2,text="Horário").pack(anchor="w")
        ttk.Combobox(box2,textvariable=self.hour,values=shared_db.TIMES,state="readonly").pack(fill="x",pady=(0,10))
        tk.Button(box2,text="CONFIRMAR AGENDAMENTO",command=self.book,font=("Segoe UI",11,"bold"),height=2).pack(fill="x")
        tk.Button(box2,text="MEUS AGENDAMENTOS",command=self.refresh).pack(fill="x",pady=6)
        tk.Button(box2,text="CANCELAR SELECIONADO",command=self.cancel).pack(fill="x")
        self.listbox=tk.Listbox(box2,height=8,font=("Segoe UI",10)); self.listbox.pack(fill="both",expand=True,pady=8)
        tk.Label(box2,text="Após confirmar, WhatsApp e SMS ficam registrados como mensagens pendentes para envio pelo canal configurado.",wraplength=480,justify="left").pack(anchor="w")
        self.entered=False

    def enter(self):
        ok,msg,row=shared_db.register_client(self.name.get(),self.phone.get())
        self.entered=ok
        self.status.set(msg if ok else "Erro: "+msg)
        if ok: self.refresh()

    def book(self):
        if not self.entered:
            self.enter(); 
            if not self.entered: return
        ok,msg,_=shared_db.book(self.name.get(),self.phone.get(),self.service.get(),self.day.get(),self.hour.get())
        (messagebox.showinfo if ok else messagebox.showerror)("Agendamento",msg)
        if ok: self.refresh()

    def refresh(self):
        if not self.phone.get().strip(): return
        self.listbox.delete(0,"end")
        for r in shared_db.appointments(self.phone.get().strip()):
            self.listbox.insert("end",f"#{r[0]} | {r[3]} {r[4]} | {r[6]}")

    def cancel(self):
        rows=shared_db.appointments(self.phone.get().strip())
        if not rows or self.listbox.curselection()==(): return
        shared_db.cancel(rows[self.listbox.curselection()[0]][0]); self.refresh()

if __name__=="__main__": ClientApp().mainloop()
