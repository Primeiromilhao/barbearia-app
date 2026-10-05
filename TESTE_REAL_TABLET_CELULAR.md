# TESTE REAL — BARBEARIA — TABLET PROPRIETÁRIO + CELULAR CLIENTE

Data: 2026-10-05
Release backend: b148154
Objetivo: validar o produto em dois dispositivos físicos.

## Papéis
- Tablet: PROPRIETÁRIO. Primeiro dispositivo autorizado para gestão.
- Celular: CLIENTE. Fluxo público de cadastro e agendamento.

## Fluxo obrigatório
1. Tablet abre /proprietario.html.
2. Informar telefone do proprietário + senha de ativação.
3. Ativar/entrar neste dispositivo.
4. Confirmar que a área privada carrega.
5. Celular abre a página principal.
6. Cadastrar cliente com nome + telefone.
7. Escolher serviço, data e horário.
8. Enviar solicitação.
9. Tablet deve receber o agendamento em Pendentes.
10. Tablet confirma.
11. Celular consulta Histórico e deve mostrar CONFIRMADO.
12. Celular cancela o agendamento.
13. Tablet deve refletir o cancelamento.
14. Tentar abrir a área do proprietário em outro navegador/dispositivo: deve ser recusado se o limite de dispositivos estiver 1.
15. Não compartilhar a senha de ativação durante o teste.

## Validações automatizadas
- Backend online /api/health: PASS.
- /api/owner/me sem sessão: PASS.
- Endpoint de proprietário sem autenticação: PASS (401).
- Endpoint de cliente sem sessão: PASS (401).
- CORS malicioso: PASS.
- Headers de segurança: PASS.
- Frontend cliente 390x844: PASS.
- Frontend cliente 820x1180: PASS.
- Frontend proprietário local sincronizado para a versão criptográfica: PASS.

## Regra de release
A venda comercial só recebe o selo RELEASE após o teste físico dos dois dispositivos acima terminar sem falha.
