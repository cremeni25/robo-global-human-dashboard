"""Curadoria de natação e triathlon: marcas conhecidas, com os IDs de afiliado da Amazon e do Mercado Livre."""
from fastapi.testclient import TestClient

from app.curadoria import CURADORIA, REFERENCIAS, aplicar
from app.main import create_app
from app.problemas import TEMAS


def test_curadoria_natacao_e_triathlon(settings):
    settings.amazon_tag = "roboglobal-20"
    settings.lojas_confiaveis = []  # só curadoria vai ao público
    client = TestClient(create_app(settings, start_scheduler=False), follow_redirects=False)

    # todo problema do site tem 3 escolhas na curadoria
    slugs = {p["slug"] for t in TEMAS for p in t["problemas"]}
    assert slugs == set(CURADORIA) | set(REFERENCIAS) and all(len(v) == 3 for v in CURADORIA.values())
    assert all(c.split(":")[0] in CURADORIA for v in REFERENCIAS.values() for c in v)

    temas = client.get("/public/problemas").json()["temas"]
    assert [t["slug"] for t in temas] == ["natacao", "triathlon", "treino", "nutricao", "mente"]
    # nenhum produto aparece em duas páginas
    buscas = [it["busca"].lower() for itens in CURADORIA.values() for it in itens]
    assert len(buscas) == len(set(buscas))
    pag = client.get("/public/problemas/oculos-natacao").json()["data"]
    titulos = [e["oferta"]["title"] for e in pag["escolhas"]]
    assert titulos == ["Óculos de natação Hammerhead Vortex", "Óculos Speedo Vanquisher 2.0", "Óculos Arena Cobra Ultra Swipe"]
    assert pag["escolhas"][0]["oferta"]["translations"]["en"]["title"] == "Hammerhead Vortex goggles"

    # o clique passa pelo rastreio e chega na Amazon com o ID de Associado
    r = client.get(pag["escolhas"][1]["oferta"]["url"], params={"utm_source": "instagram"})
    assert r.status_code in (302, 307)
    assert r.headers["location"].endswith("Speedo+Vanquisher+2.0&tag=roboglobal-20")

    # produtos com link do Mercado Livre gerado mostram as duas lojas, com a etiqueta de afiliado
    creatina = client.get("/public/problemas/proteina-creatina").json()["data"]["escolhas"][0]["lojas"]
    assert [l["loja"] for l in creatina] == ["Amazon", "Mercado Livre"]
    from app.curadoria_ml import LINKS_ML
    assert client.get(creatina[1]["url"]).headers["location"] == LINKS_ML["creatina monohidratada Max Titanium 300g"]

    # aplicar de novo não duplica nada
    with client.app.state.sessionmaker() as db:
        assert aplicar(db, settings)["ofertas_criadas"] == 0
    from app.models import Oferta
    with client.app.state.sessionmaker() as db:
        assert db.query(Oferta).filter(Oferta.platform == "amazon").count() == 3 * len(CURADORIA)
        from app.curadoria_ml import LINKS_ML
        com_link = sum(1 for itens in CURADORIA.values() for it in itens if it["busca"] in LINKS_ML)
        assert db.query(Oferta).filter(Oferta.platform == "mercadolivre").count() == com_link
