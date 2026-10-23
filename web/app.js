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

function showNotice(elId, msg, isSuccess = false) {
  const el = $(elId);
  if (!el) return;
  const bg = isSuccess ? "#064e3b" : "#451a1a";
  const border = isSuccess ? "#059669" : "#b91c1c";
  const color = isSuccess ? "#6ee7b7" : "#fca5a5";
  el.innerHTML = `<div style="background:${bg};border:1px solid ${border};color:${color};padding:10px 14px;border-radius:10px;font-size:14px;line-height:1.4;margin-bottom:10px">
    ${esc(msg)}
  </div>`;
}

function clearNotice(elId) {
  const el = $(elId);
  if (el) el.innerHTML = "";
}

document.addEventListener("click", e => {
  const g = e.target.closest("[data-go]"), n = e.target.closest("[data-next]");
  if (g) { e.preventDefault(); show(g.dataset.go); }
  if (n) {
    if (n.dataset.next === "datetime" && !service) {
      showNotice("serviceFeedback", "Por favor, selecione um serviço para continuar.");
      return;
    }
    clearNotice("serviceFeedback");
    if (n.dataset.next === "confirm" && !time) {
      showNotice("datetimeFeedback", "Por favor, selecione um horário para continuar.");
      return;
    }
    clearNotice("datetimeFeedback");
    show(n.dataset.next);
  }
});

let pendingPhone = "";
let pendingName = "";

$("registerBtn").onclick = async () => {
  clearNotice("regFeedback");
  const name = $("regName").value.trim(), phone = $("regPhone").value.trim();
  if (!name || !phone) {
    showNotice("regFeedback", "Não foi possível concluir o cadastro. Informe o seu nome e telefone.");
    return;
  }

  pendingName = name;
  pendingPhone = phone;
  $("registerBtn").disabled = true;
  $("registerBtn").textContent = "Enviando código...";
  try {
    const res = await api("/client/phone/send-code", {
      method: "POST",
      body: JSON.stringify({ phone })
    });
    if ($("verifyPhoneDisplay")) $("verifyPhoneDisplay").textContent = res.phone || phone;
    showNotice("verifyFeedback", "Código de verificação enviado por SMS. Verifique o seu telemóvel.", true);
    if (res.dev_code_test && $("verifyCodeInput")) {
      $("verifyCodeInput").value = res.dev_code_test;
    }
    show("verifyPhone");
  } catch (err) {
    try {
      user = await api("/client/register", { method: "POST", body: JSON.stringify({ name, phone }) });
      csrfToken = null;
      localStorage.setItem("barbearia_cliente", JSON.stringify(user));
      show("home");
    } catch (e2) {
      showNotice("regFeedback", e2.message || "Não foi possível concluir o cadastro. Verifique os dados e tente novamente.");
    }
  } finally {
    $("registerBtn").disabled = false;
    $("registerBtn").textContent = "Continuar";
  }
};

if ($("verifySubmitBtn")) {
  $("verifySubmitBtn").onclick = async () => {
    clearNotice("verifyFeedback");
    const code = $("verifyCodeInput").value.trim();
    if (!code || code.length < 4) {
      showNotice("verifyFeedback", "Informe o código de 6 dígitos recebido por SMS.");
      return;
    }
    $("verifySubmitBtn").disabled = true;
    $("verifySubmitBtn").textContent = "Verificando...";
    try {
      await api("/client/phone/verify-code", {
        method: "POST",
        body: JSON.stringify({ phone: pendingPhone, code })
      });
      user = await api("/client/register", {
        method: "POST",
        body: JSON.stringify({ name: pendingName, phone: pendingPhone })
      });
      csrfToken = null;
      localStorage.setItem("barbearia_cliente", JSON.stringify(user));
      showNotice("verifyFeedback", "Telefone confirmado com sucesso!", true);
      setTimeout(() => show("home"), 500);
    } catch (err) {
      showNotice("verifyFeedback", err.message || "Código incorreto ou expirado. Tente novamente.");
    } finally {
      $("verifySubmitBtn").disabled = false;
      $("verifySubmitBtn").textContent = "Confirmar Telefone";
    }
  };
}

