import os, json, time
import pytest
from backend import app, init_db, db, get_dev_user, get_dev_secret, get_owner_secret, hash_password

@pytest.fixture(autouse=True)
def test_setup(monkeypatch, tmp_path):
    test_db = tmp_path / "test_suite.db"
    monkeypatch.setenv("BARBEARIA_DB_PATH", str(test_db))
    monkeypatch.setenv("BARBEARIA_DEV_USERNAME", "DBAONLINE")
    monkeypatch.setenv("BARBEARIA_DEV_PASSWORD", "SecretDev2026!")
    monkeypatch.setenv("BARBEARIA_OWNER_PASSWORD", "SecretOwner2026!")
    monkeypatch.setenv("BARBEARIA_TEST_MODE", "1")
    import backend
    backend.DB = test_db
    init_db()
    with db() as c:
        # Cria proprietário de teste
        c.execute("INSERT OR REPLACE INTO owners(phone,password_hash,active,max_devices,created_at) VALUES(?,?,1,5,?)",
                  ("+351920000001", hash_password("SecretOwner2026!"), time.time()))
        # Cria clientes de teste
        c.execute("INSERT OR REPLACE INTO clients(id,name,phone,created_at,phone_verified) VALUES(1,'Cliente Alfa','+351910000001',?,1)", (time.time(),))
        c.execute("INSERT OR REPLACE INTO clients(id,name,phone,created_at,phone_verified) VALUES(2,'Cliente Beta','+351910000002',?,1)", (time.time(),))

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

# ==============================================================================
# ETAPA 1 — 5 CENÁRIOS: MENSAGENS PROPRIETÁRIO PARA CLIENTE
# ==============================================================================
def test_p2c_scenario_1_owner_sends_to_client(client):
    """1. Envio com sucesso do proprietário com identificador 'TESTE PROPRIETARIO PARA CLIENTE'."""
    # Login do proprietário
    res_login = client.post("/api/owner/login", json={"phone": "+351920000001", "password": "SecretOwner2026!"})
    assert res_login.status_code == 200

    # Envia mensagem para cliente
    res_msg = client.post("/api/messages", json={
        "message": "TESTE PROPRIETARIO PARA CLIENTE",
        "recipient_type": "client",
        "recipient_id": "+351910000001"
    })
    assert res_msg.status_code == 201
    mid = res_msg.get_json()["id"]

    # Consulta como cliente Alfa
    client.post("/api/client/register", json={"name": "Cliente Alfa", "phone": "+351910000001"})
    res_get = client.get("/api/messages")
    assert res_get.status_code == 200
    msgs = res_get.get_json()
    assert any(m["id"] == mid and m["message"] == "TESTE PROPRIETARIO PARA CLIENTE" for m in msgs)

def test_p2c_scenario_2_broadcast_to_all_clients(client):
    """2. Proprietário envia mensagem geral (recipient_id: 'all') recebida por todos os clientes."""
    client.post("/api/owner/login", json={"phone": "+351920000001", "password": "SecretOwner2026!"})
    res_msg = client.post("/api/messages", json={
        "message": "Aviso: Aberto no feriado",
        "recipient_type": "client",
        "recipient_id": "all"
    })
    assert res_msg.status_code == 201
    mid = res_msg.get_json()["id"]

    # Cliente Beta recebe aviso geral
    client.post("/api/client/register", json={"name": "Cliente Beta", "phone": "+351910000002"})
    msgs = client.get("/api/messages").get_json()
    assert any(m["id"] == mid for m in msgs)

def test_p2c_scenario_3_client_cannot_see_other_client_messages(client):
    """3. Isolamento: Cliente Beta NÃO consegue ver mensagem privada enviada ao Cliente Alfa."""
    # Proprietário envia mensagem exclusiva para Cliente Alfa
    client.post("/api/owner/login", json={"phone": "+351920000001", "password": "SecretOwner2026!"})
    res_msg = client.post("/api/messages", json={
        "message": "Mensagem confidencial para Alfa",
        "recipient_type": "client",
        "recipient_id": "+351910000001"
    })
    mid = res_msg.get_json()["id"]

    # Cliente Beta consulta suas mensagens
    client.post("/api/client/register", json={"name": "Cliente Beta", "phone": "+351910000002"})
    msgs_beta = client.get("/api/messages").get_json()
    assert not any(m["id"] == mid for m in msgs_beta)

def test_p2c_scenario_4_empty_message_rejected(client):
    """4. Rejeição de mensagem vazia sem anexo de foto."""
    client.post("/api/owner/login", json={"phone": "+351920000001", "password": "SecretOwner2026!"})
    res = client.post("/api/messages", json={"message": "   ", "recipient_type": "client", "recipient_id": "+351910000001"})
    assert res.status_code == 400
    assert "mensagem" in res.get_json()["error"].lower()

