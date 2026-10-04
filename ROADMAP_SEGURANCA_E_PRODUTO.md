# BARBEARIA — CAMADA 2 DE SEGURANÇA E ROADMAP COMERCIAL
Data: 2026-10-04
Executor: Gravity/Desktop Commander
Projeto: Fábrica de Aplicativos / Barbearia

## REGRA DA FÁBRICA
Toda evolução deste aplicativo passa pelo mesmo ciclo: arquitetura -> implementação -> QA -> Security -> testes negativos -> regressão -> publicação controlada -> QA online -> Release Gate.
O Executor registra as ações e evidências. Nenhuma funcionalidade comercial nova fica fora do Security Gate.

## CAMADA 2 — HARDENING
Objetivos:
1. Rate limiting para login, ativação de dispositivo, challenge e cadastro.
2. Limite de tamanho do corpo HTTP.
3. Validação robusta de JSON e tipos.
4. Headers de segurança.
5. Cache-control para dados de API.
6. Auditoria de ações administrativas sem armazenar senhas ou chaves privadas.
7. Testes de abuso: brute force, payload inválido, excesso de requisições, métodos HTTP inesperados, replay, device clone, sessão expirada e CORS.
8. Regressão completa após cada correção.
9. Teste online no Render antes do Release Gate.

## CAMADA 3 — FUTURA SEGURANÇA COMERCIAL
Para uma versão nativa Android do proprietário:
- Android Keystore / chave não exportável.
- Attestation quando disponível.
- Revogação de instalação.
- Transferência segura de propriedade.
- Política 1 licença -> 1 dispositivo ou N dispositivos.
- Registro de eventos de segurança.
- Detecção de instalação/clonagem anormal.
A identidade do aparelho não deve depender exclusivamente de IMEI.

## PRODUTO BASE — O QUE VENDEMOS AGORA
O MVP demonstra:
- cadastro do cliente;
- catálogo de serviços;
- agendamento;
- confirmação/recusa pelo proprietário;
- histórico;
- cancelamento com ownership;
- notificações preparadas;
- acesso do proprietário vinculado ao dispositivo;
- trilha de auditoria;
- arquitetura separada cliente/proprietário.

## ROADMAP DE UPSELL — VERSÃO 2
### 1. Perfil visual da barbearia
- logo;
- capa;
- fotos do ambiente;
- galeria de cortes;
- portfólio antes/depois;
- horários e endereço;
- identidade visual personalizada.

### 2. Serviços e preços
- serviços ilimitados;
- duração;
- preço;
- promoções;
- combos;
- adicionais;
- serviços por profissional.

### 3. Agenda profissional
- múltiplos barbeiros;
- agenda individual;
- bloqueios;
- férias;
- encaixe;
- recorrência;
- lista de espera;
- confirmação automática.

### 4. Cliente
- favoritos;
- histórico;
- barbeiro preferido;
- lembretes;
- avaliação;
- foto de referência do corte;
- observações do cliente.

### 5. Gestão
- faturamento;
- caixa diário;
- relatórios;
- clientes ativos/inativos;
- ticket médio;
- horários mais procurados;
- serviços mais vendidos;
- painel de desempenho.

### 6. Fidelização
- pontos;
- cartão digital;
- indicação;
- cupom;
- aniversário;
- campanhas para clientes inativos;
- programa VIP.

### 7. Comunicação
- notificações push;
- WhatsApp via integração autorizada;
- lembrete automático;
- confirmação;
- aviso de atraso;
- campanhas segmentadas.

### 8. Fotos e mídia
Sim, fotos são uma ótima evolução comercial, mas devem entrar com segurança:
- compressão no cliente;
- limite de tamanho;
- formatos permitidos;
- remoção de metadados quando apropriado;
- autorização do cliente para fotos;
- armazenamento separado;
- URLs temporárias;
- controle de acesso;
- exclusão pelo proprietário;
- proteção contra upload de arquivos maliciosos.

### 9. Multiunidade
- uma conta para várias barbearias;
- profissionais por unidade;
- permissões;
- relatórios por unidade;
- administração central.

### 10. Monetização
Pacotes possíveis:
BASE: agenda + clientes + serviços.
PRO: fotos + fidelização + relatórios + notificações.
BUSINESS: múltiplos profissionais + caixa + campanhas.
ENTERPRISE: múltiplas unidades + permissões + relatórios avançados + suporte.

## PRINCÍPIO COMERCIAL
A versão atual deve ser simples, bonita e segura para demonstrar valor.
As funções avançadas ficam como módulos de expansão contratáveis.
Cada módulo novo precisa nascer com seus próprios testes funcionais e negativos.

## BLOQUEIO ATUAL
O Release Gate continua bloqueado até a versão endurecida ser confirmada no Render e a bateria online ser repetida.
