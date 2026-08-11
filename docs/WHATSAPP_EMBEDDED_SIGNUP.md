# WhatsApp Embedded Signup

Deixa o espaço conectar o **próprio** número de WhatsApp Business à Hevo
(login na conta dele, autoriza a Hevo a mandar/receber mensagens) — a Hevo
nunca é dona do número. Isso é o modelo "Tech Provider" do Meta, mais
trabalhoso de configurar que um número único, mas é o que sustenta múltiplos
clientes sem cada um virar uma integração manual.

O código (`apps/venue/views.py:whatsapp_connect`, `static/js/whatsapp-
embedded-signup.js`) já está pronto — falta só a configuração do lado do
Meta, feita uma vez pela conta da Hevo.

## 1. Verificação de negócio

No [Meta Business Manager](https://business.facebook.com/), `Configurações
do Business` → `Verificação de negócios` → complete com os documentos legais
da Hevo. Obrigatório antes de sair do modo de teste — sem isso, só usuários
adicionados manualmente como "Test users" conseguem conectar.

## 2. Marcar como Tech Provider

Ainda em `Configurações do Business`, procure a opção de tornar o Business
um **Tech Provider**. É isso que permite outros Businesses (os clientes)
concederem acesso ao WhatsApp deles pra Hevo via Embedded Signup.

## 3. App no Meta for Developers

Se ainda não existe um app: [developers.facebook.com](https://developers.facebook.com/)
→ `Meus apps` → `Criar app` → tipo "Business".

- Adicione o produto **WhatsApp**
- Anote o **App ID** (vai em `FACEBOOK_APP_ID`)

## 4. Configuração de Embedded Signup

Dentro do app: `WhatsApp` → `Configuration` → `Embedded Signup` (ou
`Business Login for WhatsApp`, o nome varia por versão do console) →
criar uma configuração:

- Vincule ao Business da Hevo
- Escopo de permissões: `whatsapp_business_messaging` +
  `whatsapp_business_management`
- Ao salvar, você recebe um **Configuration ID** → vai em
  `WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID`

## 5. Advanced Access

`App Review` → `Permissions and Features` → solicite **Advanced Access**
pras duas permissões do passo 4. Standard Access só cobre números de teste;
sem Advanced Access, clientes reais não conseguem completar o signup.
Isso passa por revisão do Meta (eles pedem uma descrição do caso de uso e,
às vezes, um vídeo de demonstração).

## 6. System User + token

No Business Manager: `Usuários` → `Usuários do sistema` → criar um System
User (papel: Admin ou Employee, dependendo de quais outras ações ele vai
fazer). Atribua a ele:

- O app da Hevo, com as permissões `whatsapp_business_messaging` e
  `whatsapp_business_management`

Gere um **token de acesso de longa duração** (ou sem expiração, se
disponível) pra esse System User → vai em `WHATSAPP_ACCESS_TOKEN` (a mesma
variável já usada pra mandar mensagem — é o mesmo token usado nos dois
lugares).

## 7. Variáveis de ambiente

No `.env` (local e de cada servidor):

```
FACEBOOK_APP_ID=<do passo 3>
WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID=<do passo 4>
WHATSAPP_ACCESS_TOKEN=<token do System User, passo 6>
```

## Como funciona depois de configurado

1. O espaço abre `Base de Conhecimento` → `Conectar WhatsApp`
2. Um popup do Meta abre — o dono do WhatsApp Business loga com a própria
   conta e autoriza a Hevo
3. O popup manda de volta (via `postMessage`) o `phone_number_id` e
   `waba_id` que o cliente escolheu
4. O frontend (`whatsapp-embedded-signup.js`) manda isso pro backend
   (`venue:whatsapp-connect`)
5. O backend chama `POST /{waba_id}/subscribed_apps` (usando o token do
   System User) — é esse passo que faz o WABA do cliente começar a mandar
   eventos pro nosso webhook único
6. Salva `phone_number_id`/`waba_id` no `Venue`, pronto

## O que não testei

Sem `FACEBOOK_APP_ID`/`CONFIG_ID` reais não dá pra abrir o popup de verdade
nem confirmar o payload exato do `postMessage` do Meta em produção. Validei
a lógica do backend (endpoint, tratamento de erro de rede, gravação no
banco) com um `waba_id` falso — o resto só valida configurando os passos
acima e testando o botão de verdade.
