"""Fluxo principal de ponta a ponta: catálogo → clique → venda → decisão humana."""
from urllib.parse import parse_qs, urlsplit

from conftest import ADMIN, HOTTOK, WEBHOOK


def hotmart_event(event, transaction="HP123", sck="", commission=40.0):
    return {"event": event, "data": {
        "product": {"id": 999},
        "purchase": {"transaction": transaction, "price": {"value": 197.0, "currency_value": "BRL"},
                     "origin": {"sck": sck}, "approved_date": 1730000000000},
        "commissions": [{"value": 150.0, "source": "PRODUCER"}, {"value": commission, "source": "AFFILIATE"}],
    }}


def test_catalogo_publico_respeita_publicacao(client, catalogo):
    nichos = client.get("/public/nichos").json()
    assert [n["slug"] for n in nichos["data"]] == ["saude"]
    subs = client.get("/public/nichos/saude/subnichos").json()["data"]
    dores = client.get(f"/public/subnichos/{subs[0]['id']}/dores").json()["data"]
    sol = client.get(f"/public/dores/{dores[0]['id']}/solucoes").json()["data"]
    assert sol[0]["url"] == f"/r/{catalogo['oferta']['id']}"
    assert "destination_url" not in sol[0]  # link do parceiro nunca é exposto
    assert client.get("/public/ofertas").json()["total"] == 1


def test_despublicar_nicho_esconde_toda_a_arvore(admin, catalogo):
    admin.patch(f"/admin/catalogo/nichos/{catalogo['nicho']['id']}", json={"published": False})
    assert admin.get("/public/nichos").json()["total"] == 0
    assert admin.get(f"/public/dores/{catalogo['dor']['id']}/solucoes").status_code == 404


def test_publicacao_exige_pai_publicado_e_bloqueia_teste(admin):
    n = admin.post("/admin/catalogo/nichos", json={"title": "Teste", "slug": "teste-x"}).json()
    assert admin.patch(f"/admin/catalogo/nichos/{n['id']}", json={"published": True}).status_code == 409
    n2 = admin.post("/admin/catalogo/nichos", json={"title": "Finanças", "slug": "financas"}).json()
    s = admin.post("/admin/catalogo/subnichos", json={"title": "Renda", "slug": "renda", "parent_id": n2["id"]}).json()
    assert admin.patch(f"/admin/catalogo/subnichos/{s['id']}", json={"published": True}).status_code == 409


def test_redirecionamento_registra_clique_e_anexa_rastreio(client, catalogo):
    oferta, dor = catalogo["oferta"], catalogo["dor"]
    r = client.get(f"/r/{oferta['id']}?d={dor['id']}&utm_source=instagram")
    assert r.status_code == 302
    loc = urlsplit(r.headers["location"])
    assert loc.netloc == "go.hotmart.com"
    qs = parse_qs(loc.query)
    assert qs["ap"] == ["1"] and len(qs["sck"][0]) == 36
    m = client.get("/admin/metricas", headers={"Authorization": f"Bearer {ADMIN}"}).json()
    assert m["ofertas"][0]["cliques"] == 1
    assert m["dores"][0]["cliques"] == 1


def test_oferta_despublicada_ou_sistema_pausado_nao_redireciona(admin, catalogo):
    oid = catalogo["oferta"]["id"]
    admin.put("/admin/sistema", json={"ativo": False, "motivo": "revisão"})
    assert admin.get(f"/r/{oid}").status_code == 503
    admin.put("/admin/sistema", json={"ativo": True})
    admin.patch(f"/admin/ofertas/{oid}", json={"published": False})
    assert admin.get(f"/r/{oid}").status_code == 404
    assert admin.get("/r/nao-e-uuid").status_code == 422


def test_link_sem_https_e_rejeitado(admin):
    r = admin.post("/admin/ofertas", json={"title": "X", "destination_url": "javascript:alert(1)"})
    assert r.status_code == 422


