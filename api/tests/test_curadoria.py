"""Curadoria: produtos de marcas conhecidas, com o ID de Associado, nas 6 áreas."""
from fastapi.testclient import TestClient

from app.curadoria import CURADORIA, aplicar
from app.main import create_app
from app.problemas import TEMAS


def test_curadoria_preenche_os_seis_temas_com_links_da_amazon(settings):
    settings.amazon_tag = "roboglobal-20"
    settings.lojas_confiaveis = []  # só curadoria vai ao público
    client = TestClient(create_app(settings, start_scheduler=False), follow_redirects=False)

    # todo problema do site tem 3 escolhas na curadoria
    slugs = {p["slug"] for t in TEMAS for p in t["problemas"]}
    assert slugs == set(CURADORIA) and all(len(v) == 3 for v in CURADORIA.values())

    temas = client.get("/public/problemas").json()["temas"]
    assert [t["slug"] for t in temas] == ["esporte", "saude", "bem-estar", "casa", "pet", "eletronicos"]
    pag = client.get("/public/problemas/som-para-reunir").json()["data"]
    titulos = [e["oferta"]["title"] for e in pag["escolhas"]]
    assert titulos == ["Caixa de som JBL Go 4", "Caixa de som JBL Flip 6", "Caixa de som JBL Charge 5"]
    assert pag["escolhas"][0]["motivo"]["pt"].startswith("Pequena")
    assert pag["escolhas"][0]["oferta"]["translations"]["en"]["title"] == "JBL Go 4 speaker"

    # o clique passa pelo rastreio e chega na Amazon com o ID de Associado
    r = client.get(pag["escolhas"][1]["oferta"]["url"], params={"utm_source": "instagram"})
    assert r.status_code in (302, 307)
    assert r.headers["location"].startswith("https://www.amazon.com.br/s?k=JBL+Flip+6&tag=roboglobal-20")

    # aplicar de novo não duplica nada
    with client.app.state.sessionmaker() as db:
        assert aplicar(db, settings)["ofertas_criadas"] == 0
    from app.models import Oferta
    with client.app.state.sessionmaker() as db:
        assert db.query(Oferta).filter(Oferta.platform == "amazon").count() == 3 * len(CURADORIA)
