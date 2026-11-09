"""Conector Awin (origem: core-v1, branch rebuild/core-v1 do repositório robo).

Três fontes oficiais da Awin, todas somente leitura:
- feed de produtos (CSV, gz ou não): catálogo completo de cada anunciante;
- API de programas: de quais anunciantes você é afiliado aprovado (joined);
- API de transações: vendas e comissões, com o clickref do clique de origem.
Nenhuma inscrição em programa é feita automaticamente.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterator, Optional
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

FEED_HOSTS = {"productdata.awin.com", "ui.awin.com"}
API_BASE = "https://api.awin.com"
CLICKREF_PARAM = "clickref"  # parâmetro de rastreio aceito nos links awin1.com

Fetch = Callable[[Request, float], Any]


class AwinError(ValueError):
    pass


def _default_fetch(request: Request, timeout: float):
    return urlopen(request, timeout=timeout)


@dataclass
class ProdutoFeed:
    merchant_id: str
    merchant_name: str
    product_id: str
    name: str
    url: str
    price: Optional[Decimal]
    currency: str
    category: str
    image_url: str
    description: str
    language: str
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def external_id(self) -> str:
        return f"{self.merchant_id}:{self.product_id}"


def _price(value: str | None) -> Optional[Decimal]:
    if not value:
        return None
    try:
        return Decimal(str(value).strip().replace(",", ".")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _first(record: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = (record.get(key) or "").strip()
        if value:
            return value
    return ""


def normalizar_url_feed(url: str) -> str:
    """Aceita só hosts oficiais de feed e remove o filtro de conteúdo adulto
    que a Awin inclui por padrão em algumas URLs geradas."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in FEED_HOSTS or parts.username or parts.password:
        raise AwinError("host de feed nao autorizado")
    segments = parts.path.split("/")
    kept, i = [], 0
    while i < len(segments):
        if segments[i].lower() == "adultcontent" and i + 1 < len(segments):
            i += 2
            continue
        kept.append(segments[i])
        i += 1
    return urlunsplit((parts.scheme, parts.netloc, quote("/".join(kept), safe="/%:@-._~"), parts.query, parts.fragment))


def ler_feed(stream: io.BufferedIOBase, *, max_rows: int = 500_000) -> Iterator[ProdutoFeed]:
    """Lê o CSV em fluxo (não carrega o arquivo inteiro na memória)."""
    buffered = stream if hasattr(stream, "peek") else io.BufferedReader(stream)  # type: ignore[arg-type]
    if buffered.peek(2)[:2] == b"\x1f\x8b":
        buffered = gzip.GzipFile(fileobj=buffered)  # type: ignore[assignment]
    text = io.TextIOWrapper(buffered, encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text)
    if not reader.fieldnames:
        raise AwinError("feed sem cabecalho")
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        r = {str(k): str(v or "") for k, v in row.items() if k is not None}
        merchant = _first(r, "merchant_id", "advertiser_id", "aw_merchant_id")
        product = _first(r, "aw_product_id", "id", "merchant_product_id")
        name = _first(r, "product_name", "title")
        url = _first(r, "aw_deep_link", "link")
        if not (merchant and product and name and url):
            continue
        p = urlsplit(url)
        if p.scheme != "https" or not p.hostname:
            continue
        yield ProdutoFeed(
            merchant_id=merchant, merchant_name=_first(r, "merchant_name", "advertiser_name", "brand"),
            product_id=product, name=name[:200], url=url,
            price=_price(_first(r, "search_price", "price", "sale_price")),
            currency=(_first(r, "currency") or "BRL").upper()[:3],
            category=" > ".join(x for x in (_first(r, "category_name", "product_type"), _first(r, "merchant_category")) if x)[:300],
            image_url=_first(r, "merchant_image_url", "aw_image_url", "large_image", "image_link")[:2000],
            description=_first(r, "description", "product_short_description")[:2000],
            language=(_first(r, "language") or "pt")[:10],
            raw={k: v for k, v in r.items() if v and k in ("merchant_name", "category_name", "merchant_category", "brand_name", "in_stock")},
        )


def baixar_feed(url: str, fetch: Fetch = _default_fetch):
    request = Request(normalizar_url_feed(url), headers={"User-Agent": "RoboGlobal/2"})
    response = fetch(request, 120)
    final = getattr(response, "geturl", lambda: url)()
    if urlsplit(final).hostname not in FEED_HOSTS:
        raise AwinError("redirecionamento inesperado do feed")
    return response


class AwinClient:
    def __init__(self, publisher_id: str, token: str, fetch: Fetch = _default_fetch):
        if not str(publisher_id).isdigit() or not token:
            raise AwinError("AWIN_PUBLISHER_ID e AWIN_API_TOKEN sao obrigatorios")
        self.publisher_id = str(publisher_id)
        self._token = token
        self._fetch = fetch

    def _get(self, path: str) -> Any:
        request = Request(API_BASE + path, headers={"Authorization": "Bearer " + self._token,
                                                    "Accept": "application/json"})
        with self._fetch(request, 60) as response:
            return json.load(response)

    def programas(self, relationship: str = "joined") -> list[dict[str, Any]]:
        if relationship not in {"joined", "pending", "suspended", "rejected", "notjoined"}:
            raise AwinError("relationship invalido")
        data = self._get(f"/publishers/{self.publisher_id}/programmes?relationship={relationship}")
        if not isinstance(data, list):
            raise AwinError("resposta inesperada de programas")
        return [p for p in data if isinstance(p, dict) and str(p.get("id", "")).isdigit()]

    def transacoes(self, inicio: datetime, fim: datetime) -> list[dict[str, Any]]:
        """A API aceita janelas de até 31 dias; divide automaticamente."""
        out: list[dict[str, Any]] = []
        cursor = inicio
        while cursor < fim:
            stop = min(cursor + timedelta(days=30), fim)
            fmt = "%Y-%m-%dT%H:%M:%S"
            data = self._get(f"/publishers/{self.publisher_id}/transactions/?startDate={cursor.strftime(fmt)}"
                             f"&endDate={stop.strftime(fmt)}&timezone=UTC&dateType=transaction")
            if not isinstance(data, list):
                raise AwinError("resposta inesperada de transacoes")
            out.extend(t for t in data if isinstance(t, dict))
            cursor = stop
        return out


AWIN_STATUS = {"pending": "pending", "approved": "approved", "declined": "canceled", "deleted": "canceled"}


def normalizar_transacao(t: dict[str, Any]) -> Optional[dict[str, Any]]:
    status = AWIN_STATUS.get(str(t.get("commissionStatus", "")).lower())
    if not status or not t.get("id"):
        return None
    commission = t.get("commissionAmount") or {}
    sale = t.get("saleAmount") or {}
    refs = t.get("clickRefs") or {}
    when = None
    try:
        when = datetime.fromisoformat(str(t.get("transactionDate", "")).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
    except ValueError:
        when = None
    return {
        "external_id": str(t["id"]), "status": status,
        "commission": _price(str(commission.get("amount", ""))) or Decimal("0"),
        "gross": _price(str(sale.get("amount", ""))) or Decimal("0"),
        "currency": str(commission.get("currency") or sale.get("currency") or "BRL").upper()[:3],
        "click_id": str(refs.get("clickRef") or "")[:36] if isinstance(refs, dict) else "",
        "advertiser_id": str(t.get("advertiserId") or ""),
        "occurred_at": when,
    }
