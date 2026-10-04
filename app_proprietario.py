import tkinter as tk
from tkinter import ttk, messagebox
import shared_db

APP_TITLE = "Barbearia • App Proprietário"

class OwnerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE); self.geometry("1000x680"); self.configure(padx=18,pady=18)
        self.phone=tk.StringVar()
        tk.Label(self,text="Barbearia",font=("Segoe UI",22,"bold")).pack(anchor="w")
        tk.Label(self,text="Área do Proprietário",font=("Segoe UI",14)).pack(anchor="w")
        top=tk.Frame(self); top.pack(fill="x",pady=10)
        tk.Label(top,text="Telefone do proprietário:").pack(side="left")
        tk.Entry(top,textvariable=self.phone,width=22).pack(side="left",padx=6)
        tk.Button(top,text="CADASTRAR / ENTRAR",command=self.enter).pack(side="left")
        self.status=tk.StringVar(value="Entre com o telefone do proprietário.")
        tk.Label(self,textvariable=self.status).pack(anchor="w")
        self.stats=tk.StringVar(); tk.Label(self,textvariable=self.stats,font=("Segoe UI",11,"bold")).pack(anchor="w",pady=6)
        cols=("id","cliente","telefone","serviço","data","hora","status")
        self.tree=ttk.Treeview(self,columns=cols,show="headings")
        for c in cols:self.tree.heading(c,text=c.title())
        self.tree.pack(fill="both",expand=True,pady=8)
        bar=tk.Frame(self);bar.pack(fill="x")
        for text,cmd in [("Atualizar",self.refresh),("Concluir",self.complete),("Cancelar",self.cancel)]:
            tk.Button(bar,text=text,command=cmd).pack(side="left",padx=3)
        tk.Button(bar,text="Ver clientes cadastrados",command=self.show_clients).pack(side="left",padx=8)
        self.refresh(); self.after(2500,self.loop)

    def enter(self):
        phone=shared_db.normalize_phone(self.phone.get())
        if not phone: self.status.set("Telefone obrigatório."); return
        self.status.set("Proprietário identificado pelo telefone: "+phone)

    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        rows=shared_db.appointments()
        for r in rows:self.tree.insert("","end",values=r)
        clients=len(shared_db.clients()); done=sum(r[6]=="completed" for r in rows); canc=sum(r[6]=="cancelled" for r in rows)
        self.stats.set(f"Agendamentos: {len(rows)}   Clientes cadastrados: {clients}   Concluídos: {done}   Cancelados: {canc}")

    def selected_id(self):
        s=self.tree.selection()
        return int(self.tree.item(s[0],"values")[0]) if s else None

    def complete(self):
        i=self.selected_id()
        if i: shared_db.complete(i); self.refresh()

    def cancel(self):
        i=self.selected_id()
        if i: shared_db.cancel(i); self.refresh()

    def show_clients(self):
        rows=shared_db.clients()
        w=tk.Toplevel(self); w.title("Clientes cadastrados"); w.geometry("600x420")
        t=ttk.Treeview(w,columns=("id","name","phone"),show="headings")
        for c in ("id","name","phone"): t.heading(c,text=c.title())
        for r in rows:t.insert("","end",values=r)
        t.pack(fill="both",expand=True,padx=12,pady=12)

    def loop(self):
        self.refresh(); self.after(2500,self.loop)

if __name__=="__main__": OwnerApp().mainloop()
