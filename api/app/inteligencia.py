"""Inteligência do Robô Global: métricas reais e recomendações explicáveis.

A máquina mede e recomenda; a pessoa aprova. Nenhuma recomendação muda o
sistema antes da aprovação humana (ver aplicar_decisao).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import Settings
from .core import auditar, dor_visivel, oferta_visivel
from .models import Clique, Conversao, Decisao, Dor, DorOferta, Lead, Oferta, utcnow

RECOMENDACOES = ("COLETAR_DADOS", "ESCALAR", "MANTER", "OTIMIZAR", "PAUSAR")


def _since(days: int | None) -> datetime | None:
    return datetime.now(timezone.utc) - timedelta(days=days) if days else None


def metricas_ofertas(db: Session, days: int | None = None) -> list[dict[str, Any]]:
    since = _since(days)
    q_clicks = select(Clique.oferta_id, func.count()).group_by(Clique.oferta_id)
    q_conv = select(Conversao.oferta_id, Conversao.status, func.count(),
                    func.coalesce(func.sum(Conversao.commission_amount), 0),
                    func.coalesce(func.sum(Conversao.gross_amount), 0)
                    ).where(Conversao.oferta_id.is_not(None)).group_by(Conversao.oferta_id, Conversao.status)
    if since:
        q_clicks = q_clicks.where(Clique.created_at >= since)
        q_conv = q_conv.where(Conversao.occurred_at >= since)
    clicks = dict(db.execute(q_clicks).all())
    conv: dict[str, dict[str, Any]] = {}
    for oferta_id, status, count, commission, gross in db.execute(q_conv).all():
        conv.setdefault(oferta_id, {})[status] = (int(count), Decimal(commission), Decimal(gross))

    rows = []
    for o in db.scalars(select(Oferta).order_by(Oferta.title)):
        c = conv.get(o.id, {})
        approved, receita, bruto = c.get("approved", (0, Decimal(0), Decimal(0)))
        devolvidas = sum(c.get(s, (0,))[0] for s in ("refunded", "chargeback"))
        pendentes = c.get("pending", (0,))[0]
        n_clicks = int(clicks.get(o.id, 0))
        rows.append({
            "oferta_id": o.id, "title": o.title, "kind": o.kind, "platform": o.platform,
            "active": o.active, "published": o.published, "visivel": oferta_visivel(o),
            "cliques": n_clicks, "vendas": approved, "pendentes": pendentes,
            "reembolsos": devolvidas,
            "receita": float(receita), "faturamento_bruto": float(bruto),
            "taxa_conversao": round(approved / n_clicks, 4) if n_clicks else 0.0,
            "epc": round(float(receita) / n_clicks, 4) if n_clicks else 0.0,
            "taxa_reembolso": round(devolvidas / (approved + devolvidas), 4) if (approved + devolvidas) else 0.0,
        })
    return rows


def demanda_dores(db: Session) -> list[dict[str, Any]]:
    """Sinais de demanda por dor: cliques, leads e ofertas disponíveis.
    Dores com pessoas interessadas e sem oferta são oportunidades reais
    (buscar afiliação, criar produto ou serviço próprio)."""
    clicks = dict(db.execute(select(Clique.dor_id, func.count()).where(
        Clique.dor_id.is_not(None)).group_by(Clique.dor_id)).all())
    leads = dict(db.execute(select(Lead.dor_id, func.count()).where(
        Lead.dor_id.is_not(None)).group_by(Lead.dor_id)).all())
    rows = []
    for d in db.scalars(select(Dor)):
        ofertas = [v.oferta for v in d.vinculos if oferta_visivel(v.oferta)]
        n_leads, n_clicks = int(leads.get(d.id, 0)), int(clicks.get(d.id, 0))
        rows.append({
            "dor_id": d.id, "title": d.title, "visivel": dor_visivel(d),
            "subnicho": d.subnicho.title, "nicho": d.subnicho.nicho.title,
            "cliques": n_clicks, "leads": n_leads, "ofertas_visiveis": len(ofertas),
            "oportunidade": n_leads > 0 and not ofertas,
        })
    rows.sort(key=lambda r: (not r["oportunidade"], -(r["leads"] * 5 + r["cliques"])))
    return rows


def recomendar(m: dict[str, Any], s: Settings) -> tuple[str, str]:
    cliques, vendas, devol = m["cliques"], m["vendas"], m["reembolsos"]
    if vendas + devol >= 3 and m["taxa_reembolso"] > s.taxa_reembolso_max:
        return "PAUSAR", (f"Taxa de reembolso de {m['taxa_reembolso']:.0%} acima do limite de "
                          f"{s.taxa_reembolso_max:.0%}: a oferta pode estar prejudicando a confiança.")
    if cliques < s.min_cliques_decisao and vendas == 0:
        return "COLETAR_DADOS", (f"{cliques} cliques ainda não bastam para decidir "
                                 f"(mínimo {s.min_cliques_decisao}). Continue divulgando.")
    if vendas == 0:
        if cliques >= 2 * s.min_cliques_decisao:
            return "PAUSAR", f"{cliques} cliques e nenhuma venda: o público não está comprando esta oferta."
        return "OTIMIZAR", (f"{cliques} cliques sem venda. Revise o texto, a dor vinculada "
                            "ou a página do produtor antes de investir mais.")
    if m["epc"] >= s.epc_alvo:
        return "ESCALAR", (f"Cada clique rende em média {m['epc']:.2f} (meta {s.epc_alvo:.2f}). "
                           "Vale aumentar a divulgação e a prioridade.")
    return "MANTER", (f"Gera vendas ({vendas}), mas o ganho por clique ({m['epc']:.2f}) está abaixo "
                      f"da meta de {s.epc_alvo:.2f}.")


def gerar_decisoes(db: Session, s: Settings, actor: str) -> list[Decisao]:
    criadas = []
    for m in metricas_ofertas(db):
        if not m["active"]:
            continue
        rec, motivo = recomendar(m, s)
        pendente = db.scalars(select(Decisao).where(
            Decisao.oferta_id == m["oferta_id"], Decisao.status == "pendente")).first()
        if pendente and pendente.recomendacao == rec:
            continue
        if pendente:
            pendente.status = "substituida"
        if rec in ("COLETAR_DADOS", "MANTER"):
            # Nada a fazer: não ocupa a fila humana com "continue como está".
            continue
        d = Decisao(oferta_id=m["oferta_id"], recomendacao=rec, motivo=motivo, metricas=m)
        db.add(d)
        criadas.append(d)
    auditar(db, actor, "decisoes.geradas", "decisao", "", {"quantidade": len(criadas)})
    db.commit()
    return criadas


def aplicar_decisao(db: Session, d: Decisao, *, aprovar: bool, actor: str, nota: str = "") -> Decisao:
    if d.status != "pendente":
        raise ValueError("Decisao ja tratada")
    d.status = "aprovada" if aprovar else "rejeitada"
    d.decided_at, d.decided_by, d.nota = utcnow(), actor, nota
    efeito = "nenhum"
    if aprovar:
        oferta = db.get(Oferta, d.oferta_id)
        if d.recomendacao == "PAUSAR" and oferta:
            oferta.active = False
            efeito = "oferta desativada"
        elif d.recomendacao == "ESCALAR":
            for v in db.scalars(select(DorOferta).where(DorOferta.oferta_id == d.oferta_id)):
                v.priority += 1
            efeito = "prioridade aumentada nas dores vinculadas"
    auditar(db, actor, f"decisao.{d.status}", "decisao", d.id,
            {"recomendacao": d.recomendacao, "efeito": efeito, "nota": nota})
    db.commit()
    return d


def resumo_humano(db: Session, s: Settings) -> dict[str, Any]:
    """Leitura humana do sistema — frases claras, baseadas só em dados reais."""
    m30 = metricas_ofertas(db, days=30)
    cliques = sum(r["cliques"] for r in m30)
    vendas = sum(r["vendas"] for r in m30)
    receita = sum(r["receita"] for r in m30)
    reembolsos = sum(r["reembolsos"] for r in m30)
    leads_30 = db.scalar(select(func.count()).select_from(Lead).where(Lead.created_at >= _since(30))) or 0
    pendentes = db.scalar(select(func.count()).select_from(Decisao).where(Decisao.status == "pendente")) or 0
    nao_atribuidas = db.scalar(select(func.count()).select_from(Conversao).where(Conversao.oferta_id.is_(None))) or 0
    visiveis = sum(1 for r in m30 if r["visivel"])
    oportunidades = [d for d in demanda_dores(db) if d["oportunidade"]]

    frases = []
    if visiveis == 0:
        frases.append("Nenhuma oferta está visível ao público. Cadastre e publique ofertas para começar a monetizar.")
    else:
        frases.append(f"{visiveis} oferta(s) visível(is) ao público.")
    if cliques == 0:
        frases.append("Ainda não houve cliques nos últimos 30 dias. O próximo passo é levar pessoas ao site (divulgação).")
    else:
        frases.append(f"Nos últimos 30 dias: {cliques} cliques, {vendas} venda(s) aprovada(s) e "
                      f"{receita:.2f} em comissões aprovadas.")
    if reembolsos:
        frases.append(f"{reembolsos} reembolso(s) ou chargeback(s) no período — acompanhe a qualidade das ofertas.")
    if leads_30:
        frases.append(f"{leads_30} pessoa(s) pediram para ser avisadas sobre soluções.")
    if oportunidades:
        frases.append(f"{len(oportunidades)} dor(es) têm pessoas interessadas e nenhuma oferta: oportunidade direta.")
    if nao_atribuidas:
        frases.append(f"{nao_atribuidas} venda(s) sem oferta associada — confira o id do produto nas ofertas.")
    if pendentes:
        frases.append(f"{pendentes} recomendação(ões) aguardando sua decisão.")

    return {
        "sistema": None,  # preenchido pela rota
        "periodo_dias": 30,
        "totais": {"cliques": cliques, "vendas": vendas, "receita": round(receita, 2),
                   "reembolsos": reembolsos, "leads": leads_30, "ofertas_visiveis": visiveis,
                   "decisoes_pendentes": pendentes, "vendas_nao_atribuidas": nao_atribuidas},
        "frases": frases,
    }
