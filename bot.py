# =============================================================
#  BOT VIP — gestão de assinaturas para grupo/canal do Telegram
#  Pagamento via PIX (Mercado Pago) | Hospedagem: Railway
#  Você não precisa mexer neste arquivo.
# =============================================================
import base64
import io
import logging
import re
from datetime import datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo

import mercadopago
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from database import Assinante, Pagamento, SessionLocal, iniciar_banco

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("bot-vip")

sdk = mercadopago.SDK(config.MP_ACCESS_TOKEN)

FUSO_BR = ZoneInfo("America/Sao_Paulo")
EMAIL_REGEX = re.compile(r"^[\w\.\-\+]+@[\w\-]+\.[\w\.\-]+$")


def utc(dt):
    """Garante que o datetime tenha fuso UTC (SQLite salva sem fuso)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def agora():
    return datetime.now(timezone.utc)


# =============================================================
#  COMANDOS BÁSICOS
# =============================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    botoes = [
        [
            InlineKeyboardButton(
                f"{p['nome']} — R$ {p['preco']:.2f}".replace(".", ","),
                callback_data=f"plano:{chave}",
            )
        ]
        for chave, p in config.PLANOS.items()
    ]
    await update.message.reply_text(
        config.TEXTO_BOAS_VINDAS,
        reply_markup=InlineKeyboardMarkup(botoes),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o ID do chat atual (use dentro do grupo para pegar o GROUP_ID)."""
    await update.message.reply_text(
        f"🆔 ID deste chat: `{update.effective_chat.id}`\n"
        f"🙋 Seu ID de usuário: `{update.effective_user.id}`",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    with SessionLocal() as s:
        a = s.get(Assinante, update.effective_user.id)
    if a and a.ativo and utc(a.vence_em) > agora():
        venc = utc(a.vence_em).astimezone(FUSO_BR).strftime("%d/%m/%Y")
        await update.message.reply_text(
            f"✅ Sua assinatura está *ativa*!\n📅 Válida até: *{venc}*",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text(
            "Você não tem uma assinatura ativa no momento. "
            "Use /start para assinar. 😊"
        )


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        return
    with SessionLocal() as s:
        ativos = (
            s.query(Assinante).filter(Assinante.ativo == True).count()  # noqa
        )
        inicio_mes = agora().replace(day=1, hour=0, minute=0, second=0)
        pagos_mes = (
            s.query(Pagamento)
            .filter(Pagamento.status == "approved")
            .all()
        )
        receita = sum(
            p.valor for p in pagos_mes if utc(p.criado_em) >= inicio_mes
        )
        vendas = sum(1 for p in pagos_mes if utc(p.criado_em) >= inicio_mes)
    await update.message.reply_text(
        f"📊 *Estatísticas*\n\n"
        f"👥 Assinantes ativos: *{ativos}*\n"
        f"🛒 Vendas neste mês: *{vendas}*\n"
        f"💰 Receita neste mês: *R$ {receita:.2f}*".replace(".", ","),
        parse_mode=ParseMode.MARKDOWN,
    )


# =============================================================
#  FLUXO DE COMPRA
# =============================================================
async def escolher_plano(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chave = query.data.split(":", 1)[1]
    if chave not in config.PLANOS:
        return

    with SessionLocal() as s:
        a = s.get(Assinante, query.from_user.id)

    if a and a.email:
        await gerar_pix(query.from_user, chave, context, query.message.chat_id)
    else:
        context.user_data["plano_pendente"] = chave
        context.user_data["aguardando_email"] = True
        await query.message.reply_text(
            "📧 Antes de gerar o PIX, me envia seu *e-mail* "
            "(necessário para o pagamento):",
            parse_mode=ParseMode.MARKDOWN,
        )


async def receber_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    if not context.user_data.get("aguardando_email"):
        return
    email = update.message.text.strip()
    if not EMAIL_REGEX.match(email):
        await update.message.reply_text(
            "Hmm, esse e-mail não parece válido. Tenta de novo? 🙂"
        )
        return

    user = update.effective_user
    with SessionLocal() as s:
        a = s.get(Assinante, user.id)
        if not a:
            a = Assinante(telegram_id=user.id)
            s.add(a)
        a.nome = user.full_name or ""
        a.username = user.username or ""
        a.email = email
        s.commit()

    context.user_data["aguardando_email"] = False
    chave = context.user_data.pop("plano_pendente", None)
    if chave:
        await gerar_pix(user, chave, context, update.effective_chat.id)


async def gerar_pix(user, chave_plano, context, chat_id):
    plano = config.PLANOS[chave_plano]
    with SessionLocal() as s:
        a = s.get(Assinante, user.id)
        email = a.email if a else "cliente@email.com"

    expira = (agora() + timedelta(minutes=config.VALIDADE_PIX_MINUTOS)).strftime(
        "%Y-%m-%dT%H:%M:%S.000-00:00"
    )
    dados = {
        "transaction_amount": float(plano["preco"]),
        "description": f"{plano['nome']} - Grupo VIP",
        "payment_method_id": "pix",
        "date_of_expiration": expira,
        "payer": {"email": email},
    }
    try:
        resultado = sdk.payment().create(dados)
        resp = resultado["response"]
        pix = resp["point_of_interaction"]["transaction_data"]
        copia_cola = pix["qr_code"]
        qr_base64 = pix.get("qr_code_base64")
        mp_id = str(resp["id"])
    except Exception as e:
        log.error(f"Erro ao criar pagamento: {e}")
        await context.bot.send_message(
            chat_id,
            "😕 Não consegui gerar o PIX agora. Tenta de novo em instantes.",
        )
        return

    with SessionLocal() as s:
        s.add(
            Pagamento(
                mp_id=mp_id,
                telegram_id=user.id,
                plano=chave_plano,
                valor=float(plano["preco"]),
            )
        )
        s.commit()

    if qr_base64:
        foto = io.BytesIO(base64.b64decode(qr_base64))
        foto.name = "pix.png"
        await context.bot.send_photo(chat_id, foto)

    botao = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Já paguei", callback_data=f"verificar:{mp_id}")]]
    )
    preco_txt = f"R$ {plano['preco']:.2f}".replace(".", ",")
    await context.bot.send_message(
        chat_id,
        f"💳 *{plano['nome']}* — {preco_txt}\n\n"
        f"Escaneie o QR Code acima ou use o *PIX copia e cola* abaixo. "
        f"O código vence em {config.VALIDADE_PIX_MINUTOS} minutos.\n\n"
        f"`{copia_cola}`\n\n"
        f"_Toque no código para copiar._ Assim que o pagamento cair, "
        f"eu te envio o convite automaticamente. 😉",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=botao,
    )


async def verificar_pagamento_botao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mp_id = query.data.split(":", 1)[1]
    aprovado = await checar_e_ativar(mp_id, context)
    if aprovado:
        await query.answer("Pagamento confirmado! 🎉")
    else:
        await query.answer(
            "Ainda não identifiquei o pagamento. Aguarde alguns segundos "
            "após pagar e tente de novo.",
            show_alert=True,
        )


# =============================================================
#  CONFIRMAÇÃO E ATIVAÇÃO
# =============================================================
async def checar_e_ativar(mp_id: str, context) -> bool:
    """Consulta o Mercado Pago; se aprovado, ativa a assinatura. Retorna True se aprovado."""
    with SessionLocal() as s:
        pg = s.get(Pagamento, mp_id)
        if not pg:
            return False
        if pg.status == "approved":
            return True

    try:
        resp = sdk.payment().get(int(mp_id))["response"]
        status = resp.get("status", "")
    except Exception as e:
        log.error(f"Erro ao consultar pagamento {mp_id}: {e}")
        return False

    if status != "approved":
        if status in ("cancelled", "expired", "rejected"):
            with SessionLocal() as s:
                pg = s.get(Pagamento, mp_id)
                pg.status = status
                s.commit()
        return False

    # ---- Pagamento aprovado: ativar assinatura ----
    with SessionLocal() as s:
        pg = s.get(Pagamento, mp_id)
        if pg.status == "approved":  # evita ativar duas vezes
            return True
        pg.status = "approved"

        plano = config.PLANOS.get(pg.plano, {"dias": 30, "nome": pg.plano})
        a = s.get(Assinante, pg.telegram_id)
        if not a:
            a = Assinante(telegram_id=pg.telegram_id)
            s.add(a)

        base = agora()
        if a.ativo and a.vence_em and utc(a.vence_em) > base:
            base = utc(a.vence_em)  # renovação: soma ao tempo restante
        a.vence_em = base + timedelta(days=plano["dias"])
        a.ativo = True
        a.avisado = False
        a.plano = pg.plano
        s.commit()
        telegram_id = pg.telegram_id
        vence = utc(a.vence_em)

    # Convite de uso único
    try:
        convite = await context.bot.create_chat_invite_link(
            chat_id=config.GROUP_ID,
            member_limit=1,
            expire_date=agora() + timedelta(days=2),
        )
        link = convite.invite_link
    except Exception as e:
        log.error(f"Erro ao criar convite: {e}")
        link = None

    venc_txt = vence.astimezone(FUSO_BR).strftime("%d/%m/%Y")
    texto = config.TEXTO_APOS_PAGAMENTO + f"\n\n📅 Acesso válido até: *{venc_txt}*"
    botoes = None
    if link:
        botoes = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🚪 Entrar no Grupo VIP", url=link)]]
        )
    try:
        await context.bot.send_message(
            telegram_id, texto, parse_mode=ParseMode.MARKDOWN, reply_markup=botoes
        )
    except Exception as e:
        log.error(f"Erro ao avisar assinante {telegram_id}: {e}")

    # Notifica o admin
    if config.ADMIN_ID:
        try:
            await context.bot.send_message(
                config.ADMIN_ID,
                f"💰 *Nova venda!*\n"
                f"Plano: {plano['nome']}\n"
                f"Valor: R$ {config.PLANOS.get(pg.plano, {}).get('preco', 0):.2f}".replace(".", ",")
                + f"\nAssinante: `{telegram_id}`",
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
    return True


# =============================================================
#  TAREFAS AUTOMÁTICAS
# =============================================================
async def job_checar_pagamentos(context: ContextTypes.DEFAULT_TYPE):
    """Roda a cada 60s: confirma pagamentos pendentes das últimas 2 horas."""
    limite = agora() - timedelta(hours=2)
    with SessionLocal() as s:
        pendentes = (
            s.query(Pagamento).filter(Pagamento.status == "pending").all()
        )
    for pg in pendentes:
        if utc(pg.criado_em) < limite:
            with SessionLocal() as s:
                p = s.get(Pagamento, pg.mp_id)
                p.status = "expired"
                s.commit()
            continue
        await checar_e_ativar(pg.mp_id, context)


async def job_diario(context: ContextTypes.DEFAULT_TYPE):
    """Roda 1x por dia: envia lembretes e remove assinaturas vencidas."""
    hoje = agora()
    with SessionLocal() as s:
        ativos = s.query(Assinante).filter(Assinante.ativo == True).all()  # noqa

    for a in ativos:
        vence = utc(a.vence_em)
        if vence is None:
            continue

        # --- Assinatura vencida: remover do grupo ---
        if vence <= hoje:
            try:
                await context.bot.ban_chat_member(config.GROUP_ID, a.telegram_id)
                await context.bot.unban_chat_member(
                    config.GROUP_ID, a.telegram_id, only_if_banned=True
                )
            except Exception as e:
                log.error(f"Erro ao remover {a.telegram_id}: {e}")
            with SessionLocal() as s:
                x = s.get(Assinante, a.telegram_id)
                x.ativo = False
                s.commit()
            try:
                await context.bot.send_message(a.telegram_id, config.TEXTO_REMOVIDO)
            except Exception:
                pass
            if config.ADMIN_ID:
                try:
                    await context.bot.send_message(
                        config.ADMIN_ID,
                        f"👋 Assinante `{a.telegram_id}` removido (assinatura vencida).",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception:
                    pass
            continue

        # --- Perto de vencer: enviar lembrete ---
        dias_restantes = (vence - hoje).days
        if dias_restantes <= config.DIAS_AVISO_VENCIMENTO and not a.avisado:
            try:
                await context.bot.send_message(
                    a.telegram_id,
                    config.TEXTO_LEMBRETE.format(dias=max(dias_restantes, 1)),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception:
                pass
            with SessionLocal() as s:
                x = s.get(Assinante, a.telegram_id)
                x.avisado = True
                s.commit()


# =============================================================
#  INICIALIZAÇÃO
# =============================================================
def main():
    if not config.BOT_TOKEN:
        raise SystemExit("Configure a variável BOT_TOKEN no Railway.")
    iniciar_banco()

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CallbackQueryHandler(escolher_plano, pattern=r"^plano:"))
    app.add_handler(
        CallbackQueryHandler(verificar_pagamento_botao, pattern=r"^verificar:")
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, receber_email)
    )

    app.job_queue.run_repeating(job_checar_pagamentos, interval=60, first=15)
    app.job_queue.run_daily(job_diario, time=dtime(10, 0, tzinfo=FUSO_BR))

    log.info("Bot VIP iniciado! 🚀")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
