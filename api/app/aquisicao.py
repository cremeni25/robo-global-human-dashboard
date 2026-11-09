"""Ciclo de aquisição automática — o "motor" que dispensa cadastro manual.

A cada ciclo (padrão: 6 h, ou sob demanda no painel):
1. importa os feeds de produtos (milhares de itens), cria/atualiza anunciantes e
   ofertas, e desativa o que saiu do feed;
2. liga produtos novos às dores pelas regras de categoria (definidas uma vez);
3. confere na rede de quais anunciantes você é afiliado aprovado;
4. sincroniza vendas e comissões, atribuindo ao clique de origem.

A única decisão humana é por ANUNCIANTE (revisar termos uma vez), nunca por produto.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .conectores import awin
from .conversions import ConversaoIn, registrar
from .core import auditar
from .models import Anunciante, Configuracao, DorOferta, MapeamentoCategoria, Oferta, new_id, utcnow

log = logging.getLogger("robo_global.aquisicao")
ESTADO_KEY = "aquisicao"
_lock = threading.Lock()


# ------------------------------------------------------------------ importação

def importar_produtos(db: Session, produtos: Iterable[awin.ProdutoFeed], *, platform: str = "awin",
                      batch: int = 1000) -> dict[str, int]:
    inicio = utcnow()
    anunciantes = {a.external_id: a for a in db.scalars(select(Anunciante).where(Anunciante.platform == platform))}
    existentes = {o.external_product_id: o for o in db.scalars(select(Oferta).where(Oferta.platform == platform))}
    vistos: set[str] = set()
    tocados: set[str] = set()
    novos: list[str] = []
    resumo = {"lidos": 0, "novos": 0, "atualizados": 0, "duplicados": 0, "desativados": 0, "anunciantes_novos": 0}

    for n, p in enumerate(produtos, start=1):
        resumo["lidos"] += 1
        key = p.external_id
        if key in vistos:
            resumo["duplicados"] += 1
            continue
        vistos.add(key)
        a = anunciantes.get(p.merchant_id)
        if a is None:
            a = Anunciante(id=new_id(), platform=platform, external_id=p.merchant_id,
                           name=p.merchant_name or f"Anunciante {p.merchant_id}",
                           membership="unknown", approved=False, auto_publish=True)
            db.add(a)
            anunciantes[p.merchant_id] = a
            resumo["anunciantes_novos"] += 1
        elif p.merchant_name and a.name.startswith("Anunciante "):
            a.name = p.merchant_name
        tocados.add(a.id)
        o = existentes.get(key)
        fields = dict(title=p.name, destination_url=p.url, price=p.price, currency=p.currency,
                      category=p.category, image_url=p.image_url, description=p.description,
                      provider=a.name, language=p.language, last_seen_at=inicio, active=True)
        if o is None:
            o = Oferta(id=new_id(), platform=platform, external_product_id=key, kind="afiliado",
                       source=f"{platform}_feed", subid_param=awin.CLICKREF_PARAM,
                       anunciante_id=a.id, published=a.auto_publish, market="BR", **fields)
            db.add(o)
            existentes[key] = o
            novos.append(o.id)
            resumo["novos"] += 1
        else:
            for k, v in fields.items():
                setattr(o, k, v)
            resumo["atualizados"] += 1
        if n % batch == 0:
            db.commit()
    db.commit()

    # Produto que sumiu do feed do seu anunciante = saiu de linha: tira do ar.
    if tocados:
        r = db.execute(update(Oferta).where(
            Oferta.platform == platform, Oferta.anunciante_id.in_(tocados), Oferta.active.is_(True),
            (Oferta.last_seen_at.is_(None)) | (Oferta.last_seen_at < inicio),
        ).values(active=False).execution_options(synchronize_session=False))
        resumo["desativados"] = r.rowcount or 0
        db.commit()
        db.expire_all()
    resumo["vinculos_criados"] = aplicar_mapeamentos(db)
    return resumo


def aplicar_mapeamentos(db: Session, mapeamento_id: Optional[str] = None) -> int:
    """Liga ofertas às dores pelas regras de termo. Idempotente."""
    q = select(MapeamentoCategoria)
    if mapeamento_id:
        q = q.where(MapeamentoCategoria.id == mapeamento_id)
    criados = 0
    for m in db.scalars(q).all():
        coluna = Oferta.title if m.campo == "title" else Oferta.category
        ja = select(DorOferta.oferta_id).where(DorOferta.dor_id == m.dor_id)
        ids = db.scalars(select(Oferta.id).where(coluna.ilike(f"%{m.termo}%"), Oferta.id.not_in(ja))).all()
        for oid in ids:
            db.add(DorOferta(id=new_id(), dor_id=m.dor_id, oferta_id=oid, priority=1))
            criados += 1
        db.commit()
    return criados


# ------------------------------------------------------------------ rede

def sincronizar_programas(db: Session, client: awin.AwinClient) -> dict[str, int]:
    joined = client.programas("joined")
    ids = {str(p["id"]): p for p in joined}
    agora = utcnow()
    novos = 0
    for ext, p in ids.items():
        a = db.scalars(select(Anunciante).where(Anunciante.platform == "awin", Anunciante.external_id == ext)).first()
        if a is None:
            a = Anunciante(id=new_id(), platform="awin", external_id=ext, name=str(p.get("name") or f"Anunciante {ext}"),
                           approved=False, auto_publish=True)
            db.add(a)
            novos += 1
        elif p.get("name"):
            a.name = str(p["name"])[:200]
        a.membership, a.membership_checked_at = "joined", agora
    # Resposta válida: quem não está em "joined" não está aprovado (hoje).
    db.execute(update(Anunciante).where(Anunciante.platform == "awin", Anunciante.external_id.not_in(list(ids) or [""]))
               .values(membership="not_joined", membership_checked_at=agora).execution_options(synchronize_session=False))
    db.commit()
    db.expire_all()
    return {"afiliacoes_aprovadas": len(ids), "anunciantes_novos": novos}


def sincronizar_vendas(db: Session, client: awin.AwinClient, dias: int = 35) -> dict[str, int]:
    fim = datetime.now(timezone.utc)
    resumo = {"transacoes": 0, "novas": 0, "atualizadas": 0}
    for t in client.transacoes(fim - timedelta(days=dias), fim):
        n = awin.normalizar_transacao(t)
        if not n:
            continue
        resumo["transacoes"] += 1
        r = registrar(db, ConversaoIn(
            platform="awin", external_id=n["external_id"], status=n["status"],
            gross_amount=n["gross"], commission_amount=n["commission"], currency=n["currency"],
            occurred_at=n["occurred_at"], click_id=n["click_id"], source="awin_api",
            product_id="", raw={k: str(v) for k, v in t.items() if k in (
                "id", "advertiserId", "commissionStatus", "transactionDate", "clickRefs")},
        ))
        if r.criada:
            resumo["novas"] += 1
        elif r.alterada:
            resumo["atualizadas"] += 1
    return resumo


# ------------------------------------------------------------------ ciclo

def executar_ciclo(SessionLocal: sessionmaker, s: Settings, actor: str = "agendador",
                   fetch: awin.Fetch = awin._default_fetch) -> dict[str, Any]:
    if not _lock.acquire(blocking=False):
        return {"status": "em_andamento"}
    inicio = utcnow()
    etapas: dict[str, Any] = {}
    try:
        with SessionLocal() as db:
            # 1. feeds
            if s.awin_feed_urls:
                totais: dict[str, int] = {}
                erros = 0
                for url in s.awin_feed_urls:
                    try:
                        with awin.baixar_feed(url, fetch) as resp:
                            r = importar_produtos(db, awin.ler_feed(resp))
                        for k, v in r.items():
                            totais[k] = totais.get(k, 0) + v
                    except Exception as exc:  # um feed ruim não derruba os outros
                        db.rollback()
                        erros += 1
                        log.warning("feed falhou: %s", type(exc).__name__)
                etapas["feeds"] = {"fontes": len(s.awin_feed_urls), "falhas": erros, **totais}
            else:
                etapas["feeds"] = {"status": "nao_configurado", "falta": "AWIN_FEED_URL"}
            # 2. rede (afiliações e vendas)
            if s.awin_publisher_id and s.awin_api_token:
                client = awin.AwinClient(s.awin_publisher_id, s.awin_api_token, fetch)
                for nome, func in (("afiliacoes", sincronizar_programas), ("vendas", sincronizar_vendas)):
                    try:
                        etapas[nome] = func(db, client)
                    except Exception as exc:
                        db.rollback()
                        status = getattr(exc, "code", None)
                        etapas[nome] = {"status": "falhou", "erro": type(exc).__name__, "http": status,
                                        "dica": "Token da API Awin invalido ou expirado: gere outro em ui.awin.com > API credentials"
                                        if status in (401, 403) else ""}
            else:
                etapas["afiliacoes"] = etapas["vendas"] = {"status": "nao_configurado",
                                                           "falta": "AWIN_PUBLISHER_ID e AWIN_API_TOKEN"}
            # 3. agentes autônomos (aprovação, taxonomia, decisões)
            try:
                from .agentes import executar as executar_agentes
                etapas["agentes"] = executar_agentes(db, s)
            except Exception as exc:
                db.rollback()
                etapas["agentes"] = {"status": "falhou", "erro": type(exc).__name__}
            resultado = {"inicio": inicio.isoformat(), "fim": utcnow().isoformat(), "etapas": etapas}
            row = db.get(Configuracao, ESTADO_KEY)
            if row:
                row.value = resultado
            else:
                db.add(Configuracao(key=ESTADO_KEY, value=resultado))
            auditar(db, actor, "aquisicao.ciclo", "aquisicao", "", {"etapas": list(etapas)})
            db.commit()
            log.info("ciclo de aquisicao: %s", {k: (v.get("status") or "ok") for k, v in etapas.items()})
            return resultado
    finally:
        _lock.release()


def iniciar_agendador(SessionLocal: sessionmaker, s: Settings) -> None:
    if not s.aquisicao_automatica or not (s.awin_feed_urls or s.awin_api_token):
        log.info("aquisicao automatica desligada ou sem fontes configuradas")
        return

    def loop() -> None:
        time.sleep(30)  # deixa o servidor subir primeiro
        while True:
            try:
                executar_ciclo(SessionLocal, s)
            except Exception as exc:
                log.error("ciclo falhou: %s", type(exc).__name__)
            time.sleep(max(0.25, s.aquisicao_intervalo_horas) * 3600)

    threading.Thread(target=loop, name="robo-aquisicao", daemon=True).start()
