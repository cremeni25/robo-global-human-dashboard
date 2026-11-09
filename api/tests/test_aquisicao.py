"""Motor de aquisição: feed → anunciantes → regras → afiliação → vendas, sem cadastro manual."""
import csv
import gzip
import io
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from conftest import ADMIN, HOTTOK
from app.aquisicao import executar_ciclo
from app.conectores.awin import AwinError, normalizar_url_feed
from app.main import create_app

FEED = "https://productdata.awin.com/datafeed/download/apikey/KEY/adultcontent/1/fid/123/columns/x/format/csv/"


def feed_bytes(rows):
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=["aw_product_id", "product_name", "aw_deep_link", "merchant_id",
                                        "merchant_name", "search_price", "currency", "category_name",
                                        "merchant_image_url", "description"])
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return gzip.compress(out.getvalue().encode())


def produto(pid, merchant, name, category="Fitness"):
    return {"aw_product_id": pid, "product_name": name, "merchant_id": merchant,
            "aw_deep_link": f"https://www.awin1.com/pclick.php?p={pid}&a=999&m={merchant}",
            "merchant_name": "Loja A" if merchant == "111" else "Loja B", "search_price": "99.90",
            "currency": "BRL", "category_name": category, "merchant_image_url": "https://img/x.jpg",
            "description": "Produto real"}


class FakeResp(io.BufferedReader):
    def __init__(self, data, url):
        super().__init__(io.BytesIO(data))
        self._url = url

    def geturl(self):
        return self._url


class FakeAwin:
    def __init__(self):
        self.rows = [produto("1", "111", "Tapete de yoga"), produto("2", "111", "Halteres 5kg"),
                     produto("2", "111", "Halteres 5kg"), produto("3", "222", "Panela", "Cozinha")]
        self.joined = [{"id": 111, "name": "Loja A"}]
        self.transactions = []
        self.requests = []

    def __call__(self, request, timeout):
        url = request.full_url
        self.requests.append(url)
        if "productdata.awin.com" in url:
            return FakeResp(feed_bytes(self.rows), url)
        if "/programmes" in url:
            return FakeResp(json.dumps(self.joined).encode(), url)
        if "/transactions/" in url:
            return FakeResp(json.dumps(self.transactions).encode(), url)
        raise AssertionError(url)


@pytest.fixture()
def motor(settings):
    settings.awin_feed_urls = [FEED]
    settings.awin_publisher_id = "999"
    settings.awin_api_token = "token"
    app = create_app(settings, start_scheduler=False)
    client = TestClient(app, follow_redirects=False)
    client.headers.update({"Authorization": f"Bearer {ADMIN}"})
    fake = FakeAwin()
    run = lambda: executar_ciclo(app.state.sessionmaker, settings, "teste", fake)  # noqa: E731
    return client, fake, run


def test_url_do_feed_sem_filtro_adulto_e_host_restrito():
    assert "adultcontent" not in normalizar_url_feed(FEED)
    with pytest.raises(AwinError):
        normalizar_url_feed("https://evil.example.com/feed.csv")


def test_ciclo_importa_e_so_publica_anunciante_liberado(motor):
    client, fake, run = motor
    r = run()
    feeds = r["etapas"]["feeds"]
    assert feeds["novos"] == 3 and feeds["duplicados"] == 1 and feeds["anunciantes_novos"] == 2
    assert r["etapas"]["afiliacoes"]["afiliacoes_aprovadas"] == 1
    assert all("adultcontent" not in u for u in fake.requests)
    # importado, mas ninguém aprovou os termos ainda: nada vai ao ar
    assert client.get("/public/ofertas").json()["total"] == 0
    anunciantes = {a["external_id"]: a for a in client.get("/admin/anunciantes").json()["data"]}
    assert anunciantes["111"]["membership"] == "joined" and anunciantes["222"]["membership"] == "not_joined"
    assert anunciantes["111"]["produtos_ativos"] == 2
    # UMA aprovação humana por anunciante libera todos os produtos dele
    client.patch(f"/admin/anunciantes/{anunciantes['111']['id']}", json={"approved": True})
    client.patch(f"/admin/anunciantes/{anunciantes['222']['id']}", json={"approved": True})
    publico = client.get("/public/ofertas").json()
    assert publico["total"] == 2  # Loja B aprovada por você, mas a rede não confirmou a afiliação
    assert {o["title"] for o in publico["data"]} == {"Tapete de yoga", "Halteres 5kg"}
    assert publico["data"][0]["price"] == 99.9 and publico["data"][0]["image_url"]
    assert client.get("/public/ofertas?q=yoga").json()["total"] == 1
    assert client.get("/public/ofertas?limit=1&page=2").json()["data"][0]["title"] == "Tapete de yoga"


