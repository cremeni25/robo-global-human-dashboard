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
