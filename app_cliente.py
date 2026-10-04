import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import shared_db

APP_TITLE = "Barbearia • App Cliente"

class ClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE); self.geometry("520x650")
        self.configure(padx=18,pady=18)
        tk.Label(self,text="Barbearia",font=("Segoe UI",22,"bold")).pack(anchor="w")
        tk.Label(self,text="Área do Cliente",font=("Segoe UI",14)).pack(anchor="w",pady=(0,18))
        self.name=tk.StringVar(); self.phone=tk.StringVar(); self.service=tk.StringVar(value=shared_db.SERVICES[0][0])
        self.day=tk.StringVar(value=date.today().isoformat()); self.hour=tk.StringVar(value=shared_db.TIMES[0])
        for label,var in [("Nome",self.name),("Telefone",self.phone),("Data (AAAA-MM-DD)",self.day)]:
            tk.Label(self,text=label).pack(anchor="w"); tk.Entry(self,textvariable=var,font=("Segoe UI",12)).pack(fill="x",pady=(0,10))
        tk.Label(self,text="Serviço").pack(anchor="w")
        ttk.Combobox(self,textvariable=self.service,values=[x[0] for x in shared_db.SERVICES],state="readonly").pack(fill="x",pady=(0,10))
        tk.Label(self,text="Horário").pack(anchor="w")
        ttk.Combobox(self,textvariable=self.hour,values=shared_db.TIMES,state="readonly").pack(fill="x",pady=(0,14))
        tk.Button(self,text="CONFIRMAR AGENDAMENTO",command=self.book,font=("Segoe UI",12,"bold"),height=2).pack(fill="x")
        tk.Button(self,text="Meus agendamentos",command=self.refresh).pack(fill="x",pady=8)
        self.listbox=tk.Listbox(self,height=10,font=("Segoe UI",11)); self.listbox.pack(fill="both",expand=True)
        tk.Button(self,text="Cancelar selecionado",command=self.cancel).pack(fill="x",pady=8)

    def book(self):
        ok,msg=shared_db.book(self.name.get(),self.phone.get(),self.service.get(),self.day.get(),self.hour.get())
        (messagebox.showinfo if ok else messagebox.showerror)("Agendamento",msg)
        if ok:self.refresh()

    def refresh(self):
        self.listbox.delete(0,"end")
        for r in shared_db.appointments(self.phone.get().strip()):
            self.listbox.insert("end",f"#{r[0]} | {r[3]} {r[4]} | {r[6]}")

    def cancel(self):
        if not self.phone.get().strip(): return
        rows=shared_db.appointments(self.phone.get().strip())
        if not rows or self.listbox.curselection()==(): return
        shared_db.cancel(rows[self.listbox.curselection()[0]][0]); self.refresh()

if __name__=="__main__": ClientApp().mainloop()