def test_hotmart_venda_atribuida_idempotente_e_reembolso(client, catalogo):
    sck = parse_qs(urlsplit(client.get(f"/r/{catalogo['oferta']['id']}").headers["location"]).query)["sck"][0]
    h = {"X-HOTMART-HOTTOK": HOTTOK}
    assert client.post("/webhooks/hotmart", json=hotmart_event("PURCHASE_APPROVED", sck=sck), headers=h).json()["status"] == "registrado"
    # reenvio do mesmo evento não duplica
    assert client.post("/webhooks/hotmart", json=hotmart_event("PURCHASE_APPROVED", sck=sck), headers=h).json()["status"] == "duplicado"
    adm = {"Authorization": f"Bearer {ADMIN}"}
    conv = client.get("/admin/conversoes", headers=adm).json()["data"]
    assert len(conv) == 1 and conv[0]["oferta_id"] == catalogo["oferta"]["id"] and conv[0]["clique_id"] == sck
    assert float(conv[0]["commission_amount"]) == 40.0  # comissão do afiliado, não do produtor
    # reembolso atualiza a mesma venda; aprovação atrasada não desfaz o reembolso
    client.post("/webhooks/hotmart", json=hotmart_event("PURCHASE_REFUNDED"), headers=h)
    client.post("/webhooks/hotmart", json=hotmart_event("PURCHASE_APPROVED"), headers=h)
    conv = client.get("/admin/conversoes", headers=adm).json()["data"]
    assert len(conv) == 1 and conv[0]["status"] == "refunded"
    m = client.get("/admin/metricas", headers=adm).json()["ofertas"][0]
    assert m["vendas"] == 0 and m["reembolsos"] == 1 and m["receita"] == 0


def test_hotmart_rejeita_token_errado_e_ignora_evento_nao_financeiro(client):
    assert client.post("/webhooks/hotmart", json=hotmart_event("PURCHASE_APPROVED"),
                       headers={"X-HOTMART-HOTTOK": "errado"}).status_code == 401
    r = client.post("/webhooks/hotmart", json={"event": "CLUB_FIRST_ACCESS", "data": {}},
                    headers={"X-HOTMART-HOTTOK": HOTTOK})
    assert r.status_code == 200 and r.json()["status"] == "ignorado"


def test_hotmart_atribui_por_produto_sem_clique(client, catalogo):
    client.post("/webhooks/hotmart", json=hotmart_event("PURCHASE_APPROVED", "T2"), headers={"X-HOTMART-HOTTOK": HOTTOK})
    conv = client.get("/admin/conversoes", headers={"Authorization": f"Bearer {ADMIN}"}).json()["data"]
    assert conv[0]["oferta_id"] == catalogo["oferta"]["id"] and conv[0]["clique_id"] is None


def test_webhook_generico_e_csv(client, catalogo):
    body = {"platform": "eduzz", "external_id": "E1", "status": "approved", "commission_amount": 30,
            "oferta_id": catalogo["oferta"]["id"]}
    assert client.post("/webhooks/conversao", json=body).status_code == 401
    assert client.post("/webhooks/conversao", json=body, headers={"X-Webhook-Token": WEBHOOK}).json()["status"] == "registrado"
    csv_body = ("platform,external_id,status,commission_amount\n"
                "eduzz,E1,approved,30\n"      # já existe → duplicada
                "monetizze,M1,approved,12.5\n"
                "monetizze,M2,invalido,1\n")
    r = client.post("/admin/conversoes/importar", content=csv_body.encode(),
                    headers={"Authorization": f"Bearer {ADMIN}", "Content-Type": "text/csv"}).json()
    assert r["criadas"] == 1 and r["duplicadas"] == 1 and len(r["erros"]) == 1


