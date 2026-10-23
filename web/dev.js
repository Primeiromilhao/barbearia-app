const API = "https://barbearia-api-w37o.onrender.com/api/dev";
const $ = id => document.getElementById(id);

let devCsrfToken = null;
async function api(path, opt = {}) {
  const method = (opt.method || "GET").toUpperCase();
  const headers = { "Content-Type": "application/json", ...(opt.headers || {}) };
  if (method === "POST" && !["/login"].includes(path)) {
    if (!devCsrfToken) {
      try {
        const csrfRes = await fetch("https://barbearia-api-w37o.onrender.com/api/csrf", { credentials: "include" });
        if (csrfRes.ok) {
          const cd = await csrfRes.json();
          devCsrfToken = cd.csrf_token;
        }
      } catch {}
    }
    if (devCsrfToken) headers["X-CSRF-Token"] = devCsrfToken;
  }
  const r = await fetch(API + path, {
    credentials: "include",
    headers,
    ...opt
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "Erro");
  return d;
}

async function check() {
  try {
    const d = await api("/me");
    if (d.authenticated) {
      $("loginView").hidden = true;
      $("consoleView").hidden = false;
      loadAll();
    }
  } catch {}
}

$("loginBtn").onclick = async () => {
  try {
    await api("/login", {
      method: "POST",
      body: JSON.stringify({
        username: ($("devUsername") ? $("devUsername").value.trim() : ""),
        password: $("devPassword").value
      })
    });
    $("devPassword").value = "";
    $("loginView").hidden = true;
    $("consoleView").hidden = false;
    loadAll();
  } catch (e) {
    $("loginStatus").textContent = e.message;
  }
};

$("logoutBtn").onclick = async () => {
  await api("/logout", { method: "POST" });
  location.reload();
};

async function loadAll() {
  try {
    const d = await api("/dashboard");
    $("devContent").innerHTML = "<h2>Diagnóstico do Sistema</h2><pre>" + esc(JSON.stringify(d, null, 2)) + "</pre>";
  } catch (e) {
    $("devContent").textContent = e.message;
  }
}

async function showClients() {
  const d = await api("/clients");
  renderTable("Clientes", d, ["id", "name", "phone", "appointments"]);
}

async function showAppointments() {
  const d = await api("/appointments");
  renderTable("Todos os agendamentos", d, ["id", "client", "phone", "service", "date", "time", "status"]);
}

async function showNotifications() {
  const d = await api("/notifications");
  renderTable("Fila de notificações", d, ["id", "appointment_id", "channel", "status", "phone", "message"]);
}

async function showAudit() {
  const d = await api("/audit");
  renderTable("Auditoria", d, ["id", "actor_type", "action", "target_type", "target_id", "created_at"]);
}

async function showRepairMenu() {
  $("devContent").innerHTML = `
    <h2>Centro de Ferramentas de Reparação</h2>
    <p>Ações separadas com explicação, pré-visualização e verificação posterior:</p>
    <div class="menu-grid" style="margin-bottom:15px">
      <button onclick="runRepair('availability')"><b>⚡</b>Corrigir Disponibilidade</button>
      <button onclick="runRepair('duplicates')"><b>◫</b>Detectar Horários Duplicados</button>
      <button onclick="runRepair('pending')"><b>◷</b>Recuperar Pedidos 48h</button>
      <button onclick="runRepair('sync')"><b>⇄</b>Diagnosticar Sincronização</button>
      <button onclick="runRepair('images')"><b>🖼</b>Verificar Uploads de Fotos</button>
      <button onclick="runRepair('notifications')"><b>✉</b>Verificar Fila Mensagens</button>
      <button onclick="runRepair('integrity')"><b>✓</b>Integridade Base de Dados</button>
      <button onclick="loadRepairsHistory()"><b>▤</b>Histórico de Reparações</button>
    </div>
    <div id="repairOutput" class="summary">Selecione uma ferramenta acima para executar.</div>
  `;
}

async function runRepair(type) {
  const out = $("repairOutput");
  out.textContent = `Executando reparação '${type}'...`;
  try {
    const res = await api(`/repair/${type}`, { method: "POST" });
    out.innerHTML = `
      <h3 style="color:#4ade80">Resultado da Ação: ${type.toUpperCase()}</h3>
      <p><strong>Diagnóstico / Problema:</strong> ${esc(res.problem)}</p>
      <p><strong>Alterações Efetuadas:</strong> ${esc(res.changes)}</p>
      <p><strong>Verificação Posterior:</strong> ${esc(res.verification)}</p>
    `;
  } catch (e) {
    out.innerHTML = `<span style="color:#f87171">Erro: ${esc(e.message)}</span>`;
  }
}

async function loadRepairsHistory() {
  const out = $("repairOutput");
  out.textContent = "Carregando histórico...";
  try {
    const rows = await api("/repair/repairs");
    if (!rows.length) {
      out.textContent = "Nenhum registo de reparação anterior.";
      return;
    }
    out.innerHTML = `<h3>Histórico de Operações de Recuperação</h3>
      <table style="width:100%;font-size:12px">
        <thead><tr><th>Tipo</th><th>Diagnóstico</th><th>Alterações</th><th>Resultado</th></tr></thead>
        <tbody>
          ${rows.map(r => `<tr><td><b>${esc(r.repair_type)}</b></td><td>${esc(r.problem_description)}</td><td>${esc(r.changes_applied)}</td><td>${esc(r.verification_result)}</td></tr>`).join("")}
        </tbody>
      </table>`;
  } catch (e) {
    out.textContent = "Erro: " + e.message;
  }
}

async function showAppVersionForm() {
  $("devContent").innerHTML = `
    <h2>Publicar Nova Versão da PWA</h2>
    <p>Ao publicar uma nova versão, todos os clientes e proprietários receberão o aviso de atualização.</p>
    <div style="max-width:400px">
      <label>Número da Versão (ex: 1.1.0)<input id="newVersionNumber" placeholder="1.1.0"></label>
      <label>Changelog / Notas de Atualização<input id="newVersionLog" placeholder="Melhorias de desempenho e novas regras"></label>
      <button class="gold full" onclick="submitAppVersion()">Publicar Versão</button>
      <p id="publishVersionStatus" style="margin-top:10px"></p>
    </div>
  `;
}

async function submitAppVersion() {
  const version = $("newVersionNumber").value.trim();
  const changelog = $("newVersionLog").value.trim();
  const status = $("publishVersionStatus");
  if (!version) return status.textContent = "Número da versão obrigatório.";
  status.textContent = "Publicando...";
  try {
    const res = await api("/version", {
      method: "POST",
      body: JSON.stringify({ version, changelog })
    });
    status.style.color = "#4ade80";
    status.textContent = `Versão ${res.version} publicada com sucesso!`;
  } catch (e) {
    status.style.color = "#f87171";
    status.textContent = "Erro: " + e.message;
  }
}

async function showRecoveryStaged() {
  $("devContent").innerHTML = "Carregando pré-visualização de impacto...";
  try {
    const prev = await api("/recovery/preview", { method: "POST" });
    $("devContent").innerHTML = `
      <h2>Recuperação do Sistema em Etapas (Ambiente de Produção)</h2>
      <p style="color:#d8aa50"><strong>Garantia de Segurança:</strong> ${esc(prev.guarantee)}</p>
      <div class="summary">
        <h4>Impacto Previsto:</h4>
        <ul>
          <li>Agendamentos Pendentes para análise/expiração: ${prev.impact_preview.pending_appointments_to_check}</li>
          <li>Agendamentos Confirmados (Protegidos): ${prev.impact_preview.confirmed_appointments_protected}</li>
          <li>Clientes Registados (Protegidos): ${prev.impact_preview.clients_protected}</li>
          <li>Histórico de Pagamentos (Protegido): ${prev.impact_preview.payments_protected}</li>
        </ul>
      </div>
      <button class="gold full" onclick="executeRecoveryStaged()">Executar Recuperação Segura</button>
      <div id="recoveryStatus" style="margin-top:10px"></div>
    `;
  } catch (e) {
    $("devContent").textContent = "Erro: " + e.message;
  }
}

async function executeRecoveryStaged() {
  if (!confirm("Confirmar execução da recuperação em etapas? Registos reais de clientes e pagamentos permanecerão intocados.")) return;
  const status = $("recoveryStatus");
  status.textContent = "Executando recuperação em etapas...";
  try {
    const res = await api("/recovery/execute", {
      method: "POST",
      body: JSON.stringify({ confirm: "CONFIRM_STAGED_RECOVERY" })
    });
    status.style.color = "#4ade80";
    status.textContent = "Recuperação concluída! " + res.message;
  } catch (e) {
    status.style.color = "#f87171";
    status.textContent = "Erro: " + e.message;
  }
}

async function resetTest() {
  if (!confirm("RESETAR DADOS DE TESTE? Esta ação é destrutiva para o ambiente de testes.")) return;
  try {
    const d = await api("/test/reset", { method: "POST", body: JSON.stringify({ confirm: "RESET_TEST_ENVIRONMENT" }) });
    $("devContent").innerHTML = "<h2>Teste resetado</h2><pre>" + esc(JSON.stringify(d, null, 2)) + "</pre>";
  } catch (e) {
    alert(e.message);
  }
}

async function showCreateOwnerForm() {
  $("devContent").innerHTML = `<h2>Cadastrar Novo Proprietário (Barbearia)</h2>
    <p>Crie o acesso de um novo lojista/barbeiro para ativar o seu terminal operacional.</p>
    <div style="max-width:400px">
      <label>Telefone do Proprietário<input id="newOwnerPhone" type="tel" placeholder="ex: +351912345678"></label>
      <label>Senha Inicial (mínimo 12 caracteres)<input id="newOwnerPassword" type="password" placeholder="Senha forte"></label>
      <label>Máximo de Dispositivos<input id="newOwnerDevices" type="number" value="1" min="1" max="20"></label>
      <button class="gold full" onclick="submitCreateOwner()">Criar Barbearia / Proprietário</button>
      <p id="createOwnerStatus" style="margin-top:10px"></p>
    </div>`;
}

async function submitCreateOwner() {
  const phone = $("newOwnerPhone").value.trim();
  const password = $("newOwnerPassword").value;
  const max_devices = parseInt($("newOwnerDevices").value, 10) || 1;
  const status = $("createOwnerStatus");
  if (!phone || password.length < 12) {
    status.style.color = "#f87171";
    status.textContent = "Erro: Telefone e senha com mínimo de 12 caracteres são obrigatórios.";
    return;
  }
  status.style.color = "#d8aa50";
  status.textContent = "Enviando cadastro...";
  try {
    const res = await api("/owners", {
      method: "POST",
      body: JSON.stringify({ phone, password, max_devices })
    });
    status.style.color = "#4ade80";
    status.innerHTML = `Proprietário criado com sucesso!<br>ID: ${res.id} | Telefone: ${esc(res.phone)} | Dispositivos: ${res.max_devices}`;
  } catch (e) {
    status.style.color = "#f87171";
    status.textContent = "Erro: " + e.message;
  }
}

function renderTable(title, rows, cols) {
  $("devContent").innerHTML = "<h2>" + title + "</h2>" + (rows.length ? '<div style="overflow:auto"><table><thead><tr>' + cols.map(c => "<th>" + c + "</th>").join("") + "</tr></thead><tbody>" + rows.map(r => "<tr>" + cols.map(c => "<td>" + esc(r[c]) + "</td>").join("") + "</tr>").join("") + "</tbody></table></div>" : "<p>Nenhum registro.</p>");
}

function esc(v) {
  return String(v ?? "").replace(/[&<>"]/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));
}

check();