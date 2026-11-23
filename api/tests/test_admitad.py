"""Admitad: lojas aprovadas → feeds → produtos → vendas, sem link manual."""
import io
import json

import pytest
from fastapi.testclient import TestClient

from conftest import ADMIN
from app.aquisicao import executar_ciclo
from app.conectores import admitad
from app.main import create_app

YML = """<?xml version="1.0" encoding="UTF-8"?><yml_catalog><shop>
<categories><category id="c1">Casa</category><category id="c2" parentId="c1">Cozinha</category></categories>
<offers><offer id="P1"><name>Air fryer 5L</name><url>https://ad.admitad.com/g/abc/?ulp=x</url><price>399.90</price>
<currencyId>BRL</currencyId><categoryId>c2</categoryId><picture>https://img/p1.jpg</picture></offer></offers>
</shop></yml_catalog>"""


class R(io.BufferedReader):
    def __init__(self, data):
        super().__init__(io.BytesIO(data.encode() if isinstance(data, str) else data))


class FakeAdmitad:
    def __init__(self):
        self.vendas = []
        self.chamadas = []

    def __call__(self, req, timeout):
        u = req.full_url
        self.chamadas.append(u)
        if u.endswith("/token/"):
            assert req.get_header("Authorization") == "Basic B64"
            return R(json.dumps({"access_token": "tok"}))
        assert "export.admitad.com" in u or req.get_header("Authorization") == "Bearer tok"
        if "/websites/" in u:
            return R(json.dumps({"results": [{"id": 3025594, "name": "Robô Global", "site_url": "https://roboglobal.com.br"}],
                                 "_meta": {"count": 1}}))
        if "/advcampaigns/website/3025594/" in u:
            return R(json.dumps({"results": [
                {"id": 1, "name": "Casa Fácil BR", "connection_status": "active", "feeds_info": [
                    {"name": "Old EN", "xml_link": "https://export.admitad.com/x?feed_id=9&code=z", "admitad_last_update": "2020-01-01T00:00:00"},
                    {"name": "Main PT", "xml_link": "https://export.admitad.com/x?feed_id=10&code=z", "admitad_last_update": "2026-11-20T00:00:00"}]},
                {"id": 2, "name": "Sem Feed WW", "connection_status": "active", "feeds_info": []},
                {"id": 3, "name": "Pendente", "connection_status": "pending", "feeds_info": [
                    {"name": "x", "xml_link": "https://export.admitad.com/x?feed_id=11"}]},
            ], "_meta": {"count": 3}}))
        if "export.admitad.com" in u:
            assert "feed_id=10" in u and "currency=BRL" in u
            return R(YML)
        if "/statistics/actions/" in u:
            return R(json.dumps({"results": self.vendas, "_meta": {"count": len(self.vendas)}}))
        raise AssertionError(u)


@pytest.fixture()
def ambiente(settings):
    settings.admitad_base64, settings.admitad_client_id = "B64", "cid"
    settings.auto_aprovar_anunciantes = settings.auto_taxonomia = True
    app = create_app(settings, start_scheduler=False)
    c = TestClient(app, follow_redirects=False)
    c.headers.update({"Authorization": f"Bearer {ADMIN}"})
    fake = FakeAdmitad()
    return c, fake, lambda: executar_ciclo(app.state.sessionmaker, settings, "teste", fake)


def test_escolhe_feed_pt_recente_e_ignora_antigo():
    loja = {"feeds_info": [{"name": "Old", "xml_link": "https://e/x?feed_id=1", "admitad_last_update": "2019-01-01T00:00:00"},
                           {"name": "Main PT", "xml_link": "https://e/x?feed_id=2"}]}
    url = admitad.escolher_feed(loja)
    assert "feed_id=2" in url and "currency=BRL" in url and "format=xml" in url
    assert admitad.escolher_feed({"feeds_info": []}) is None


def test_ciclo_descobre_lojas_importa_e_publica_sem_link_manual(ambiente):
    c, fake, run = ambiente
    r = run()
    info = r["etapas"]["admitad_lojas"]
    assert info["lojas_aprovadas"] == 2 and info["com_feed"] == 1 and info["sem_feed"] == ["Sem Feed WW"]
    assert info["espacos_usados"] == [3025594]
    assert r["etapas"]["fontes"]["resultado"][0]["novos"] == 1
    ofertas = c.get("/public/ofertas").json()["data"]
    assert [o["title"] for o in ofertas] == ["Air fryer 5L"]
    assert [n["title"] for n in c.get("/public/nichos").json()["data"]] == ["Casa"]
    loc = c.get(f"/r/{ofertas[0]['id']}").headers["location"]
    assert "subid=" in loc


def test_vendas_admitad_entram_atribuidas_ao_clique(ambiente):
    c, fake, run = ambiente
    run()
    oferta = c.get("/public/ofertas").json()["data"][0]
    from urllib.parse import parse_qs, urlsplit
    subid = parse_qs(urlsplit(c.get(f"/r/{oferta['id']}").headers["location"]).query)["subid"][0]
    fake.vendas = [{"action_id": 777, "status": "pending", "payment": "12.30", "cart": "399.90",
                    "currency": "BRL", "subid": subid, "action_date": "2026-11-22 10:00:00", "advcampaign_name": "Casa Fácil BR"}]
    assert run()["etapas"]["admitad_vendas"]["novas"] == 1
    fake.vendas[0]["status"] = "approved"
    assert run()["etapas"]["admitad_vendas"]["atualizadas"] == 1
    venda = c.get("/admin/conversoes").json()["data"][0]
    assert venda["status"] == "approved" and venda["oferta_id"] == oferta["id"] and venda["source"] == "admitad_api"


def test_nao_duplica_loja_ja_cadastrada_a_mao(ambiente):
    c, fake, run = ambiente
    c.post("/admin/fontes", json={"rede": "admitad", "url": "https://export.admitad.com/x?feed_id=10&code=z",
                                  "anunciante": "Casa Fácil", "subid": "subid"})
    r = run()
    assert r["etapas"]["admitad_lojas"]["com_feed"] == 0
    assert r["etapas"]["fontes"]["total"] == 1


def test_usa_id_do_link_quando_espaco_em_analise_nao_aparece(ambiente):
    c, fake, run = ambiente
    original = fake.__call__

    class SemEspacos(FakeAdmitad):
        def __call__(self, req, timeout):
            if "/websites/" in req.full_url and "api.admitad.com" in req.full_url:
                return R(json.dumps({"results": [], "_meta": {"count": 0}}))
            return FakeAdmitad.__call__(self, req, timeout)
    sem = SemEspacos()
    c.post("/admin/fontes", json={"rede": "admitad", "url": "https://export.admitad.com/en/webmaster/websites/3025594/products/export_adv_products/?feed_id=99&currency=BRL",
                                  "anunciante": "Outra", "subid": "subid"})
    from app.aquisicao import executar_ciclo
    r = executar_ciclo(c.app.state.sessionmaker, c.app.state.settings, "teste", sem)
    info = r["etapas"]["admitad_lojas"]
    assert info["espacos_api"] == 0 and info["espacos_usados"] == [3025594] and info["com_feed"] == 1
