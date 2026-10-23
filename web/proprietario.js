const API = "https://barbearia-api-w37o.onrender.com/api";
const $ = id => document.getElementById(id);
let csrfToken = null;

async function api(path, opt = {}) {
  const method = (opt.method || "GET").toUpperCase();
  const headers = { "Content-Type": "application/json", ...(opt.headers || {}) };
  if (method === "POST" && !["/owner/login", "/owner/challenge", "/owner/device/register"].includes(path)) {
    if (!csrfToken) {
      try {
        const csrfRes = await fetch(API + "/csrf", { credentials: "include" });
        if (csrfRes.ok) {
          const d = await csrfRes.json();
          csrfToken = d.csrf_token;
        }
      } catch (e) {}
    }
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
  }
  const r = await fetch(API + path, { ...opt, credentials: "include", headers });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "Erro");
  return d;
}

const DEVICE_KEY = "barbearia.owner.device.v1", DEVICE_ID_KEY = "barbearia.owner.device_id.v1";
let keyPair = null;

function b64u(bytes) {
  let s = "";
  for (const b of new Uint8Array(bytes)) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64uBytes(s) {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  const raw = atob(s);
  return Uint8Array.from(raw, c => c.charCodeAt(0));
}

function getDeviceId() {
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

async function loadKeyPair() {
  if (keyPair) return keyPair;
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("barbearia-owner-device", 1);
    req.onupgradeneeded = () => req.result.createObjectStore("keys");
    req.onerror = () => reject(req.error);
    req.onsuccess = () => {
      const db = req.result, get = db.transaction("keys", "readonly").objectStore("keys").get(DEVICE_KEY);
      get.onsuccess = async () => {
        if (get.result) {
          keyPair = get.result;
          return resolve(keyPair);
        }
        keyPair = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, false, ["sign", "verify"]);
        const tx = db.transaction("keys", "readwrite");
        tx.objectStore("keys").put(keyPair, DEVICE_KEY);
        tx.oncomplete = () => resolve(keyPair);
        tx.onerror = () => reject(tx.error);
      };
      get.onerror = () => reject(get.error);
    };
  });
}

async function publicJwk() {
  return crypto.subtle.exportKey("jwk", (await loadKeyPair()).publicKey);
}

async function signChallenge(challenge) {
  return b64u(await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, (await loadKeyPair()).privateKey, b64uBytes(challenge)));
}

async function authenticateOwner(phone, password) {
  const deviceId = getDeviceId();
  let challenge;
  try {
    ({ challenge } = await api("/owner/challenge", { method: "POST", body: JSON.stringify({ phone, device_id: deviceId }) }));
  } catch (e) {
    if (!password) throw new Error("Este dispositivo ainda não está ativado. Informe a senha de ativação.");
    await api("/owner/device/register", { method: "POST", body: JSON.stringify({ phone, password, device_id: deviceId, public_jwk: await publicJwk() }) });
    ({ challenge } = await api("/owner/challenge", { method: "POST", body: JSON.stringify({ phone, device_id: deviceId }) }));
  }
  return api("/owner/login", { method: "POST", body: JSON.stringify({ phone, device_id: deviceId, signature: await signChallenge(challenge) }) });
}

$("ownerEnter").onclick = async () => {
  const phone = $("ownerPhone").value.trim(), password = $("ownerPassword").value;
  const status = $("ownerStatus");
  if (!phone) {
    status.style.color = "#f87171";
    status.textContent = "Informe o telefone do estabelecimento cadastrado.";
    return;
  }
  status.style.color = "#d8aa50";
  status.textContent = "Validando autorização do dispositivo...";
  try {
    await authenticateOwner(phone, password);
    $("ownerPassword").value = "";
    $("ownerArea").hidden = false;
    status.style.color = "#4ade80";
    status.textContent = "Dispositivo autorizado com sucesso. Área privada ativa.";
    await render();
  } catch (e) {
    status.style.color = "#f87171";
    if (e.message && e.message.includes("Credencial inválida")) {
      status.textContent = "Credencial inválida: verifique o telefone e a senha de ativação fornecida pelo gestor da plataforma.";
    } else {
      status.textContent = e.message;
    }
  }
};

