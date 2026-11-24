"""Curadoria: os produtos de cada página de problema, escolhidos a dedo.

Somente marcas conhecidas no Brasil, vendidas na Amazon.com.br. Cada item aponta
para a busca do modelo na Amazon com o ID de Associado (AMAZON_TAG): o visitante
sempre vê preço, estoque e vendedor atualizados pela própria Amazon, e nenhum
link quebra quando um anúncio sai do ar. Preço e foto não são copiados (regra do
Programa de Associados até a liberação da API oficial).

Aplicada automaticamente na inicialização (idempotente). Para mudar um produto,
altere a lista abaixo; para trocar à mão sem publicar código, use o painel.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .config import Settings
from .models import Configuracao, Oferta, new_id

log = logging.getLogger("robo.curadoria")
PLATAFORMA = "amazon"
LOJA = "Amazon"


def item(pt: str, en: str, es: str, busca: str, mpt: str, men: str, mes: str) -> dict[str, Any]:
    return {"titulo": {"pt": pt, "en": en, "es": es}, "busca": busca, "motivo": {"pt": mpt, "en": men, "es": mes}}


CURADORIA: dict[str, list[dict[str, Any]]] = {
    # ---------------------------------------------------------------- Esporte
    "treinar-em-casa": [
        item("Kit de faixas elásticas Acte Sports", "Acte Sports resistance band set", "Kit de bandas elásticas Acte Sports",
             "kit faixas elásticas Acte Sports",
             "Ocupa quase nenhum espaço e serve para treinar o corpo todo.", "Takes almost no space and trains the whole body.", "Casi no ocupa espacio y entrena todo el cuerpo."),
        item("Tapete de yoga Acte Sports", "Acte Sports yoga mat", "Esterilla de yoga Acte Sports",
             "tapete de yoga Acte Sports",
             "Base firme e antiderrapante para alongar e treinar no chão.", "A firm, non-slip base for floor workouts.", "Base firme y antideslizante para entrenar en el suelo."),
        item("Par de halteres emborrachados Kikos", "Kikos rubber dumbbell pair", "Par de mancuernas Kikos",
             "par de halteres emborrachados Kikos",
             "Para evoluir a força com carga, de uma marca tradicional de fitness.", "To build strength with weights, from a trusted fitness brand.", "Para ganar fuerza con peso, de una marca tradicional."),
    ],
    "roupa-de-treino": [
        item("Camiseta de treino dry Olympikus", "Olympikus dry training T-shirt", "Camiseta deportiva dry Olympikus",
             "camiseta dry fit Olympikus masculina feminina",
             "Tecido leve que seca rápido, ótimo para começar.", "Light quick-dry fabric, great to start.", "Tejido ligero de secado rápido, ideal para empezar."),
        item("Camiseta de treino Adidas", "Adidas training T-shirt", "Camiseta de entrenamiento Adidas",
             "camiseta treino Adidas",
             "Conforto e durabilidade de uma marca que todo mundo conhece.", "Comfort and durability from a brand everyone knows.", "Comodidad y durabilidad de una marca reconocida."),
        item("Tênis de corrida Olympikus Corre", "Olympikus Corre running shoes", "Zapatillas de running Olympikus Corre",
             "tênis Olympikus Corre",
             "Para quem corre ou caminha: o tênis é o item que mais faz diferença.", "For runners and walkers: shoes make the biggest difference.", "Para correr o caminar: las zapatillas marcan la diferencia."),
    ],
    "suplementos": [
        item("Creatina monohidratada Max Titanium", "Max Titanium creatine monohydrate", "Creatina monohidratada Max Titanium",
             "creatina monohidratada Max Titanium 300g",
             "O suplemento mais estudado para força, de marca nacional consolidada.", "The most researched strength supplement, from an established brand.", "El suplemento más estudiado para la fuerza, de marca consolidada."),
        item("Whey Protein Top Whey 3W Max Titanium", "Max Titanium Top Whey 3W protein", "Proteína Top Whey 3W Max Titanium",
             "Top Whey 3W Max Titanium 900g",
             "Ajuda a completar a proteína do dia com bom custo-benefício.", "Helps meet daily protein at good value.", "Ayuda a completar la proteína diaria con buena relación calidad-precio."),
        item("Whey Protein Isolado Dux Nutrition", "Dux Nutrition whey protein isolate", "Proteína aislada Dux Nutrition",
             "whey protein isolado Dux Nutrition",
             "Mais pureza e menos lactose, para quem quer o mais completo.", "Higher purity and less lactose for the most complete option.", "Más pureza y menos lactosa, para la opción más completa."),
    ],
    # ---------------------------------------------------------------- Saúde corporal
    "dores-nas-costas": [
        item("Almofada lombar para cadeira Duoflex", "Duoflex lumbar support cushion", "Cojín lumbar para silla Duoflex",
             "almofada lombar cadeira Duoflex",
             "Apoia a curva das costas para quem passa horas sentado.", "Supports your lower back during long hours seated.", "Apoya la zona lumbar en largas horas sentado."),
        item("Massageador elétrico Relaxmedic", "Relaxmedic electric massager", "Masajeador eléctrico Relaxmedic",
             "massageador elétrico Relaxmedic",
             "Alívio da tensão no pescoço e nos ombros, de marca brasileira conhecida.", "Relieves neck and shoulder tension, from a known Brazilian brand.", "Alivia la tensión de cuello y hombros, de una marca brasileña conocida."),
        item("Pistola de massagem Relaxmedic", "Relaxmedic massage gun", "Pistola de masaje Relaxmedic",
             "pistola de massagem Relaxmedic",
             "Massagem profunda para músculos cansados depois do dia ou do treino.", "Deep massage for tired muscles after work or training.", "Masaje profundo para músculos cansados."),
    ],
    "acompanhar-peso": [
        item("Balança digital Multilaser", "Multilaser digital scale", "Báscula digital Multilaser",
             "balança digital banheiro Multilaser",
             "Simples e precisa para acompanhar o peso no dia a dia.", "Simple and accurate for everyday weighing.", "Sencilla y precisa para el día a día."),
        item("Balança de bioimpedância Xiaomi Mi Body Composition Scale 2", "Xiaomi Mi Body Composition Scale 2", "Báscula de bioimpedancia Xiaomi Mi Body Composition Scale 2",
             "Xiaomi Mi Body Composition Scale 2",
             "Mostra gordura, músculo e guarda o histórico no aplicativo.", "Shows fat and muscle, and saves history in the app.", "Muestra grasa y músculo y guarda el historial en la app."),
        item("Balança de bioimpedância Omron", "Omron body composition scale", "Báscula de bioimpedancia Omron",
             "balança bioimpedância Omron",
             "Marca de referência em saúde, para medições mais completas.", "A health reference brand for fuller measurements.", "Marca de referencia en salud para mediciones más completas."),
    ],
    # ---------------------------------------------------------------- Bem-estar
    "dormir-melhor": [
        item("Protetor auricular de espuma 3M", "3M foam earplugs", "Tapones de espuma 3M",
             "protetor auricular espuma 3M",
             "Bloqueia o barulho por pouco dinheiro.", "Blocks noise for very little money.", "Bloquea el ruido por muy poco dinero."),
        item("Máscara de dormir 3D", "3D sleep mask", "Antifaz para dormir 3D",
             "máscara de dormir 3D blackout",
             "Escuridão total sem pressionar os olhos.", "Total darkness without pressing on the eyes.", "Oscuridad total sin presionar los ojos."),
        item("Travesseiro viscoelástico Duoflex", "Duoflex memory foam pillow", "Almohada viscoelástica Duoflex",
             "travesseiro viscoelástico Duoflex",
             "Apoio correto para o pescoço, de marca brasileira de referência.", "Proper neck support from a leading Brazilian brand.", "Buen apoyo para el cuello, de una marca brasileña de referencia."),
    ],
    "relaxar-em-casa": [
        item("Óleo essencial de lavanda Via Aroma", "Via Aroma lavender essential oil", "Aceite esencial de lavanda Via Aroma",
             "óleo essencial lavanda Via Aroma",
             "O aroma mais usado para relaxar, de marca brasileira.", "The classic relaxing scent, from a Brazilian brand.", "El aroma clásico para relajarse, de una marca brasileña."),
        item("Difusor de aromas elétrico Via Aroma", "Via Aroma electric diffuser", "Difusor eléctrico Via Aroma",
             "difusor elétrico ultrassônico Via Aroma",
             "Espalha o aroma pelo ambiente com luz suave.", "Spreads scent through the room with soft light.", "Difunde el aroma por la habitación con luz suave."),
        item("Umidificador de ar Philco", "Philco air humidifier", "Humidificador Philco",
             "umidificador de ar Philco",
             "Ar mais agradável, principalmente nos dias secos.", "More comfortable air, especially on dry days.", "Aire más agradable, sobre todo en días secos."),
    ],
    # ---------------------------------------------------------------- Casa
    "cozinha-organizada": [
        item("Organizador de gaveta Ordene", "Ordene drawer organizer", "Organizador de cajón Ordene",
             "organizador de gaveta Ordene",
             "Talheres e utensílios no lugar, de marca especialista em organização.", "Cutlery in place, from an organization specialist.", "Cubiertos en su lugar, de una marca especialista."),
        item("Kit de potes herméticos Electrolux", "Electrolux airtight container set", "Kit de recipientes herméticos Electrolux",
             "kit potes herméticos Electrolux",
             "Mantimentos protegidos e armário organizado.", "Protected food and a tidy cupboard.", "Alimentos protegidos y despensa ordenada."),
        item("Porta-temperos giratório Ordene", "Ordene rotating spice rack", "Especiero giratorio Ordene",
             "porta temperos giratório Ordene",
             "Todos os temperos à mão em pouco espaço.", "All spices at hand in little space.", "Todas las especias a mano en poco espacio."),
    ],
    "limpeza-facil": [
        item("Mop giratório Flash Limp", "Flash Limp spin mop", "Mopa giratoria Flash Limp",
             "mop giratório Flash Limp",
             "Limpa o chão rápido, sem molhar as mãos.", "Cleans floors fast without wet hands.", "Limpia el suelo rápido sin mojarte las manos."),
        item("Aspirador de pó vertical Electrolux", "Electrolux stick vacuum", "Aspiradora vertical Electrolux",
             "aspirador de pó vertical Electrolux",
             "Leve e prático para o dia a dia, de marca tradicional.", "Light and handy for daily use, from a trusted brand.", "Ligera y práctica a diario, de marca tradicional."),
        item("Robô aspirador WAP", "WAP robot vacuum", "Robot aspirador WAP",
             "robô aspirador WAP",
             "Aspira sozinho enquanto você cuida de outras coisas.", "Vacuums on its own while you do other things.", "Aspira solo mientras haces otras cosas."),
    ],
    # ---------------------------------------------------------------- Pet
    "pet-sozinho-em-casa": [
        item("Fonte bebedouro para gatos Furacão Pet", "Furacão Pet cat water fountain", "Fuente bebedero para gatos Furacão Pet",
             "fonte bebedouro gato Furacão Pet",
             "Água fresca e corrente o dia todo, de marca pet brasileira.", "Fresh running water all day, from a Brazilian pet brand.", "Agua fresca todo el día, de marca brasileña de mascotas."),
        item("Comedouro automático Petkit", "Petkit automatic feeder", "Comedero automático Petkit",
             "comedouro automático Petkit",
             "Refeições nos horários certos, mesmo com você fora.", "Meals on schedule even when you're away.", "Comidas a su hora aunque no estés."),
        item("Comedouro automático Xiaomi", "Xiaomi smart pet feeder", "Comedero inteligente Xiaomi",
             "comedouro automático Xiaomi pet feeder",
             "Controle pelo celular e acompanhamento das refeições.", "Phone control and meal tracking.", "Control desde el móvil y seguimiento de comidas."),
    ],
    "passeio-seguro": [
        item("Guia retrátil Flexi", "Flexi retractable leash", "Correa retráctil Flexi",
             "guia retrátil Flexi",
             "Liberdade para o cachorro com controle para você.", "Freedom for your dog, control for you.", "Libertad para tu perro y control para ti."),
        item("Peitoral para cachorro Furacão Pet", "Furacão Pet dog harness", "Arnés para perro Furacão Pet",
             "peitoral cachorro Furacão Pet",
             "Distribui melhor a força e protege o pescoço.", "Spreads pressure and protects the neck.", "Reparte la fuerza y protege el cuello."),
        item("Peitoral Zee.Dog", "Zee.Dog harness", "Arnés Zee.Dog",
             "peitoral Zee.Dog",
             "Design e acabamento de uma das marcas pet mais queridas do Brasil.", "Design and quality from a beloved Brazilian pet brand.", "Diseño y calidad de una marca de mascotas muy querida en Brasil."),
    ],
    # ---------------------------------------------------------------- Eletrônicos
    "fone-sem-fio": [
        item("Fone sem fio JBL Wave Buds", "JBL Wave Buds wireless earbuds", "Auriculares inalámbricos JBL Wave Buds",
             "JBL Wave Buds",
             "Som JBL com preço de entrada e boa bateria.", "JBL sound at an entry price with good battery.", "Sonido JBL a precio de entrada y buena batería."),
        item("Fone sem fio Samsung Galaxy Buds FE", "Samsung Galaxy Buds FE", "Auriculares Samsung Galaxy Buds FE",
             "Samsung Galaxy Buds FE",
             "Cancelamento de ruído e conforto para o dia inteiro.", "Noise cancelling and all-day comfort.", "Cancelación de ruido y comodidad todo el día."),
        item("Fone sem fio JBL Tune Beam", "JBL Tune Beam earbuds", "Auriculares JBL Tune Beam",
             "JBL Tune Beam",
             "Mais recursos: cancelamento de ruído e resistência a água e poeira.", "More features: noise cancelling and water/dust resistance.", "Más funciones: cancelación de ruido y resistencia al agua y polvo."),
    ],
    "bateria-do-celular": [
        item("Carregador portátil Geonav 10.000 mAh", "Geonav 10,000 mAh power bank", "Batería portátil Geonav 10.000 mAh",
             "carregador portátil Geonav 10000mAh",
             "Duas cargas completas no bolso, de marca nacional.", "Two full charges in your pocket, from a Brazilian brand.", "Dos cargas completas en el bolsillo, de marca brasileña."),
        item("Carregador portátil Xiaomi 10.000 mAh", "Xiaomi 10,000 mAh power bank", "Batería portátil Xiaomi 10.000 mAh",
             "power bank Xiaomi 10000mAh",
             "Fino, confiável e com carregamento rápido.", "Slim, reliable and fast-charging.", "Delgada, fiable y con carga rápida."),
        item("Carregador portátil Anker 20.000 mAh", "Anker 20,000 mAh power bank", "Batería portátil Anker 20.000 mAh",
             "Anker power bank 20000mAh",
             "Bateria para vários dias ou para carregar mais de um aparelho.", "Power for days or several devices.", "Energía para varios días o varios dispositivos."),
    ],
    "som-para-reunir": [
        item("Caixa de som JBL Go 4", "JBL Go 4 speaker", "Altavoz JBL Go 4",
             "JBL Go 4",
             "Pequena, à prova d'água e com o som que todo mundo conhece.", "Small, waterproof and with the sound everyone knows.", "Pequeño, resistente al agua y con sonido JBL."),
        item("Caixa de som JBL Flip 6", "JBL Flip 6 speaker", "Altavoz JBL Flip 6",
             "JBL Flip 6",
             "Som potente para churrasco e viagem, à prova d'água.", "Powerful waterproof sound for barbecues and trips.", "Sonido potente y resistente al agua para asados y viajes."),
        item("Caixa de som JBL Charge 5", "JBL Charge 5 speaker", "Altavoz JBL Charge 5",
             "JBL Charge 5",
             "Mais potência e bateria longa, ainda carrega o celular.", "More power, long battery, and charges your phone.", "Más potencia, batería larga y carga tu móvil."),
    ],
}


# Páginas que reúnem produtos já escolhidos acima (mesma oferta, mesmas lojas e motivos).
REFERENCIAS: dict[str, list[str]] = {
    "presente-musica": ["som-para-reunir:0", "fone-sem-fio:0", "som-para-reunir:1"],
    "presente-treino": ["treinar-em-casa:1", "dores-nas-costas:2", "roupa-de-treino:2"],
    "presente-pet": ["passeio-seguro:2", "pet-sozinho-em-casa:0", "pet-sozinho-em-casa:1"],
    "presente-casa": ["relaxar-em-casa:1", "dormir-melhor:2", "limpeza-facil:2"],
    "presente-tecnologia": ["bateria-do-celular:1", "fone-sem-fio:1", "acompanhar-peso:1"],
}


def link_amazon(busca: str, tag: str) -> str:
    return f"https://www.amazon.com.br/s?k={quote_plus(busca)}&tag={quote_plus(tag)}"


PLATAFORMA_ML = "mercadolivre"
LOJA_ML = "Mercado Livre"


def _aplicar_mercadolivre(db: Session) -> int:
    """Mesmo produto, segunda loja: oferta do Mercado Livre com a mesma chave da curadoria."""
    from .curadoria_ml import LINKS_ML
    itens = {f"{slug}:{n}": it for slug, lista in CURADORIA.items() for n, it in enumerate(lista)}
    existentes = {o.external_product_id: o for o in db.scalars(select(Oferta).where(Oferta.platform == PLATAFORMA_ML))}
    criadas = 0
    for ext, link in LINKS_ML.items():
        it = itens.get(ext)
        if it is None:
            continue
        o = existentes.get(ext)
        if o is None:
            o = Oferta(id=new_id(), platform=PLATAFORMA_ML, external_product_id=ext, source="curadoria")
            db.add(o)
            criadas += 1
        o.title = it["titulo"]["pt"][:200]
        o.description = it["motivo"]["pt"]
        o.translations = {l: {"title": it["titulo"][l], "description": it["motivo"][l]} for l in ("pt", "en", "es")}
        o.kind, o.provider, o.market, o.language, o.currency = "afiliado", LOJA_ML, "BR", "pt", "BRL"
        o.destination_url = link
        o.subid_param = None
        o.image_url, o.price = "", None
        o.category = "curadoria > " + ext.split(":")[0]
        o.active = o.published = True
        flag_modified(o, "translations")
    for ext, o in existentes.items():
        if ext not in LINKS_ML:
            o.active = False
    return criadas


def aplicar(db: Session, s: Settings) -> dict[str, int]:
    """Cria/atualiza as ofertas da curadoria e fixa cada trio na sua página."""
    if not s.amazon_tag:
        return {"status": "sem_tag"}
    existentes = {o.external_product_id: o for o in db.scalars(select(Oferta).where(Oferta.platform == PLATAFORMA))}
    usados: set[str] = set()
    fixas: dict[str, list[str]] = {}
    criadas = 0
    for slug, itens in CURADORIA.items():
        ids = []
        for n, it in enumerate(itens):
            ext = f"{slug}:{n}"
            usados.add(ext)
            o = existentes.get(ext)
            if o is None:
                o = Oferta(id=new_id(), platform=PLATAFORMA, external_product_id=ext, source="curadoria")
                db.add(o)
                criadas += 1
            o.title = it["titulo"]["pt"][:200]
            o.description = it["motivo"]["pt"]
            o.translations = {l: {"title": it["titulo"][l], "description": it["motivo"][l]} for l in ("pt", "en", "es")}
            o.kind, o.provider, o.market, o.language, o.currency = "afiliado", LOJA, "BR", "pt", "BRL"
            o.destination_url = link_amazon(it["busca"], s.amazon_tag)
            o.subid_param = None
            o.image_url, o.price = "", None
            o.category = f"curadoria > {slug}"
            o.active = o.published = True
            flag_modified(o, "translations")
            ids.append(o.id)
        fixas[slug] = ids
    por_chave = {o.external_product_id: o.id for o in db.scalars(select(Oferta).where(Oferta.platform == PLATAFORMA))}
    por_chave.update({f"{slug}:{n}": i for slug, ids in fixas.items() for n, i in enumerate(ids)})
    for slug, chaves in REFERENCIAS.items():
        fixas[slug] = [por_chave[c] for c in chaves if c in por_chave]
    for ext, o in existentes.items():  # saiu da lista: sai do ar
        if ext not in usados:
            o.active = False
    criadas += _aplicar_mercadolivre(db)
    row = db.get(Configuracao, "problemas_escolhas")
    valor = dict(row.value) if row and isinstance(row.value, dict) else {}
    valor.update(fixas)
    if row is None:
        db.add(Configuracao(key="problemas_escolhas", value=valor))
    else:
        row.value = valor
        flag_modified(row, "value")
    db.commit()
    from .problemas import limpar_cache
    limpar_cache()
    return {"ofertas_criadas": criadas, "paginas": len(fixas)}