def test_p2c_scenario_5_unauthenticated_cannot_send(client):
    """5. Tentativa de envio sem sessão autenticada é bloqueada com 401."""
    res = client.post("/api/messages", json={"message": "Hack", "recipient_type": "client", "recipient_id": "+351910000001"})
    assert res.status_code == 401

# ==============================================================================
# ETAPA 1 — 5 CENÁRIOS: MENSAGENS CLIENTE PARA PROPRIETÁRIO
# ==============================================================================
def test_c2p_scenario_1_client_sends_to_owner(client):
    """1. Cliente envia 'TESTE CLIENTE PARA PROPRIETARIO' e o proprietário recebe."""
    client.post("/api/client/register", json={"name": "Cliente Alfa", "phone": "+351910000001"})
    res_msg = client.post("/api/messages", json={
        "message": "TESTE CLIENTE PARA PROPRIETARIO"
    })
    assert res_msg.status_code == 201
    mid = res_msg.get_json()["id"]

    # Proprietário consulta mensagens
    client.post("/api/owner/login", json={"phone": "+351920000001", "password": "SecretOwner2026!"})
    owner_msgs = client.get("/api/messages").get_json()
    assert any(m["id"] == mid and m["message"] == "TESTE CLIENTE PARA PROPRIETARIO" for m in owner_msgs)

def test_c2p_scenario_2_owner_filters_by_client(client):
    """2. Proprietário pode filtrar a conversa específica de um cliente."""
    client.post("/api/client/register", json={"name": "Cliente Alfa", "phone": "+351910000001"})
    client.post("/api/messages", json={"message": "Mensagem Alfa"})

    client.post("/api/client/register", json={"name": "Cliente Beta", "phone": "+351910000002"})
    client.post("/api/messages", json={"message": "Mensagem Beta"})

    client.post("/api/owner/login", json={"phone": "+351920000001", "password": "SecretOwner2026!"})
    filtered = client.get("/api/messages?client_phone=+351910000001").get_json()
    assert all(m["sender_id"] == "+351910000001" or m["recipient_id"] in ("+351910000001", "all") for m in filtered)
    assert not any(m["message"] == "Mensagem Beta" for m in filtered)

def test_c2p_scenario_3_client_cannot_spoof_sender(client):
    """3. Cliente não pode forjar sender_id; o backend força o número da sessão do cliente."""
    client.post("/api/client/register", json={"name": "Cliente Alfa", "phone": "+351910000001"})
    res = client.post("/api/messages", json={
        "message": "Tentando forjar",
        "sender_id": "+351999999999"
    })
    assert res.status_code == 201
    assert res.get_json()["sender_id"] == "+351910000001"

def test_c2p_scenario_4_message_persistence_across_sessions(client):
    """4. Persistência: mensagem continua gravada após limpeza de sessão e recarregamento."""
    client.post("/api/client/register", json={"name": "Cliente Alfa", "phone": "+351910000001"})
    res = client.post("/api/messages", json={"message": "Mensagem Persistente"})
    mid = res.get_json()["id"]

    # Simula logout/limpeza de sessão e reautenticação
    client.post("/api/client/logout")
    client.post("/api/client/register", json={"name": "Cliente Alfa", "phone": "+351910000001"})
    msgs = client.get("/api/messages").get_json()
    assert any(m["id"] == mid for m in msgs)

def test_c2p_scenario_5_dev_cannot_read_private_messages(client):
    """5. Privacidade: Gestor/Developer autenticado NÃO tem acesso irrestrito às conversas privadas."""
    client.post("/api/client/register", json={"name": "Cliente Alfa", "phone": "+351910000001"})
    client.post("/api/messages", json={"message": "Segredo cliente-barbearia"})

    # Login gestor
    client.post("/api/dev/login", json={"username": "DBAONLINE", "password": "SecretDev2026!"})
    dev_msgs = client.get("/api/messages").get_json()
    assert dev_msgs == []

# ==============================================================================
# ETAPA 2 — TESTES DOS BOTÕES DE DIAGNÓSTICO DO GESTOR
# ==============================================================================
def get_dev_csrf(client):
    res = client.get("/api/csrf")
    return res.get_json().get("csrf_token")