async function render() {
  try {
    const p = await api("/owner/appointments?status=pending&active_only=1");
    const c = await api("/owner/appointments?status=confirmed&active_only=1");
    const all = await api("/owner/appointments");
    const users = await api("/owner/clients");
    const payments = await api("/payments").catch(() => []);

    $("pending").innerHTML = p.length ? p.map(x => card(x, "pending")).join("") : "Nenhuma solicitação pendente.";
    $("confirmed").innerHTML = c.length ? c.map(x => card(x, "confirmed")).join("") : "Nenhum horário confirmado.";
    $("clients").innerHTML = users.length ? users.map(x => '<div class="appointment"><strong>' + esc(x.name) + '</strong><span>' + esc(x.phone) + ' · ' + x.appointments + ' agendamento(s)</span></div>').join("") : "Nenhum cliente.";
    
    // Payments list
    $("paymentsList").innerHTML = payments.length ? payments.map(x => {
      let actions = "";
      if (x.status === "pending_verification") {
        actions = `<div class="actions"><button class="gold" onclick="confirmPaymentAction(${x.id})">CONFIRMAR RECEBIMENTO</button></div>`;
      }
      return `<div class="appointment"><strong>Pagamento #${x.id} — €${x.amount} (${x.method.toUpperCase()})</strong><span>Status: ${x.status.toUpperCase()} · Ref: ${esc(x.reference || 'N/A')}</span>${actions}</div>`;
    }).join("") : "Nenhum pagamento registado.";

    $("historyOwner").innerHTML = all.filter(x => !["pending", "confirmed"].includes(x.status)).map(x =>
      '<div class="appointment"><strong>' + esc(x.client) + ' — ' + esc(x.service) + '</strong><span>' + x.date + ' · ' + x.time + ' · ' + x.status.toUpperCase() + (x.payment_status ? ' · Pagamento: ' + x.payment_status.toUpperCase() : '') + '</span></div>'
    ).join("") || "Sem histórico.";

    await loadOwnerChat();
  } catch (err) {
    console.error("Render error", err);
  }
}

function card(x, type) {
  let b = '<div class="appointment"><strong>' + esc(x.client) + ' — ' + esc(x.service) + '</strong><span>' + x.date + ' · ' + x.time + ' · ' + esc(x.phone) + '</span>';
  if (type === "pending") {
    b += '<div class="actions"><button class="gold" onclick="confirmA(' + x.id + ')">CONFIRMAR</button><button class="dark-btn" onclick="rejectA(' + x.id + ')">RECUSAR</button></div>';
  } else if (type === "confirmed") {
    b += `<div class="actions">
      <button class="gold" onclick="completeA(${x.id}, 'money')">Concluir (Dinheiro)</button>
      <button class="gold" onclick="completeA(${x.id}, 'mbway')">Concluir (MB WAY)</button>
      <button class="dark-btn" onclick="markNoShowAction(${x.id})">Registar Falta</button>
    </div>`;
  }
  return b + "</div>";
}

async function confirmA(id) {
  try {
    await api("/owner/appointments/" + id + "/confirm", { method: "POST" });
    await render();
  } catch (e) {
    alert(e.message);
  }
}

async function rejectA(id) {
  try {
    await api("/owner/appointments/" + id + "/reject", { method: "POST" });
    await render();
  } catch (e) {
    alert(e.message);
  }
}

async function completeA(id, method) {
  try {
    await api("/owner/appointments/" + id + "/complete", {
      method: "POST",
      body: JSON.stringify({ payment_method: method, payment_status: "paid" })
    });
    await render();
  } catch (e) {
    alert(e.message);
  }
}

async function markNoShowAction(id) {
  const reason = prompt("Justificação da falta (opcional):") || "Cliente não compareceu";
  try {
    await api("/owner/appointments/" + id + "/no_show", {
      method: "POST",
      body: JSON.stringify({ notes: reason })
    });
    await render();
  } catch (e) {
    alert(e.message);
  }
}

async function confirmPaymentAction(pid) {
  try {
    await api("/owner/payments/" + pid + "/confirm", { method: "POST" });
    alert("Pagamento confirmado com sucesso!");
    await render();
  } catch (e) {
    alert(e.message);
  }
}

async function loadOwnerChat() {
  const box = $("ownerChatBox");
  if (!box) return;
  try {
    const msgs = await api("/messages");
    box.replaceChildren();
    if (!msgs.length) {
      box.textContent = "Sem mensagens.";
      return;
    }
    msgs.forEach(m => {
      const d = document.createElement("div");
      d.className = "chat-msg " + (m.sender_type === "owner" ? "msg-out" : "msg-in");
      let content = "<strong>" + esc(m.sender_id) + ":</strong> " + esc(m.message);
      if (m.photo_id) {
        content += `<br><img src="${API}/photos/${m.photo_id}" style="max-width:180px;border-radius:6px;margin-top:4px" alt="Foto">`;
      }
      d.innerHTML = content;
      box.append(d);
    });
  } catch (e) {
    box.textContent = "Erro: " + e.message;
  }
}

if ($("ownerSendChatBtn")) {
  $("ownerSendChatBtn").onclick = async () => {
    const txt = $("ownerChatInput").value.trim();
    if (!txt) return alert("Escreva uma mensagem.");
    try {
      await api("/messages", {
        method: "POST",
        body: JSON.stringify({
          message: txt,
          recipient_type: "client",
          recipient_id: "all"
        })
      });
      $("ownerChatInput").value = "";
      await loadOwnerChat();
    } catch (e) {
      alert(e.message);
    }
  };
}

function esc(v) {
  return String(v ?? "").replace(/[&<>"]/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
}
