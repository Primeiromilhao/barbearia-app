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

## BLOQUEIO DE RELEASE
FAIL crítico enquanto Render estiver na versão antiga e enquanto ownership de cliente/cancelamento não estiver protegido.

## PRÓXIMAS FASES
1. Deploy dos commits de segurança no Render.
2. Configurar BARBEARIA_OWNER_PASSWORD no host.
3. Repetir ataques online.
4. Corrigir ownership/IDOR de cliente.
5. Implementar licença por instalação/dispositivo para app proprietário.
6. Testar clonagem da instalação em segundo aparelho.
7. Testar transferência de proprietário.
8. Regressão completa.
