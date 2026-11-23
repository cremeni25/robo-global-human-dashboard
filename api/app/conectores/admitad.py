"""Conector Admitad: descobre sozinho as lojas que aprovaram você, o feed de
produtos de cada uma e as vendas (estatísticas) — sem gerar link à mão.

Credenciais (Admitad → perfil → API): ADMITAD_CLIENT_ID, ADMITAD_CLIENT_SECRET
e ADMITAD_BASE64 (o cabeçalho base64 pronto que a própria Admitad mostra).
Somente leitura: nenhuma inscrição em programa é feita automaticamente.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request

from .awin import Fetch, _default_fetch

API = "https://api.admitad.com"
SCOPES = "advcampaigns_for_website websites statistics"
STATUS = {"approved": "approved", "approved_but_stalled": "approved", "pending": "pending",
          "declined": "canceled", "canceled": "canceled", "cancelled": "canceled"}


class AdmitadError(ValueError):
    pass


def _dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v if v not in (None, "") else "0")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


class AdmitadClient:
    def __init__(self, base64: str, client_id: str, fetch: Fetch = _default_fetch):
        if not base64 or not client_id:
            raise AdmitadError("ADMITAD_BASE64 e ADMITAD_CLIENT_ID sao obrigatorios")
        self._b64 = base64.strip().removeprefix("Basic ").strip()
        self._cid = client_id.strip()
        self._fetch = fetch
        self._token: Optional[str] = None

    def _token_get(self) -> str:
        if self._token:
            return self._token
        body = urlencode({"grant_type": "client_credentials", "client_id": self._cid, "scope": SCOPES}).encode()
        req = Request(API + "/token/", data=body, method="POST", headers={
            "Authorization": "Basic " + self._b64, "Content-Type": "application/x-www-form-urlencoded"})
        with self._fetch(req, 30) as r:
            data = json.load(r)
        token = data.get("access_token") if isinstance(data, dict) else None
        if not token:
            raise AdmitadError("token nao retornado pela Admitad")
        self._token = token
        return token

    def _get(self, path: str) -> Any:
        req = Request(API + path, headers={"Authorization": "Bearer " + self._token_get(), "Accept": "application/json"})
        with self._fetch(req, 60) as r:
            return json.load(r)

    def _paginado(self, path: str, limite: int = 2000) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        sep = "&" if "?" in path else "?"
        offset = 0
        while offset < limite:
            data = self._get(f"{path}{sep}limit=500&offset={offset}")
            results = data.get("results", []) if isinstance(data, dict) else []
            out.extend(r for r in results if isinstance(r, dict))
            total = (data.get("_meta") or {}).get("count", len(out)) if isinstance(data, dict) else len(out)
            offset += 500
            if not results or offset >= total:
                break
        return out

    def espacos(self) -> list[dict[str, Any]]:
        for path in ("/websites/v2/", "/websites/"):
            try:
                return self._paginado(path)
            except Exception:  # versões diferentes da API
                continue
        raise AdmitadError("nao foi possivel listar os espacos publicitarios")

    def lojas_aprovadas(self, website_id: int) -> list[dict[str, Any]]:
        lojas = self._paginado(f"/advcampaigns/website/{website_id}/")
        return [c for c in lojas if str(c.get("connection_status", "active")).lower() == "active"]

    def vendas(self, dias: int = 35) -> list[dict[str, Any]]:
        fim = datetime.now(timezone.utc)
        ini = fim - timedelta(days=dias)
        return self._paginado(f"/statistics/actions/?date_start={ini:%d.%m.%Y}&date_end={fim:%d.%m.%Y}", limite=10000)


def _com_moeda(url: str, moeda: str = "BRL") -> str:
    p = urlsplit(url)
    q = dict(parse_qsl(p.query, keep_blank_values=True))
    q.setdefault("currency", moeda)
    q.setdefault("format", "xml")
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), p.fragment))


def escolher_feed(loja: dict[str, Any]) -> Optional[str]:
    """Escolhe o feed da loja: prefere o em português/Brasil; ignora feeds parados há mais de 1 ano."""
    feeds = [f for f in (loja.get("feeds_info") or []) if isinstance(f, dict) and f.get("xml_link")]
    agora = datetime.now(timezone.utc)

    def recente(f: dict[str, Any]) -> bool:
        raw = str(f.get("admitad_last_update") or f.get("advertiser_last_update") or "")
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return agora - dt < timedelta(days=365)
        except ValueError:
            return True

    feeds = [f for f in feeds if recente(f)]
    if feeds:
        pt = [f for f in feeds if re.search(r"\b(pt|br|brasil|brazil|portug)", str(f.get("name", "")), re.I)]
        return _com_moeda(str((pt or feeds)[0]["xml_link"]))
    link = loja.get("products_xml_link")
    return _com_moeda(str(link)) if link else None


def normalizar_venda(a: dict[str, Any]) -> Optional[dict[str, Any]]:
    status = STATUS.get(str(a.get("status", "")).lower())
    if not status or not a.get("action_id"):
        return None
    quando = None
    try:
        quando = datetime.fromisoformat(str(a.get("action_date", "")).replace(" ", "T"))
        quando = quando if quando.tzinfo else quando.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    return {"external_id": str(a["action_id"]), "status": status, "commission": _dec(a.get("payment")),
            "gross": _dec(a.get("cart")), "currency": str(a.get("currency") or "BRL").upper()[:3],
            "click_id": str(a.get("subid") or "")[:36], "occurred_at": quando,
            "loja": str(a.get("advcampaign_name") or "")}