if ($("resendCodeBtn")) {
  $("resendCodeBtn").onclick = async () => {
    clearNotice("verifyFeedback");
    $("resendCodeBtn").disabled = true;
    try {
      const res = await api("/client/phone/send-code", {
        method: "POST",
        body: JSON.stringify({ phone: pendingPhone })
      });
      showNotice("verifyFeedback", "Novo código enviado com sucesso.", true);
      if (res.dev_code_test && $("verifyCodeInput")) {
        $("verifyCodeInput").value = res.dev_code_test;
      }
    } catch (err) {
      showNotice("verifyFeedback", err.message || "Não foi possível reenviar o código neste momento.");
    } finally {
      $("resendCodeBtn").disabled = false;
    }
  };
}

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
    }
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
};
async function loadHistory(){
  const box=$("list");
  box.innerHTML="";
  clearNotice("historyFeedback");
  const rows=await api("/appointments?phone="+encodeURIComponent(user.phone));
  if(!rows.length){box.textContent="Nenhum agendamento.";return}
  rows.forEach(x=>{
    const d=document.createElement("div");
    d.className="appointment";
    const payStatus = x.payment_status ? " · Pagamento: " + x.payment_status.toUpperCase() : "";
    d.innerHTML="<strong>"+esc(x.service)+"</strong><span>"+x.date+" · "+x.time+" · "+x.status.toUpperCase()+payStatus+"</span>";
    const q=document.createElement("div");
    q.className="actions";
    if(["pending","confirmed"].includes(x.status)){
      const c=document.createElement("button");
      c.className="dark-btn";
      c.textContent="Cancelar";
      c.onclick=async()=>{
        try {
          await api("/appointments/"+x.id+"/cancel",{method:"POST"});
          showNotice("historyFeedback", "Agendamento cancelado com sucesso.", true);
          loadHistory();
        } catch(err) {
          showNotice("historyFeedback", err.message || "Não foi possível cancelar o agendamento.");
        }
      };
      q.append(c);
    }
    if(x.status==="confirmed" && x.payment_status==="unpaid"){
      const payBtn=document.createElement("button");
      payBtn.className="gold";
      payBtn.textContent="Pagar MB WAY (€"+x.price+")";
      payBtn.onclick=async()=>{
        const ref = "MBW-" + Date.now();
        try {
          await api("/payments",{
            method:"POST",
            body:JSON.stringify({appointment_id:x.id,amount:x.price,method:"mbway",reference:ref,notes:"Registado pelo cliente"})
          });
          showNotice("historyFeedback", "Pagamento registado com sucesso! Aguarda confirmação do estabelecimento.", true);
          loadHistory();
        } catch(err){
          showNotice("historyFeedback", err.message || "Não foi possível registar o pagamento.");
        }
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
      let timeLabel = "";
      if(m.created_at) {
        try {
          const d = new Date(m.created_at * 1000);
          timeLabel = ` <small style="opacity:0.75;font-size:11px">(${d.toLocaleTimeString("pt-PT", {hour:"2-digit",minute:"2-digit"})})</small>`;
        } catch {}
      }
      let content = "<strong>" + (m.sender_type==="client"?"Você":"Barbearia") + ":</strong> " + esc(m.message) + timeLabel;
      if(m.photo_id){content += `<br><img src="${API}/photos/${m.photo_id}" style="max-width:200px;border-radius:8px;margin-top:6px" alt="Foto">`;}
      el.innerHTML=content;
      box.append(el);
    });
    box.scrollTop=box.scrollHeight;
  }catch(e){box.textContent="Não foi possível carregar as mensagens: "+e.message;}
}
if($("uploadPhotoBtn")){
  $("uploadPhotoBtn").onclick=async()=>{
    clearNotice("chatFeedback");
    const file = $("chatPhotoInput")?.files[0];
    if(!file) {
      showNotice("chatFeedback", "Por favor, selecione um ficheiro de imagem.");
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    $("photoStatus").textContent = "Carregando imagem...";
    try {
      const res = await fetch(API + "/photos/upload", {method:"POST", credentials:"include", body:fd});
      const d = await res.json();
      if(!res.ok) throw new Error(d.error || "Erro no upload");
      pendingPhotoId = d.id;
      $("photoStatus").textContent = "Imagem anexada: " + file.name;
    } catch(e){
      $("photoStatus").textContent = "Falha: " + (e.message || "Não foi possível carregar a imagem.");
    }
  };
}
if($("sendMsgBtn")){
  $("sendMsgBtn").onclick=async()=>{
    clearNotice("chatFeedback");
    const txt = $("chatTextInput").value.trim();
    if(!txt && !pendingPhotoId) {
      showNotice("chatFeedback", "Digite uma mensagem ou anexe uma imagem para enviar.");
      return;
    }
    $("sendMsgBtn").disabled = true;
    try {
      await api("/messages", {
        method:"POST",
        body:JSON.stringify({message:txt, recipient_type:"owner", recipient_id:"owner", photo_id:pendingPhotoId})
      });
      $("chatTextInput").value="";
      pendingPhotoId=null;
      if($("photoStatus")) $("photoStatus").textContent="";
      showNotice("chatFeedback", "Mensagem enviada com sucesso.", true);
      loadChat();
    } catch(e){
      showNotice("chatFeedback", e.message || "Não foi possível enviar a mensagem. Tente novamente.");
    } finally {
      $("sendMsgBtn").disabled = false;
    }
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

