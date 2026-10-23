const API="https://barbearia-api-w37o.onrender.com/api";
let user=null,service=null,time="",rescheduleId=null,csrfToken=null;
const $=id=>document.getElementById(id);const screens=[...document.querySelectorAll(".screen")];
function show(n){if(n!=="register"&&n!=="welcome"&&!user)n="register";screens.forEach(x=>x.classList.toggle("active",x.dataset.screen===n));if(n==="home")renderHome();if(n==="service")loadServices();if(n==="datetime")renderTimes();if(n==="confirm")renderSummary();if(n==="history")loadHistory();if(n==="profile")$("profileData").textContent=user?user.name+" · "+user.phone:"";location.hash=n;}
async function ensureClientSession() {
  if (!user || !user.phone) return false;
  try {
    const me = await api("/client/me");
    if (me && me.authenticated && me.phone === user.phone) return true;
  } catch {}
  try {
    await api("/client/register", {
      method: "POST",
      body: JSON.stringify({ name: user.name || "Cliente", phone: user.phone })
    });
    csrfToken = null;
    return true;
  } catch {
    return false;
  }
}

async function api(path, opt = {}) {
  const method = (opt.method || "GET").toUpperCase();
  const headers = { "Content-Type": "application/json", ...(opt.headers || {}) };
  if (method === "POST" && !["/client/register", "/dev/login", "/owner/login", "/owner/challenge", "/owner/device/register"].includes(path)) {
    if (!csrfToken) {
      try {
        const csrfRes = await fetch(API + "/csrf", { credentials: "include" });
        if (csrfRes.ok) {
          const cd = await csrfRes.json();
          csrfToken = cd.csrf_token;
        }
      } catch {}
    }
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
  }
  const r = await fetch(API + path, { ...opt, credentials: "include", headers });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new Error(d.error || "Ocorreu um erro no processamento da solicitação.");
  }
  return d;
}

document.addEventListener("click", e => {
  const g = e.target.closest("[data-go]"), n = e.target.closest("[data-next]");
  if (g) { e.preventDefault(); show(g.dataset.go); }
  if (n) {
    if (n.dataset.next === "datetime" && !service) {
      alert("Por favor, selecione um serviço.");
      return;
    }
    if (n.dataset.next === "confirm" && !time) {
      alert("Por favor, selecione um horário.");
      return;
    }
    show(n.dataset.next);
  }
});

$("registerBtn").onclick = async () => {
  const name = $("regName").value.trim(), phone = $("regPhone").value.trim();
  if (!name || !phone) return alert("Informe nome e telefone.");
  try {
    user = await api("/client/register", { method: "POST", body: JSON.stringify({ name, phone }) });
    csrfToken = null;
    localStorage.setItem("barbearia_cliente", JSON.stringify(user));
    show("home");
  } catch (e) {
    alert(e.message);
  }
};

function renderHome() {
  $("hello").textContent = "Olá, " + user.name + "!";
  $("phoneLabel").textContent = user.phone;
}

async function loadServices() {
  const box = $("serviceCards");
  box.replaceChildren();
  const services = await api("/services");
  for (const item of services) {
    const label = document.createElement("label");
    label.className = "service";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "service";
    input.value = String(item.id);
    input.addEventListener("change", () => service = item);
    label.append(input, document.createTextNode(" " + item.name + " — €" + item.price + " · " + item.duration + " min"));
    box.append(label);
  }
}

function renderTimes() {
  const box = $("times");
  box.replaceChildren();
  ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"].forEach(t => {
    const b = document.createElement("button");
    b.className = "time" + (t === time ? " selected" : "");
    b.textContent = t;
    b.onclick = () => { time = t; renderTimes(); };
    box.append(b);
  });
}

function renderSummary() {
  $("summary").textContent = (rescheduleId ? "Reagendar: " : "Solicitação: ") + service.name + " · " + $("date").value + " · " + time;
  if ($("confirmFeedback")) $("confirmFeedback").innerHTML = "";
}

