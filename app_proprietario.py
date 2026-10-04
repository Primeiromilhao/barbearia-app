import tkinter as tk
from tkinter import ttk
import shared_db

APP_TITLE = "Barbearia • App Proprietário"

class OwnerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE); self.geometry("900x600")
        self.configure(padx=18,pady=18)
        tk.Label(self,text="Barbearia",font=("Segoe UI",22,"bold")).pack(anchor="w")
        tk.Label(self,text="Área do Proprietário",font=("Segoe UI",14)).pack(anchor="w",pady=(0,12))
        self.stats=tk.StringVar(); tk.Label(self,textvariable=self.stats,font=("Segoe UI",11)).pack(anchor="w")
        cols=("id","cliente","telefone","serviço","data","hora","status")
        self.tree=ttk.Treeview(self,columns=cols,show="headings")
        for c in cols:self.tree.heading(c,text=c.title())
        self.tree.pack(fill="both",expand=True,pady=12)
        bar=tk.Frame(self);bar.pack(fill="x")
        tk.Button(bar,text="Atualizar",command=self.refresh).pack(side="left")
        tk.Button(bar,text="Concluir",command=self.complete).pack(side="left",padx=6)
        tk.Button(bar,text="Cancelar",command=self.cancel).pack(side="left")
        self.refresh(); self.after(2500,self.loop)

    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        rows=shared_db.appointments()
        for r in rows:self.tree.insert("","end",values=r)
        clients=len({r[2] for r in rows}); done=sum(r[6]=="completed" for r in rows); canc=sum(r[6]=="cancelled" for r in rows)
        self.stats.set(f"Agendamentos: {len(rows)}   Clientes: {clients}   Concluídos: {done}   Cancelados: {canc}")

    def selected_id(self):
        s=self.tree.selection()
        return int(self.tree.item(s[0],"values")[0]) if s else None

    def complete(self):
        i=self.selected_id()
        if i: shared_db.complete(i); self.refresh()

    def cancel(self):
        i=self.selected_id()
        if i: shared_db.cancel(i); self.refresh()

    def loop(self):
        self.refresh(); self.after(2500,self.loop)

if __name__=="__main__": OwnerApp().mainloop()
