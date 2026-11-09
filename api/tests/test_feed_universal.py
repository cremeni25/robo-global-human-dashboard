"""Conector universal: várias redes e lojas ao mesmo tempo, sem código por rede."""
import io
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from conftest import ADMIN
from app.aquisicao import executar_ciclo
from app.conectores import feed_universal as fu
from app.main import create_app

CJ_CSV = (
    "PROGRAMNAME;NAME;SKU;BUYURL;IMAGEURL;CURRENCY;PRICE;ADVERTISERCATEGORY;DESCRIPTION\n"
    "Loja Tech;Fone Bluetooth;A1;https://www.anrdoezrs.net/click-1-2?url=x;https://img/1.jpg;USD;49.90;Electronics > Audio;Fone sem fio\n"
    "Loja Tech;Carregador;A2;http://inseguro.example/x;;USD;9.90;Electronics;\n"  # http: descartado
)
GOOGLE_XML = """<?xml version="1.0"?>
<rss xmlns:g="http://base.google.com/ns/1.0" version="2.0"><channel>
<item><g:id>G1</g:id><title>Mochila de trilha 40L</title><link>https://loja.example/p/g1?aff=7</link>
<g:price>1.299,90 BRL</g:price><g:image_link>https://img/g1.jpg</g:image_link>
<g:product_type>Esporte &gt; Aventura</g:product_type><g:brand>Montanha</g:brand>
<g:shipping><g:price>20.00 BRL</g:price></g:shipping></item>
</channel></rss>"""
YML = """<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog><shop><offers>
<offer id="Y9" available="true"><name>Relógio inteligente</name><url>https://ad.admitad.com/g/abc/?ulp=x</url>
<price>899.00</price><currencyId>BRL</currencyId><picture>https://img/y9.jpg</picture></offer>
</offers></shop></yml_catalog>"""

FEEDS = {"https://cj.example/feed.csv": CJ_CSV, "https://merchant.example/google.xml": GOOGLE_XML,
         "https://admitad.example/yml.xml": YML}


class Resp(io.BufferedReader):
    def __init__(self, data):
        super().__init__(io.BytesIO(data.encode()))


def fake_fetch(request, timeout):
    return Resp(FEEDS[request.full_url])


def test_formatos_de_mercado():
    cj = list(fu.ler(Resp(CJ_CSV), {"rede": "cj"}))
    assert len(cj) == 1 and cj[0].merchant_name == "Loja Tech" and cj[0].price == Decimal("49.90") and cj[0].currency == "USD"
    g = list(fu.ler(Resp(GOOGLE_XML), {"rede": "google", "anunciante": "Loja Montanha"}))[0]
    assert g.price == Decimal("1299.90") and g.category == "Esporte > Aventura" and g.description.startswith("Montanha")
    y = list(fu.ler(Resp(YML), {"rede": "admitad"}))[0]
    assert y.product_id == "Y9" and y.image_url == "https://img/y9.jpg" and y.price == Decimal("899.00")


@pytest.fixture()
def multi(settings):
    settings.auto_aprovar_anunciantes = settings.auto_taxonomia = True
    app = create_app(settings, start_scheduler=False)
    c = TestClient(app, follow_redirects=False)
    c.headers.update({"Authorization": f"Bearer {ADMIN}"})
    return c, lambda: executar_ciclo(app.state.sessionmaker, settings, "teste", fake_fetch)


def test_varias_redes_ao_mesmo_tempo_sem_humano(multi):
    client, run = multi
    client.post("/admin/fontes", json={"rede": "cj", "url": "https://cj.example/feed.csv", "subid": "sid", "mercado": "US", "idioma": "en"})
    client.post("/admin/fontes", json={"rede": "google-loja", "url": "https://merchant.example/google.xml", "anunciante": "Loja Montanha"})
    client.post("/admin/fontes", json={"rede": "admitad", "url": "https://admitad.example/yml.xml", "subid": "subid"})
    assert client.post("/admin/fontes", json={"rede": "x", "url": "http://inseguro.example"}).status_code == 422
    listadas = client.get("/admin/fontes").json()["painel"]
    assert len(listadas) == 3 and all("aff=" not in f["url"] for f in listadas)  # URL mascarada

    r = run()
    assert [f.get("status", "ok") for f in r["etapas"]["fontes"]["resultado"]] == ["ok", "ok", "ok"]
    titulos = {o["title"] for o in client.get("/public/ofertas?limit=100").json()["data"]}
    assert titulos == {"Fone Bluetooth", "Mochila de trilha 40L", "Relógio inteligente"}
    nichos = {n["title"] for n in client.get("/public/nichos").json()["data"]}
    assert {"Electronics", "Esporte"} <= nichos  # taxonomia criada pelo agente
    fone = next(o for o in client.get("/public/ofertas?q=fone").json()["data"])
    loc = client.get(f"/r/{fone['id']}").headers["location"]
    assert "sid" in parse_qs(urlsplit(loc).query)  # subid da rede recebe o id do clique
    assert run()["etapas"]["fontes"]["resultado"][0]["novos"] == 0  # idempotente


def test_fonte_com_erro_nao_derruba_as_outras(multi):
    client, run = multi
    client.post("/admin/fontes", json={"rede": "quebrada", "url": "https://nao-existe.example/feed.csv"})
    client.post("/admin/fontes", json={"rede": "admitad", "url": "https://admitad.example/yml.xml"})
    res = run()["etapas"]["fontes"]["resultado"]
    assert res[0]["status"] == "falhou" and res[1]["novos"] == 1
