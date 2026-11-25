"""Vitrine pública, títulos em português e resultado por canal de divulgação."""
from app.agente_catalogo import traduzir_vitrine
from app import vitrine
from test_aquisicao import motor, produto  # noqa: F401


def test_vitrine_titulos_e_canais(motor):  # noqa: F811
    client, fake, run = motor
    s = client.app.state.settings
    s.auto_aprovar_anunciantes = s.auto_taxonomia = True
    fake.rows = [produto(str(i), "111", f"Wireless Earbuds Model {i}", "Electronics > Headphones > Earbuds")
                 for i in range(1, 7)] + [produto("99", "111", "Cheap Phone Case", "Electronics > Headphones > Earbuds")]
    fake.rows[-1]["search_price"] = "19.90"
    run()
    vitrine.limpar_cache()
    v = client.get("/public/vitrine").json()
    assert len(v["secoes"]) == 1 and len(v["secoes"][0]["itens"]) == 7
    assert all(o["url"].startswith("/r/") and o["image_url"] for o in v["secoes"][0]["itens"])
    assert [o["title"] for o in v["achados"]] == ["Cheap Phone Case"]  # só o que custa até R$ 50

    # Página de problema: produtos escolhidos no painel (curadoria) vão ao ar com 3 escolhas
    from app import problemas
    assert client.get("/public/problemas").json()["temas"] == []  # sem curadoria, nada no ar
    ids3 = [o["id"] for o in client.get("/public/ofertas", params={"q": "Earbuds"}).json()["data"]][:3]
    assert client.put("/admin/problemas/medir-treinos", json={"ofertas": ids3}).json()["ofertas"] == ids3
    temas = client.get("/public/problemas").json()["temas"]
    assert [t["slug"] for t in temas] == ["treino"]  # temas sem produto ficam fora
    pag = client.get("/public/problemas/medir-treinos").json()["data"]
    assert [e["nivel"]["chave"] for e in pag["escolhas"]] == ["comecar", "equilibrio", "completa"]
    assert len(pag["considerar"]) == 3 and pag["tema_titulo"]["pt"] == "Treino e recuperação"
    assert client.get("/public/problemas/ansiedade-prova").status_code == 404

    chamadas = []
    def fake_ia(sistema, conteudo):
        chamadas.append(conteudo)
        itens = [{"id": linha.split("\t")[0], "pt": "Fone sem fio " + linha.split("\t")[0][:4], "es": "Auricular"}
                 for linha in conteudo.splitlines()]
        return {"itens": itens, "_uso": {"entrada": 500, "saida": 300}}
    with client.app.state.sessionmaker() as db:
        r = traduzir_vitrine(db, s, fake_ia)
    assert r["titulos_traduzidos"] == 3 and len(chamadas) == 1
    item = client.get("/public/problemas/medir-treinos").json()["data"]["escolhas"][0]["oferta"]
    assert item["translations"]["pt"]["title"].startswith("Fone sem fio")
    with client.app.state.sessionmaker() as db:  # já traduzidos: não paga de novo
        assert traduzir_vitrine(db, s, fake_ia)["titulos_traduzidos"] == 0 and len(chamadas) == 1

    # Painel: fixar produtos à mão numa página (ex.: link da Amazon cadastrado em Ofertas)
    ids = [e["oferta"]["id"] for e in pag["escolhas"]][::-1][:2]
    assert client.put("/admin/problemas/medir-treinos", json={"ofertas": ids}).json()["ofertas"] == ids
    pag2 = client.get("/public/problemas/medir-treinos").json()["data"]
    assert [e["oferta"]["id"] for e in pag2["escolhas"]] == ids
    painel = {p["slug"]: p for p in client.get("/admin/problemas").json()["data"]}
    assert painel["medir-treinos"]["no_ar"] and not painel["oculos-natacao"]["no_ar"]

    # Loja fora da lista de confiáveis não aparece ao público (escolha fixada à mão é respeitada)
    client.put("/admin/problemas/medir-treinos", json={"ofertas": []})
    s.lojas_confiaveis = []
    problemas.limpar_cache()
    vitrine.limpar_cache()
    assert client.get("/public/ofertas").json()["total"] == 0
    assert client.get("/public/problemas").json()["temas"] == []
    s.lojas_confiaveis = ["Loja A"]

    # Divulgação: cliques chegam com o canal e aparecem no relatório
    client.get(item["url"], params={"utm_source": "instagram", "utm_medium": "bio"})
    client.get(item["url"], params={"utm_source": "tiktok"})
    client.get(item["url"])
    canais = {c["canal"]: c for c in client.get("/admin/canais").json()["data"]}
    assert canais["instagram"]["cliques_total"] == 1 and canais["tiktok"]["cliques_30d"] == 1
    assert canais["direto"]["cliques_total"] == 1
