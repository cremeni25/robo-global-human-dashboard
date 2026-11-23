"""Agente de catálogo com IA: categorias em inglês viram temas em português, sem humano."""
from app.agente_catalogo import organizar_com_ia
from test_aquisicao import motor, produto  # noqa: F401  (fixture)


def tema(chave, nicho, sub, dor, palavras):
    t = {"chave": chave, "palavras_pt": palavras}
    for l, suf in (("pt", ""), ("en", " EN"), ("es", " ES")):
        t.update({f"nicho_{l}": nicho + suf, f"subnicho_{l}": sub + suf, f"dor_{l}": dor + suf,
                  f"descricao_{l}": "Descrição" + suf})
    return t


class FakeClaude:
    def __init__(self):
        self.chamadas = []

    def __call__(self, sistema, conteudo):
        self.chamadas.append(conteudo)
        cats = conteudo.split("uma por linha):\n", 1)[1].splitlines()
        temas, atrib = [], []
        for c in cats:
            if "Headphones" in c:
                if "som-fones" not in conteudo:
                    temas.append(tema("som-fones", "Som e Música", "Fones", "Ouvir música sem fio", "fone, fone de ouvido"))
                atrib.append({"categoria": c, "chave": "som-fones"})
            elif "Yoga" in c:
                temas.append(tema("esporte-yoga", "Esporte em Casa", "Yoga", "Praticar yoga em casa", "yoga, tapete"))
                atrib.append({"categoria": c, "chave": "esporte-yoga"})
            else:
                atrib.append({"categoria": c, "chave": "chave-inexistente"})  # ignorada com segurança
        return {"novos_temas": temas, "atribuicoes": atrib, "_uso": {"entrada": 100, "saida": 50}}


def test_ia_traduz_agrupa_e_busca_em_portugues(motor):  # noqa: F811
    client, fake, run = motor
    s = client.app.state.settings
    s.auto_aprovar_anunciantes = s.auto_taxonomia = True
    fake.rows = [produto("1", "111", "Earbuds X1", "Electronics > Headphones > Earbud Headphones"),
                 produto("2", "111", "Over-ear Z", "Electronics > Headphones > Over-ear Headphones"),
                 produto("3", "111", "Yoga mat", "Sports > Fitness > Yoga")]
    run()  # sem chave: organizador simples cria temas em inglês
    assert {n["title"] for n in client.get("/public/nichos").json()["data"]} == {"Electronics", "Sports"}
    assert client.get("/public/ofertas", params={"q": "fone"}).json()["total"] == 0

    ia = FakeClaude()
    with client.app.state.sessionmaker() as db:
        r = organizar_com_ia(db, s, ia)
    assert r["categorias_enviadas"] == 3 and r["temas_novos"] == 2 and r["produtos_movidos"] == 3
    nichos = client.get("/public/nichos").json()["data"]
    assert {n["title"] for n in nichos} == {"Som e Música", "Esporte em Casa"}  # temas em inglês recolhidos
    som = next(n for n in nichos if n["title"] == "Som e Música")
    assert som["translations"]["en"]["title"] == "Som e Música EN"
    subs = client.get(f"/public/nichos/{som['slug']}/subnichos").json()["data"]
    dores = client.get(f"/public/subnichos/{subs[0]['id']}/dores").json()["data"]
    assert [d["title"] for d in dores] == ["Ouvir música sem fio"]
    sol = client.get(f"/public/dores/{dores[0]['id']}/solucoes").json()["data"]
    assert {o["title"] for o in sol} == {"Earbuds X1", "Over-ear Z"}
    # Busca em português encontra produtos cadastrados em inglês
    assert client.get("/public/ofertas", params={"q": "fone"}).json()["total"] == 2

    # Custo controlado: nada é reenviado; categoria nova de produto novo vai sozinha
    with client.app.state.sessionmaker() as db:
        assert organizar_com_ia(db, s, ia)["categorias_enviadas"] == 0
    fake.rows.append(produto("4", "111", "Sport buds", "Electronics > Headphones > Sports Headphones"))
    s.auto_taxonomia = False
    run()
    with client.app.state.sessionmaker() as db:
        r = organizar_com_ia(db, s, ia)
    assert r["categorias_enviadas"] == 1 and r["temas_novos"] == 0
    assert client.get("/public/ofertas", params={"q": "fone"}).json()["total"] == 3


def test_sem_chave_o_agente_nao_roda(settings):
    from app.db import make_engine
    from app.models import Base
    from sqlalchemy.orm import Session
    eng = make_engine("sqlite://")
    Base.metadata.create_all(eng)
    with Session(eng) as db:
        assert organizar_com_ia(db, settings) == {"status": "sem_chave"}
