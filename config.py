# =============================================================
#  CONFIGURAÇÃO DO BOT VIP
#  Este é o ÚNICO arquivo que você precisa editar.
# =============================================================
import os

# --- Chaves e IDs (NÃO edite aqui — configure no Railway, aba "Variables") ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///dados.db")

# =============================================================
#  SEUS PLANOS — edite os nomes, preços e duração (em dias)
#  Pode adicionar ou remover planos, mantendo o mesmo formato.
# =============================================================
PLANOS = {
    "mensal": {
        "nome": "Plano Mensal",
        "preco": 29.90,
        "dias": 30,
    },
    "trimestral": {
        "nome": "Plano Trimestral",
        "preco": 79.90,
        "dias": 90,
    },
    "anual": {
        "nome": "Plano Anual",
        "preco": 249.90,
        "dias": 365,
    },
}

# =============================================================
#  TEXTOS DO BOT — personalize à vontade
# =============================================================
TEXTO_BOAS_VINDAS = (
    "👋 Olá! Seja bem-vindo(a)!\n\n"
    "Aqui você garante seu acesso ao nosso *Grupo VIP*.\n\n"
    "Escolha um plano abaixo para começar:"
)

TEXTO_APOS_PAGAMENTO = (
    "✅ *Pagamento confirmado!*\n\n"
    "Aqui está seu convite exclusivo para entrar no grupo. "
    "Ele é de uso único — não compartilhe com ninguém."
)

TEXTO_LEMBRETE = (
    "⏰ *Atenção!* Sua assinatura vence em {dias} dia(s).\n\n"
    "Renove agora para não perder o acesso ao grupo VIP. "
    "É só usar o comando /start e escolher um plano. 😉"
)

TEXTO_REMOVIDO = (
    "😔 Sua assinatura venceu e seu acesso ao grupo VIP foi encerrado.\n\n"
    "Quando quiser voltar, é só usar o /start e renovar. "
    "Será um prazer te receber de novo!"
)

# Quantos dias antes do vencimento o bot envia o lembrete
DIAS_AVISO_VENCIMENTO = 3

# Validade do PIX gerado (em minutos)
VALIDADE_PIX_MINUTOS = 40