def test_leads_com_consentimento(client, catalogo):
    dor = catalogo["dor"]["id"]
    assert client.post("/public/leads", json={"email": "a@b.com", "dor_id": dor}).status_code == 422
    assert client.post("/public/leads", json={"email": "invalido", "consent": True}).status_code == 422
    assert client.post("/public/leads", json={"email": "Ana@Exemplo.com", "dor_id": dor, "consent": True}).status_code == 201
    assert client.post("/public/leads", json={"email": "ana@exemplo.com", "dor_id": dor, "consent": True}).status_code == 201
    leads = client.get("/admin/leads", headers={"Authorization": f"Bearer {ADMIN}"}).json()["data"]
    assert len(leads) == 1 and leads[0]["email"] == "ana@exemplo.com"
    csv = client.get("/admin/leads.csv", headers={"Authorization": f"Bearer {ADMIN}"}).text
    assert "ana@exemplo.com" in csv and "Emagrecer" in csv


def test_demanda_sem_oferta_vira_oportunidade(admin, catalogo):
    admin.patch(f"/admin/ofertas/{catalogo['oferta']['id']}", json={"active": False})
    admin.post("/public/leads", json={"email": "x@y.com", "dor_id": catalogo["dor"]["id"], "consent": True})
    dores = admin.get("/admin/metricas").json()["dores"]
    assert dores[0]["oportunidade"] is True
    assert any("oportunidade" in f for f in admin.get("/admin/resumo").json()["frases"])


def test_decisao_so_tem_efeito_apos_aprovacao_humana(admin, catalogo):
    oid = catalogo["oferta"]["id"]
    for _ in range(20):  # 20 cliques, nenhuma venda → PAUSAR (2x o mínimo de 10)
        admin.get(f"/r/{oid}")
    assert admin.post("/admin/decisoes/gerar").json()["criadas"] == 1
    assert admin.post("/admin/decisoes/gerar").json()["criadas"] == 0  # não repete
    d = admin.get("/admin/decisoes?status=pendente").json()["data"][0]
    assert d["recomendacao"] == "PAUSAR"
    assert admin.get(f"/r/{oid}").status_code == 302  # ainda ativa: nada muda sozinho
    assert admin.post(f"/admin/decisoes/{d['id']}/aprovar", json={"nota": "ok"}).status_code == 200
    assert admin.get(f"/r/{oid}").status_code == 404
    assert admin.post(f"/admin/decisoes/{d['id']}/aprovar", json={}).status_code == 409
    acoes = [a["action"] for a in admin.get("/admin/auditoria").json()["data"]]
    assert "decisao.aprovada" in acoes and all(a["actor"] == "anderson" for a in admin.get("/admin/auditoria").json()["data"])


def test_escalar_aumenta_prioridade(admin, catalogo):
    oid = catalogo["oferta"]["id"]
    for i in range(10):
        admin.get(f"/r/{oid}")
    admin.post("/admin/conversoes", json={"platform": "hotmart", "external_id": "V1", "status": "approved",
                                          "commission_amount": 50, "oferta_id": oid})
    admin.post("/admin/decisoes/gerar")
    d = admin.get("/admin/decisoes?status=pendente").json()["data"][0]
    assert d["recomendacao"] == "ESCALAR"
    admin.post(f"/admin/decisoes/{d['id']}/aprovar", json={})
    vinc = admin.get("/admin/catalogo").json()["data"][0]["subnichos"][0]["dores"][0]["vinculos"][0]
    assert vinc["priority"] == 2


def test_admin_fechado_sem_token(client, settings):
    assert client.get("/admin/resumo").status_code == 401
    assert client.get("/admin/resumo", headers={"Authorization": "Bearer errado"}).status_code == 401
    assert client.put("/admin/sistema", json={"ativo": False}).status_code == 401
    settings.admin_tokens = {}
    assert client.get("/admin/resumo", headers={"Authorization": f"Bearer {ADMIN}"}).status_code == 503


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"