$("confirmBtn").onclick = async () => {
  const btn = $("confirmBtn");
  const fb = $("confirmFeedback");
  if (btn.disabled) return;

  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = "Enviando solicitação...";
  if (fb) fb.innerHTML = "";

  try {
    // Garantir sessão ativa antes do agendamento
    await ensureClientSession();

    if (rescheduleId) {
      await api("/appointments/" + rescheduleId + "/cancel", { method: "POST" });
      rescheduleId = null;
    }

    const a = await api("/appointments", {
      method: "POST",
      body: JSON.stringify({
        phone: user.phone,
        service_id: service.id,
        date: $("date").value,
        time
      })
    });

    if (a && a.status === "pending") {
      $("successTitle").textContent = "Solicitação enviada";
      $("successSummary").textContent = service.name + " · " + a.date + " · " + a.time;
      $("successText").textContent = "Status: PENDENTE. A barbearia tem até 48 horas para confirmar a disponibilidade.";
      show("success");
    } else {
      throw new Error("Não foi possível confirmar o registo do agendamento.");
    }
  } catch (e) {
    if (fb) {
      fb.innerHTML = `<div style="background:#271b1b;border:1px solid #7f1d1d;color:#fca5a5;padding:12px;border-radius:10px;font-size:14px;line-height:1.4">
        <strong>Atenção:</strong> ${esc(e.message)}
      </div>`;
    } else {
      alert(e.message);
    }
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
};
async function loadHistory(){
  const box=$("list");
  box.innerHTML="";
  const rows=await api("/appointments?phone="+encodeURIComponent(user.phone));
  if(!rows.length){box.textContent="Nenhum agendamento.";return}
  rows.forEach(x=>{
    const d=document.createElement("div");
    d.className="appointment";
    const payStatus = x.payment_status ? " · Pagamento: " + x.payment_status.toUpperCase() : "";
    d.innerHTML="<strong>"+x.service+"</strong><span>"+x.date+" · "+x.time+" · "+x.status.toUpperCase()+payStatus+"</span>";
    const q=document.createElement("div");
    q.className="actions";
    if(["pending","confirmed"].includes(x.status)){
      const c=document.createElement("button");
      c.className="dark-btn";
      c.textContent="Cancelar";
      c.onclick=async()=>{
        try {
          await api("/appointments/"+x.id+"/cancel",{method:"POST"});
          loadHistory();
        } catch(err) {
          alert(err.message);
        }
      };
      q.append(c);
    }
    if(x.status==="confirmed" && x.payment_status==="unpaid"){
      const payBtn=document.createElement("button");
      payBtn.className="gold";
      payBtn.textContent="Pagar MB WAY (€"+x.price+")";
      payBtn.onclick=async()=>{
        const ref=prompt("Instruções MB WAY:\nEnvie €"+x.price+" para a Barbearia.\nIndique aqui a referência do comprovativo:");
        if(!ref) return;
        try {
          await api("/payments",{
            method:"POST",
            body:JSON.stringify({appointment_id:x.id,amount:x.price,method:"mbway",reference:ref,notes:"Registado pelo cliente"})
          });
          alert("Pagamento enviado para verificação do estabelecimento!");
          loadHistory();
        } catch(err){alert(err.message);}
      };
      q.append(payBtn);
    }
    if(q.children.length) d.append(q);
    box.append(d);
  });
}

let pendingPhotoId = null;
async function loadChat(){
  const box = $("chatMessages");
  if(!box) return;
  box.innerHTML="Carregando...";
  try {
    const msgs = await api("/messages");
    box.replaceChildren();
    if(!msgs.length){box.textContent="Sem mensagens anteriores.";return;}
    msgs.forEach(m=>{
      const el = document.createElement("div");
      el.className = "chat-msg " + (m.sender_type==="client"?"msg-out":"msg-in");
      let content = "<strong>" + (m.sender_type==="client"?"Você":"Barbearia") + ":</strong> " + esc(m.message);
      if(m.photo_id){content += `<br><img src="${API}/photos/${m.photo_id}" style="max-width:200px;border-radius:8px;margin-top:6px" alt="Foto">`;}
      el.innerHTML=content;
      box.append(el);
    });
    box.scrollTop=box.scrollHeight;
  }catch(e){box.textContent="Erro no chat: "+e.message;}
}
if($("uploadPhotoBtn")){
  $("uploadPhotoBtn").onclick=async()=>{
    const file = $("chatPhotoInput")?.files[0];
    if(!file) return alert("Selecione um ficheiro de imagem.");
    const fd = new FormData();
    fd.append("file", file);
    $("photoStatus").textContent = "Carregando imagem...";
    try {
      const res = await fetch(API + "/photos/upload", {method:"POST", credentials:"include", body:fd});
      const d = await res.json();
      if(!res.ok) throw new Error(d.error || "Erro no upload");
      pendingPhotoId = d.id;
      $("photoStatus").textContent = "Imagem anexada: " + file.name;
    } catch(e){$("photoStatus").textContent = "Falha: " + e.message;}
  };
}
if($("sendMsgBtn")){
  $("sendMsgBtn").onclick=async()=>{
    const txt = $("chatTextInput").value.trim();
    if(!txt && !pendingPhotoId) return alert("Digite uma mensagem ou anexe uma imagem.");
    try {
      await api("/messages", {
        method:"POST",
        body:JSON.stringify({message:txt, recipient_type:"owner", recipient_id:"owner", photo_id:pendingPhotoId})
      });
      $("chatTextInput").value="";
      pendingPhotoId=null;
      if($("photoStatus")) $("photoStatus").textContent="";
      loadChat();
    } catch(e){alert(e.message);}
  };
}

let currentAppVersion = localStorage.getItem("barbearia_app_version") || "1.0.0";
async function checkAppVersion(){
  try {
    const d = await api("/version");
    if(d && d.version && d.version !== currentAppVersion){
      if($("pwaBanner")) $("pwaBanner").hidden = false;
      if($("pwaUpdateBtn")){
        $("pwaUpdateBtn").onclick = () => {
          if("serviceWorker" in navigator){
            navigator.serviceWorker.getRegistrations().then(regs => { for(let reg of regs) reg.update(); });
          }
          currentAppVersion = d.version;
          localStorage.setItem("barbearia_app_version", d.version);
          location.reload();
        };
      }
    }
  } catch(e){}
}
if("serviceWorker" in navigator){
  navigator.serviceWorker.register("service-worker.js").catch(()=>{});
}
function esc(v){
  return String(v??"").replace(/[&<>"]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m]));
}

$("date").value=new Date().toISOString().slice(0,10);
$("date").min=$("date").value;
try{user=JSON.parse(localStorage.getItem("barbearia_cliente")||"null")}catch{}
show(user?"home":"welcome");
if (user) {
  ensureClientSession();
}
checkAppVersion();

