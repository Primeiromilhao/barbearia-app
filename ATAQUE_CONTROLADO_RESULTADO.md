# ATAQUE CONTROLADO — BARBEARIA
Data: 2026-10-04
Escopo: sistema próprio Barbearia
Executor: Gravity/Desktop Commander

## RESULTADOS

### A01 — Endpoints do proprietário sem sessão (ONLINE)
GET /api/owner/appointments -> 200 FAIL
GET /api/owner/clients -> 200 FAIL
GET /api/notifications -> 200 FAIL
GET /api/owner/me -> 404 (versão online antiga)
Conclusão: Render ainda não está com os commits de segurança.

### A02 — Autenticação do proprietário (LOCAL)
Sem sessão -> appointments 401, clients 401, notifications 401, owner/me 200 PASS
Senha inválida -> 401 PASS
Senha válida -> 200 PASS
Com sessão -> endpoints privados 200 PASS
Logout -> 200 PASS
Após logout -> 401 PASS

### A03 — IDOR/ownership (ANÁLISE DE CÓDIGO)
/api/appointments?phone=... não exige sessão nem prova de posse do telefone. Risco: enumeração/acesso indevido a agenda por telefone.
/api/appointments/<id>/cancel não exige sessão nem verifica que o agendamento pertence ao solicitante. Risco: cancelamento por ID.
STATUS: FAIL — correção necessária.

### A04 — CORS ONLINE
OPTIONS com Origin https://evil.example -> 200 sem Access-Control-Allow-Origin para origem maliciosa.
STATUS: PASS quanto ao bloqueio da origem.

### A05 — Métodos inesperados
A checar após deploy da versão corrigida. Esperado: 405.

## ESTADO FINAL DA RODADA

LOCAL: PASS nos controles de autenticação, IDOR, ownership, replay, logout, métodos HTTP e CORS.

Correções aplicadas: sessão do cliente vinculada ao telefone; histórico e cancelamento exigem ownership; telefone duplicado não pode ser tomado por outra sessão; criação de agendamento exige sessão correspondente; frontend envia cookies de sessão.

ONLINE: BLOCKED. Render continua retornando /api/owner/me = 404 e endpoints antigos sem autenticação. A versão endurecida ainda não foi confirmada no host. BARBEARIA_OWNER_PASSWORD também precisa estar configurada no Render.

WEB E2E: o teste antigo de navegador está obsoleto porque pressupõe a autenticação antiga por telefone do proprietário. Não é critério de aprovação da arquitetura mobile-first.

## BLOQUEIO DE RELEASE
FAIL crítico apenas no gate de infraestrutura/deploy: a versão endurecida ainda não está confirmada online.

## PRÓXIMO GATE
Depois do deploy, repetir ataques online e só então validar vínculo seguro do app do proprietário ao dispositivo e transferência de propriedade.

## PRÓXIMAS FASES
1. Deploy dos commits de segurança no Render.
2. Configurar BARBEARIA_OWNER_PASSWORD no host.
3. Repetir ataques online.
4. Corrigir ownership/IDOR de cliente.
5. Implementar licença por instalação/dispositivo para app proprietário.
6. Testar clonagem da instalação em segundo aparelho.
7. Testar transferência de proprietário.
8. Regressão completa.

# ATUALIZAÇÃO — 2026-10-04 — CAMADA 2

Executor: Gravity/Desktop Commander
Commit: ef02bd7

## CAMADA 2 EXECUTADA
- Rate limiting por IP/rota.
- Limite de payload HTTP de 64 KB.
- Headers: nosniff, frame deny, referrer policy, permissions policy.
- Cache-Control no-store para API.
- Rate limit específico para autenticação/ativação.
- Teste de brute force controlado: 13 tentativas de login, 13ª bloqueada com HTTP 429.
- Regressão da bateria principal: PASS.
- py_compile do backend: PASS.

## RENDER
Consulta online em 2026-10-04 ainda retorna:
GET /api/owner/me -> HTTP 404.
Portanto o host continua servindo uma versão anterior e o Release Gate permanece BLOQUEADO.
Não foi declarado que a produção está segura.

## ROADMAP COMERCIAL
Registrado em ROADMAP_SEGURANCA_E_PRODUTO.md:
- perfil visual/fotos;
- portfólio antes/depois;
- serviços e combos;
- múltiplos barbeiros;
- agenda avançada;
- fidelização;
- notificações/WhatsApp;
- relatórios/caixa;
- fotos com upload seguro;
- multiunidade;
- planos Base/Pro/Business/Enterprise.

Regra: cada módulo futuro passa pelo Security Gate antes de publicação.
