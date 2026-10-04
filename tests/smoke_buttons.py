import sys
sys.path.insert(0,r"F:\Fábrica\Teste\Barbearia")
import tkinter as tk
import app_cliente, app_proprietario, shared_db
from datetime import date
app_cliente.messagebox.showinfo=lambda *a,**k: None
app_cliente.messagebox.showerror=lambda *a,**k: None
c=app_cliente.ClientApp(); c.update()
c.name.set("GUI Cliente QA"); c.phone.set("999900001"); c.enter()
assert c.entered
c.service.set(shared_db.SERVICES[0][0]); c.day.set("2039-01-02"); c.hour.set("10:00"); c.book()
assert len(shared_db.appointments("999900001"))==1
o=app_proprietario.OwnerApp(); o.update(); o.refresh()
assert len(o.tree.get_children())>=1
o.tree.selection_set(o.tree.get_children()[-1]); o.complete(); o.refresh()
assert any(v[-1]=="completed" for v in [o.tree.item(i,"values") for i in o.tree.get_children()])
o.destroy(); c.destroy()
# cleanup
for r in shared_db.appointments("999900001"): shared_db.cancel(r[0])
print("DESKTOP_BUTTON_SMOKE=PASS")