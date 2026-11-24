"""Achados da semana (WhatsApp/e-mail com consentimento) e "Isso te ajudou?"."""


def test_inscricao_whatsapp_email_sem_duplicar(client, admin):
    ok = {"canal": "whatsapp", "contato": "(21) 99876-5432", "consent": True, "origem": "inicio", "utm_source": "instagram"}
    assert client.post("/public/inscricoes", json=ok).status_code == 201
    assert client.post("/public/inscricoes", json={**ok, "contato": "21998765432"}).status_code == 201  # mesmo número
    assert client.post("/public/inscricoes", json={"canal": "email", "contato": "Ana@Exemplo.com", "consent": True}).status_code == 201
    assert client.post("/public/inscricoes", json={**ok, "consent": False}).status_code == 422
    assert client.post("/public/inscricoes", json={**ok, "contato": "123"}).status_code == 422
    assert client.post("/public/inscricoes", json={**ok, "contato": "21911112222", "website": "spam"}).status_code == 201
    r = admin.get("/admin/inscricoes").json()
    assert r["total"] == 2 and r["por_canal"] == {"whatsapp": 1, "email": 1}
    contatos = {x["contato"] for x in r["data"]}
    assert contatos == {"+5521998765432", "ana@exemplo.com"}
    csv = admin.get("/admin/inscricoes", params={"formato": "csv"}).text
    assert "+5521998765432" in csv and "instagram" in csv


def test_feedback_ajudou_e_sugestao(client, admin):
    assert client.post("/public/feedback", json={"pagina": "som-para-reunir", "util": True}).status_code == 201
    assert client.post("/public/feedback", json={"pagina": "som-para-reunir", "util": False, "sugestao": "Faltou caixa com microfone"}).status_code == 201
    assert client.post("/public/feedback", json={"pagina": "inicio", "sugestao": "Presente para avó"}).status_code == 201
    assert client.post("/public/feedback", json={"pagina": "x"}).status_code == 422
    r = admin.get("/admin/feedback").json()
    som = next(p for p in r["paginas"] if p["pagina"] == "som-para-reunir")
    assert som == {"pagina": "som-para-reunir", "ajudou": 1, "nao_ajudou": 1}
    assert {s["texto"] for s in r["sugestoes"]} == {"Faltou caixa com microfone", "Presente para avó"}


def test_cancelar_e_voltar_aos_achados(client, admin):
    client.post("/public/inscricoes", json={"canal": "whatsapp", "contato": "21 98888-7777", "consent": True})
    client.post("/public/inscricoes", json={"canal": "email", "contato": "bia@exemplo.com", "consent": True})
    assert client.post("/public/inscricoes/cancelar", json={"contato": "(21) 98888-7777"}).json() == {"status": "OK"}
    assert client.post("/public/inscricoes/cancelar", json={"contato": "ninguem@exemplo.com"}).json() == {"status": "OK"}
    assert {x["contato"] for x in admin.get("/admin/inscricoes").json()["data"]} == {"bia@exemplo.com"}
    client.post("/public/inscricoes", json={"canal": "whatsapp", "contato": "21988887777", "consent": True})
    assert admin.get("/admin/inscricoes").json()["total"] == 2


def test_catalogo_inteiro_de_uma_vez(settings):
    from fastapi.testclient import TestClient
    from app.main import create_app
    settings.amazon_tag = "roboglobal-20"
    c = TestClient(create_app(settings, start_scheduler=False))
    r = c.get("/public/catalogo")
    d = r.json()
    assert r.headers["cache-control"].startswith("public")
    assert len(d["temas"]) == 7 and set(d["detalhes"]) >= {"presente-pet", "fone-sem-fio"}
    assert len(d["detalhes"]["presente-pet"]["escolhas"]) == 3
