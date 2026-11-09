import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

ADMIN = "token-admin-de-teste-123"
HOTTOK = "hottok-de-teste"
WEBHOOK = "webhook-de-teste"


@pytest.fixture()
def settings():
    s = Settings()
    # TEST_DATABASE_URL permite rodar a mesma suíte contra PostgreSQL (Supabase)
    s.database_url = os.getenv("TEST_DATABASE_URL", "sqlite://")
    if s.database_url != "sqlite://":
        from app.db import make_engine
        from app.models import Base
        engine = make_engine(s.database_url)
        Base.metadata.drop_all(engine)
        engine.dispose()
    s.admin_tokens = {ADMIN: "anderson"}
    s.hotmart_hottok = HOTTOK
    s.webhook_token = WEBHOOK
    s.min_cliques_decisao = 10
    s.epc_alvo = 0.5
    return s


@pytest.fixture()
def client(settings):
    return TestClient(create_app(settings, start_scheduler=False), follow_redirects=False)


@pytest.fixture()
def admin(client):
    client.headers.update({"Authorization": f"Bearer {ADMIN}"})
    return client


@pytest.fixture()
def catalogo(admin):
    """Nicho → subnicho → dor publicados e uma oferta Hotmart publicada e vinculada."""
    n = admin.post("/admin/catalogo/nichos", json={"title": "Saúde", "slug": "saude"}).json()
    s = admin.post("/admin/catalogo/subnichos", json={"title": "Peso", "slug": "peso", "parent_id": n["id"]}).json()
    d = admin.post("/admin/catalogo/dores", json={"title": "Emagrecer", "slug": "emagrecer", "parent_id": s["id"]}).json()
    for nivel, item in (("nichos", n), ("subnichos", s), ("dores", d)):
        assert admin.patch(f"/admin/catalogo/{nivel}/{item['id']}", json={"published": True}).status_code == 200
    o = admin.post("/admin/ofertas", json={
        "title": "Curso X", "destination_url": "https://go.hotmart.com/ABC?ap=1",
        "platform": "hotmart", "subid_param": "sck", "external_product_id": "999",
    }).json()
    assert admin.patch(f"/admin/ofertas/{o['id']}", json={"published": True}).status_code == 200
    assert admin.post("/admin/vinculos", json={"dor_id": d["id"], "oferta_id": o["id"]}).status_code == 201
    return {"nicho": n, "sub": s, "dor": d, "oferta": o}