def criar_dor(client):
    n = client.post("/admin/catalogo/nichos", json={"title": "Saúde", "slug": "saude"}).json()
    sub = client.post("/admin/catalogo/subnichos", json={"title": "Exercício", "slug": "exercicio", "parent_id": n["id"]}).json()
    d = client.post("/admin/catalogo/dores", json={"title": "Treinar em casa", "slug": "treinar-em-casa", "parent_id": sub["id"]}).json()
    for nivel, item in (("nichos", n), ("subnichos", sub), ("dores", d)):
        client.patch(f"/admin/catalogo/{nivel}/{item['id']}", json={"published": True})
    return d["id"]


def test_regra_de_categoria_liga_produtos_a_dor_agora_e_no_futuro(motor):
    client, fake, run = motor
    run()
    a = next(x for x in client.get("/admin/anunciantes").json()["data"] if x["external_id"] == "111")
    client.patch(f"/admin/anunciantes/{a['id']}", json={"approved": True})
    cats = {c["category"]: c for c in client.get("/admin/categorias").json()["data"]}
    assert cats["Fitness"]["sem_dor"] == 2
    dor = criar_dor(client)
    resp = client.post("/admin/mapeamentos", json={"termo": "fitness", "dor_id": dor})
    assert resp.status_code == 201, resp.text
    assert resp.json()["vinculos_criados"] == 2
    titulos = {o["title"] for o in client.get(f"/public/dores/{dor}/solucoes").json()["data"]}
    assert {"Tapete de yoga", "Halteres 5kg"} <= titulos
    fake.rows.append(produto("4", "111", "Corda de pular"))
    run()  # produto novo no feed entra sozinho na dor certa
    titulos = {o["title"] for o in client.get(f"/public/dores/{dor}/solucoes").json()["data"]}
    assert "Corda de pular" in titulos


def test_produto_que_sai_do_feed_sai_do_ar_e_venda_awin_e_atribuida(motor):
    client, fake, run = motor
    run()
    a = next(x for x in client.get("/admin/anunciantes").json()["data"] if x["external_id"] == "111")
    client.patch(f"/admin/anunciantes/{a['id']}", json={"approved": True})
    oferta = next(o for o in client.get("/public/ofertas").json()["data"] if o["title"] == "Tapete de yoga")
    loc = client.get(f"/r/{oferta['id']}").headers["location"]
    clickref = parse_qs(urlsplit(loc).query)["clickref"][0]
    fake.rows = [r for r in fake.rows if r["product_name"] != "Halteres 5kg"]
    fake.transactions = [{"id": 9001, "commissionStatus": "approved", "advertiserId": 111,
                          "commissionAmount": {"amount": 12.5, "currency": "BRL"},
                          "saleAmount": {"amount": 99.9, "currency": "BRL"},
                          "clickRefs": {"clickRef": clickref}, "transactionDate": "2026-11-08T10:00:00"}]
    r = run()
    assert r["etapas"]["feeds"]["desativados"] == 1
    assert r["etapas"]["vendas"]["novas"] == 1
    assert [o["title"] for o in client.get("/public/ofertas").json()["data"]] == ["Tapete de yoga"]
    venda = client.get("/admin/conversoes").json()["data"][0]
    assert venda["oferta_id"] == oferta["id"] and venda["clique_id"] == clickref and venda["source"] == "awin_api"
    fake.transactions[0]["commissionStatus"] = "declined"
    run()  # recusa posterior atualiza a mesma venda
    assert client.get("/admin/conversoes").json()["data"][0]["status"] == "canceled"


def test_falha_na_api_awin_nao_derruba_o_ciclo(motor):
    client, fake, run = motor
    import urllib.error

    def quebrado(request, timeout):
        if "api.awin.com" in request.full_url:
            raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)
        return fake(request, timeout)
    r = executar_ciclo(client.app.state.sessionmaker, client.app.state.settings, "teste", quebrado)
    assert r["etapas"]["feeds"]["novos"] == 3
    assert r["etapas"]["afiliacoes"]["status"] == "falhou" and "Token" in r["etapas"]["afiliacoes"]["dica"]
    assert client.get("/admin/aquisicao").json()["ultimo_ciclo"]["etapas"]["afiliacoes"]["http"] == 401


def test_compatibilidade_com_links_e_webhook_do_core_v1(client, admin, catalogo):
    from app.models import Alias
    with client.app.state.sessionmaker() as db:
        db.add(Alias(id="659339cf-ab62-444b-9bcc-676e7ba680d1", oferta_id=catalogo["oferta"]["id"]))
        db.commit()
    assert client.get("/r/659339cf-ab62-444b-9bcc-676e7ba680d1").status_code == 302
    assert client.get(f"/go/{catalogo['oferta']['id']}").status_code == 302
    body = {"event": "PURCHASE_APPROVED", "data": {"product": {"id": 999}, "purchase": {
        "transaction": "HPX", "price": {"value": 10}, "tracking": {"source_sck": "abc"}},
        "commissions": [{"value": 3, "source": "AFFILIATE"}]}}
    r = client.post("/v1/webhooks/hotmart", json=body, headers={"X-HOTMART-HOTTOK": HOTTOK})
    assert r.json()["status"] == "registrado"
