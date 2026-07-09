# 🤖 Bot VIP — Seu "Botgram" próprio, sem mensalidade

Bot de Telegram que **cobra assinaturas via PIX (Mercado Pago)**, envia o convite
do grupo automaticamente quando o pagamento cai, lembra o assinante antes de
vencer e **remove quem não renovou**. O dinheiro cai direto na sua conta do
Mercado Pago.

Você **não precisa saber programar**. Siga os passos na ordem.

---

## PASSO 1 — Criar o bot no Telegram (2 min)

1. No Telegram, procure por **@BotFather** e abra a conversa.
2. Envie o comando `/newbot`.
3. Escolha um nome (ex: *Studio VIP Bot*) e um username terminando em `bot`
   (ex: `studiovip_bot`).
4. O BotFather vai te dar um **TOKEN** (algo como `7123456:AAH8s9d...`).
   **Copie e guarde** — vamos usar no Passo 4.

## PASSO 2 — Pegar sua chave do Mercado Pago (3 min)

1. Acesse: https://www.mercadopago.com.br/developers/panel
2. Faça login com sua conta do Mercado Pago.
3. Clique em **"Criar aplicação"** (qualquer nome, ex: "Bot VIP").
4. Dentro da aplicação, vá em **"Credenciais de produção"**.
5. Copie o **Access Token** (começa com `APP_USR-...`). Guarde.

## PASSO 3 — Preparar o grupo (2 min)

1. Crie (ou abra) seu grupo/canal VIP no Telegram.
2. Adicione o seu bot como **administrador** do grupo, com as permissões:
   - ✅ Convidar usuários via link
   - ✅ Banir usuários
3. Dentro do grupo, envie o comando `/id` — o bot vai responder com o
   **ID do grupo** (um número negativo, ex: `-1001234567890`). Guarde.
   > Se o bot não responder no grupo ainda, faça esse passo depois do Passo 4,
   > quando o bot estiver no ar.
4. No privado com o bot, envie `/id` também para pegar o **seu ID de usuário**
   (será o ADMIN_ID). Guarde.

## PASSO 4 — Colocar no ar (Railway) (10 min)

1. Crie uma conta em https://github.com (se ainda não tiver) e crie um
   **repositório novo** (pode ser privado). Clique em *"uploading an existing
   file"* e arraste todos os arquivos desta pasta.
2. Acesse https://railway.app e faça login com o GitHub.
3. Clique em **New Project → Deploy from GitHub repo** e escolha o repositório.
4. Ainda no projeto, clique em **+ New → Database → PostgreSQL**
   (isso guarda seus assinantes mesmo se o bot reiniciar).
5. Clique no serviço do bot → aba **Variables** → adicione:

   | Variável          | Valor                                        |
   |-------------------|----------------------------------------------|
   | `BOT_TOKEN`       | o token do BotFather (Passo 1)               |
   | `MP_ACCESS_TOKEN` | o Access Token do Mercado Pago (Passo 2)     |
   | `GROUP_ID`        | o ID do grupo (Passo 3)                      |
   | `ADMIN_ID`        | o seu ID de usuário (Passo 3)                |
   | `DATABASE_URL`    | clique em *Add Reference* → Postgres → `DATABASE_URL` |

6. O Railway faz o deploy sozinho. Quando aparecer "Bot VIP iniciado! 🚀"
   nos logs, está no ar.

## PASSO 5 — Configurar seus planos e textos

Abra o arquivo **`config.py`** (dá pra editar direto no site do GitHub,
no ícone de lápis ✏️) e ajuste:

- **PLANOS** — nomes, preços e duração em dias
- **Textos** — boas-vindas, lembrete, etc.

Ao salvar no GitHub, o Railway atualiza o bot sozinho em ~1 minuto.

---

## Como funciona no dia a dia

- O cliente abre o bot, envia `/start`, escolhe o plano e paga o **PIX**.
- Em até 1 minuto após o pagamento, o bot envia o **convite de uso único**.
- **3 dias antes de vencer**, o bot manda um lembrete de renovação.
- **Venceu e não renovou?** O bot remove a pessoa do grupo automaticamente
  (todo dia às 10h) e avisa você.
- Renovação **soma** ao tempo restante (ninguém perde dias pagos).

## Comandos úteis

| Comando   | Quem usa    | O que faz                                    |
|-----------|-------------|----------------------------------------------|
| `/start`  | Cliente     | Mostra os planos e inicia a compra           |
| `/status` | Cliente     | Mostra até quando a assinatura vale          |
| `/id`     | Você        | Mostra o ID do chat/usuário                  |
| `/stats`  | Só você     | Assinantes ativos, vendas e receita do mês   |

## Custos

- **Bot:** R$ 0 de mensalidade.
- **Mercado Pago:** ~0,99% por PIX recebido (taxa deles, não do bot).
- **Railway:** plano Hobby (~US$ 5/mês, com US$ 5 de uso incluído — um bot
  leve como este normalmente fica dentro disso).

## Aviso importante

⚠️ O bot só gerencia **quem entrar pelo link dele**. Membros que já estavam
no grupo antes não são controlados (igual ao Botgram).
