"""Conector universal de catálogos — qualquer rede, loja ou fornecedor.

Lê os formatos que praticamente todo o mercado exporta:
- CSV/TSV (vírgula, ponto e vírgula, tab ou barra vertical), com ou sem gzip/zip;
- XML no padrão Google Shopping / Merchant Center (RSS e Atom, namespace g:);
- XML YML (usado por Admitad e várias redes da Europa, Ásia e América Latina).

Com isso o Robô Global recebe catálogos de redes como CJ Affiliate, Impact,
Rakuten, Admitad, Webgains, Tradedoubler, Partnerize, Lomadee, Awin e de
qualquer loja ou fornecedor com feed de produtos, sem código novo por rede:
basta cadastrar a URL do feed (painel → Aquisição → Fontes).
"""
from __future__ import annotations

import csv
import gzip
import io
import re
import unicodedata
import zipfile
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator, Optional
from urllib.parse import urlsplit
from urllib.request import Request
from xml.etree.ElementTree import iterparse

from .awin import Fetch, ProdutoFeed, _default_fetch

MAX_ZIP = 300 * 1024 * 1024

CAMPOS = {
    "id": ("id", "sku", "product_id", "productid", "aw_product_id", "offer_id", "item_id", "merchant_product_id", "g:id"),
    "title": ("title", "name", "product_name", "productname", "model"),
    "link": ("affiliate_link", "aw_deep_link", "deeplink", "deep_link", "tracking_url", "trackingurl", "buyurl",
             "buy_url", "click_url", "clickurl", "promotion_link", "offer_link", "link", "url", "product_url", "producturl"),
    "price": ("sale_price", "search_price", "current_price", "currentprice", "price", "price_value", "retail_price"),
    "currency": ("currency", "currencyid", "currency_code"),
    "image": ("image_link", "image_url", "imageurl", "large_image", "merchant_image_url", "aw_image_url",
              "picture", "image", "thumbnail"),
    "category": ("product_type", "category_name", "advertisercategory", "merchant_category", "category",
                 "categoryid", "google_product_category", "category_path"),
    "description": ("description", "short_description", "product_short_description", "summary"),
    "merchant": ("merchant_name", "advertiser_name", "advertisername", "programname", "program_name",
                 "store", "shop_name", "seller", "vendor"),
    "brand": ("brand", "brand_name", "manufacturer"),
}
ITEM_TAGS = {"item", "entry", "offer", "product"}


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:80] or "loja"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower().replace("-", "_")


def _pick(record: dict[str, str], campo: str) -> str:
    for key in CAMPOS[campo]:
        value = (record.get(key) or "").strip()
        if value:
            return value
    return ""


def _preco(valor: str, moeda_padrao: str) -> tuple[Optional[Decimal], str]:
    """Aceita '99.90', '99,90', '1.299,90', '99.90 BRL', 'R$ 99,90'."""
    if not valor:
        return None, moeda_padrao
    moeda = moeda_padrao
    m = re.search(r"\b([A-Z]{3})\b", valor)
    if m:
        moeda = m.group(1)
    num = re.sub(r"[^0-9,.\-]", "", valor)
    if "," in num and "." in num:
        num = num.replace(".", "").replace(",", ".") if num.rfind(",") > num.rfind(".") else num.replace(",", "")
    elif "," in num:
        num = num.replace(",", ".")
    try:
        return Decimal(num).quantize(Decimal("0.01")), moeda
    except (InvalidOperation, ValueError):
        return None, moeda


def _produto(record: dict[str, str], fonte: dict[str, Any]) -> Optional[ProdutoFeed]:
    title, link = _pick(record, "title"), _pick(record, "link")
    if not title or not link:
        return None
    parts = urlsplit(link)
    if parts.scheme != "https" or not parts.netloc:
        return None
    merchant = fonte.get("anunciante") or _pick(record, "merchant") or fonte.get("rede", "loja")
    pid = _pick(record, "id") or link
    price, currency = _preco(_pick(record, "price"), (_pick(record, "currency") or fonte.get("moeda") or "BRL").upper()[:3])
    brand = _pick(record, "brand")
    return ProdutoFeed(
        merchant_id=slug(merchant), merchant_name=merchant[:200], product_id=pid[:120], name=title[:200], url=link,
        price=price, currency=currency[:3], category=_pick(record, "category")[:300],
        image_url=_pick(record, "image")[:2000],
        description=((brand + " · ") if brand else "") + _pick(record, "description")[:1800],
        language=str(fonte.get("idioma") or "pt")[:10], raw={},
    )


def _abrir(stream) -> io.BufferedIOBase:
    buf = stream if hasattr(stream, "peek") else io.BufferedReader(stream)
    head = buf.peek(4)[:4]
    if head[:2] == b"\x1f\x8b":
        return io.BufferedReader(gzip.GzipFile(fileobj=buf))  # type: ignore[arg-type]
    if head == b"PK\x03\x04":
        data = buf.read(MAX_ZIP + 1)
        if len(data) > MAX_ZIP:
            raise ValueError("arquivo zip grande demais")
        z = zipfile.ZipFile(io.BytesIO(data))
        nome = max(z.infolist(), key=lambda i: i.file_size).filename
        return io.BufferedReader(z.open(nome))  # type: ignore[arg-type]
    return buf


def ler(stream, fonte: dict[str, Any], *, max_rows: int = 1_000_000) -> Iterator[ProdutoFeed]:
    buf = _abrir(stream)
    inicio = buf.peek(512)[:512].lstrip(b"\xef\xbb\xbf \t\r\n")
    gerador = _ler_xml(buf) if inicio.startswith(b"<") else _ler_csv(buf)
    for i, record in enumerate(gerador):
        if i >= max_rows:
            break
        p = _produto(record, fonte)
        if p:
            yield p


def _ler_csv(buf) -> Iterator[dict[str, str]]:
    text = io.TextIOWrapper(buf, encoding="utf-8-sig", errors="replace", newline="")
    amostra = text.readline()
    delim = max((",", ";", "\t", "|"), key=amostra.count)
    header = next(csv.reader([amostra], delimiter=delim))
    fields = [h.strip().lower().replace(" ", "_").replace("-", "_") for h in header]
    for row in csv.reader(text, delimiter=delim):
        yield {k: v for k, v in zip(fields, row)}


def _ler_xml(buf) -> Iterator[dict[str, str]]:
    record: Optional[dict[str, str]] = None
    depth = 0
    for event, el in iterparse(buf, events=("start", "end")):
        tag = _local(el.tag)
        if event == "start":
            if record is None and tag in ITEM_TAGS:
                record, depth = {}, 0
            elif record is not None:
                depth += 1
            continue
        if record is None:
            continue
        if tag in ITEM_TAGS and depth == 0:
            for k, v in el.attrib.items():  # YML: <offer id="...">
                record.setdefault(_local(k), v)
            yield record
            record = None
            el.clear()
            continue
        depth -= 1
        if depth != 0:  # só filhos diretos do item (ignora g:shipping > g:price etc.)
            continue
        value = (el.text or "").strip() or el.attrib.get("href", "")
        if value and tag not in record:
            record[tag] = value
        if tag == "link" and el.attrib.get("href") and "link" not in record:
            record["link"] = el.attrib["href"]


def baixar(url: str, fetch: Fetch = _default_fetch):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("a URL do feed precisa ser https")
    return fetch(Request(url, headers={"User-Agent": "RoboGlobal/2 (+https://www.roboglobal.com.br)"}), 180)
