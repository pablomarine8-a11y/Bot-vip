# =============================================================
#  BANCO DE DADOS — você não precisa mexer neste arquivo.
# =============================================================
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

import config

# Railway fornece DATABASE_URL começando com "postgres://",
# mas o SQLAlchemy exige "postgresql://"
db_url = config.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


def agora_utc():
    return datetime.now(timezone.utc)


class Assinante(Base):
    __tablename__ = "assinantes"

    telegram_id = Column(BigInteger, primary_key=True)
    nome = Column(String, default="")
    username = Column(String, default="")
    email = Column(String, default="")
    plano = Column(String, default="")
    vence_em = Column(DateTime(timezone=True), nullable=True)
    ativo = Column(Boolean, default=False)
    avisado = Column(Boolean, default=False)  # já recebeu lembrete de vencimento


class Pagamento(Base):
    __tablename__ = "pagamentos"

    mp_id = Column(String, primary_key=True)  # id do pagamento no Mercado Pago
    telegram_id = Column(BigInteger)
    plano = Column(String)
    valor = Column(Float)
    status = Column(String, default="pending")  # pending / approved / expired
    criado_em = Column(DateTime(timezone=True), default=agora_utc)


def iniciar_banco():
    Base.metadata.create_all(engine)