def test_dev_diagnostic_buttons(client):
    """Testa todos os botões e endpoints do Centro de Administração e Diagnóstico."""
    # Login gestor
    log_res = client.post("/api/dev/login", json={"username": "DBAONLINE", "password": "SecretDev2026!"})
    assert log_res.status_code == 200
    csrf = get_dev_csrf(client)
    headers = {"X-CSRF-Token": csrf}

    # 1. Dashboard
    res_dash = client.get("/api/dev/dashboard")
    assert res_dash.status_code == 200
    assert "stats" in res_dash.get_json()

    # 2. System info
    res_sys = client.get("/api/dev/system")
    assert res_sys.status_code == 200

    # 3. Clientes
    res_cli = client.get("/api/dev/clients")
    assert res_cli.status_code == 200

    # 4. Agendamentos
    res_appt = client.get("/api/dev/appointments")
    assert res_appt.status_code == 200

    # 5. Notificações
    res_notif = client.get("/api/dev/notifications")
    assert res_notif.status_code == 200

    # 6. Auditoria
    res_audit = client.get("/api/dev/audit")
    assert res_audit.status_code == 200

    # 7. Ferramenta de reparação: Disponibilidade
    r_avail = client.post("/api/dev/repair/availability", headers=headers)
    assert r_avail.status_code == 200
    assert r_avail.get_json()["status"] == "ok"

    # 8. Ferramenta de reparação: Horários Duplicados
    r_dup = client.post("/api/dev/repair/duplicates", headers=headers)
    assert r_dup.status_code == 200
    assert r_dup.get_json()["status"] == "ok"

    # 9. Ferramenta de reparação: Pedidos 48h
    r_pend = client.post("/api/dev/repair/pending", headers=headers)
    assert r_pend.status_code == 200
    assert "expired_count" in r_pend.get_json()

    # 10. Ferramenta de reparação: Sincronização
    r_sync = client.post("/api/dev/repair/sync", headers=headers)
    assert r_sync.status_code == 200
    assert r_sync.get_json()["status"] == "ok"

    # 11. Ferramenta de reparação: Uploads de Fotos
    r_img = client.post("/api/dev/repair/images", headers=headers)
    assert r_img.status_code == 200
    assert r_img.get_json()["status"] == "ok"

    # 12. Ferramenta de reparação: Fila de Notificações
    r_not = client.post("/api/dev/repair/notifications", headers=headers)
    assert r_not.status_code == 200
    assert r_not.get_json()["status"] == "ok"

    # 13. Ferramenta de reparação: Integridade do SQLite
    r_int = client.post("/api/dev/repair/integrity", headers=headers)
    assert r_int.status_code == 200
    assert r_int.get_json()["status"] == "ok"

    # 14. Histórico de reparações
    r_hist = client.get("/api/dev/repair/repairs")
    assert r_hist.status_code == 200
    assert len(r_hist.get_json()) >= 7

    # 15. Publicação de versão PWA
    r_ver = client.post("/api/dev/version", json={"version": "1.2.0", "changelog": "Auditoria aprovada"}, headers=headers)
    assert r_ver.status_code == 201

    # 16. Pré-visualização de recuperação em etapas
    r_prev = client.post("/api/dev/recovery/preview", headers=headers)
    assert r_prev.status_code == 200
    assert "impact_preview" in r_prev.get_json()

    # 17. Execução de recuperação em etapas
    r_rec = client.post("/api/dev/recovery/execute", json={"confirm": "CONFIRM_STAGED_RECOVERY"}, headers=headers)
    assert r_rec.status_code == 200

    # 18. Cadastro de novo proprietário pelo gestor
    r_owner = client.post("/api/dev/owners", json={
        "phone": "+351930000001",
        "password": "SecurePassword2026!",
        "max_devices": 2
    }, headers=headers)
    assert r_owner.status_code == 201

    # 19. Reset de ambiente de teste
    r_rst = client.post("/api/dev/test/reset", json={"confirm": "RESET_TEST_ENVIRONMENT"}, headers=headers)
    assert r_rst.status_code == 200

    # 20. Logout do gestor
    r_out = client.post("/api/dev/logout")
    assert r_out.status_code == 200
    assert client.get("/api/dev/me").get_json()["authenticated"] is False

# ==============================================================================
# ETAPA 4 — TESTES DE CONFIRMAÇÃO DE TELEFONE
# ==============================================================================
def test_phone_verification_flow(client):
    """Fluxo completo de envio de SMS e validação de código único."""
    phone = "+351915550001"
    # 1. Envio do código
    res_send = client.post("/api/client/phone/send-code", json={"phone": phone})
    assert res_send.status_code == 200
    data_send = res_send.get_json()
    assert data_send["status"] == "code_sent"
    code = data_send["dev_code_test"]

    # 2. Código incorreto
    res_err = client.post("/api/client/phone/verify-code", json={"phone": phone, "code": "000000"})
    assert res_err.status_code == 400
    assert "incorreto" in res_err.get_json()["error"].lower()

    # 3. Código correto
    res_ok = client.post("/api/client/phone/verify-code", json={"phone": phone, "code": code})
    assert res_ok.status_code == 200
    assert res_ok.get_json()["verified"] is True

    # 4. Código não pode ser reutilizado (expiração e uso único)
    res_reuse = client.post("/api/client/phone/verify-code", json={"phone": phone, "code": code})
    assert res_reuse.status_code == 400

def test_phone_verification_rate_limit(client):
    """Proteção contra excesso de envios de SMS."""
    phone = "+351919998877"
    for _ in range(3):
        client.post("/api/client/phone/send-code", json={"phone": phone})
    res_blocked = client.post("/api/client/phone/send-code", json={"phone": phone})
    assert res_blocked.status_code == 429
