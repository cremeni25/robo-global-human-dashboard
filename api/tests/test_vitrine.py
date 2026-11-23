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

    chamadas = []
    def fake_ia(sistema, conteudo):
        chamadas.append(conteudo)
        itens = [{"id": linha.split("\t")[0], "pt": "Fone sem fio " + linha.split("\t")[0][:4], "es": "Auricular"}
                 for linha in conteudo.splitlines()]
        return {"itens": itens, "_uso": {"entrada": 500, "saida": 300}}
    with client.app.state.sessionmaker() as db:
        r = traduzir_vitrine(db, s, fake_ia)
    assert r["titulos_traduzidos"] == 7 and len(chamadas) == 1
    item = client.get("/public/vitrine").json()["secoes"][0]["itens"][0]
    assert item["translations"]["pt"]["title"].startswith("Fone sem fio")
    with client.app.state.sessionmaker() as db:  # já traduzidos: não paga de novo
        assert traduzir_vitrine(db, s, fake_ia)["titulos_traduzidos"] == 0 and len(chamadas) == 1

    # Divulgação: cliques chegam com o canal e aparecem no relatório
    client.get(item["url"], params={"utm_source": "instagram", "utm_medium": "bio"})
    client.get(item["url"], params={"utm_source": "tiktok"})
    client.get(item["url"])
    canais = {c["canal"]: c for c in client.get("/admin/canais").json()["data"]}
    assert canais["instagram"]["cliques_total"] == 1 and canais["tiktok"]["cliques_30d"] == 1
    assert canais["direto"]["cliques_total"] == 1
