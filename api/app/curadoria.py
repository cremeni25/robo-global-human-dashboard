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
    # ---------------------------------------------------------------- Natação
    "oculos-natacao": [
        item("Óculos de natação Hammerhead Vortex", "Hammerhead Vortex goggles", "Gafas Hammerhead Vortex",
             "óculos de natação Hammerhead Vortex",
             "Marca brasileira de natação, boa vedação para o dia a dia.", "Brazilian swim brand with a reliable seal for daily use.", "Marca brasileña de natación, buen sellado para el día a día."),
        item("Óculos Speedo Vanquisher 2.0", "Speedo Vanquisher 2.0 goggles", "Gafas Speedo Vanquisher 2.0",
             "óculos Speedo Vanquisher 2.0",
             "Clássico de treino e prova, com encaixe baixo e visão ampla.", "A training and racing classic with low profile and wide view.", "Clásico de entreno y competición, perfil bajo y visión amplia."),
        item("Óculos Arena Cobra Ultra Swipe", "Arena Cobra Ultra Swipe goggles", "Gafas Arena Cobra Ultra Swipe",
             "óculos Arena Cobra Ultra Swipe",
             "Óculos de competição com antiembaçante que se renova ao passar o dedo por fora.", "Racing goggles whose anti-fog renews with a swipe outside.", "Gafas de competición con antiempañante que se renueva al pasar el dedo."),
    ],
    "natacao-basico": [
        item("Touca de silicone Speedo", "Speedo silicone cap", "Gorro de silicona Speedo",
             "touca de silicone Speedo",
             "Protege o cabelo e dura muito mais que a de tecido.", "Protects hair and lasts far longer than fabric caps.", "Protege el cabello y dura mucho más que el de tela."),
        item("Toalha de microfibra Speedo", "Speedo microfiber towel", "Toalla de microfibra Speedo",
             "toalha de microfibra Speedo",
             "Seca rápido e ocupa pouco espaço na mochila.", "Dries fast and packs small.", "Seca rápido y ocupa poco espacio."),
        item("Mochila de natação Arena Fastpack", "Arena Fastpack swim backpack", "Mochila de natación Arena Fastpack",
             "mochila de natação Arena Fastpack",
             "Compartimento separado para o material molhado.", "Separate compartment for wet gear.", "Compartimento separado para el material mojado."),
    ],
    "tecnica-natacao": [
        item("Prancha de natação Hammerhead", "Hammerhead kickboard", "Tabla de natación Hammerhead",
             "prancha de natação Hammerhead",
             "Base para treinar a pernada, de marca brasileira.", "The basic tool for kick sets, from a Brazilian brand.", "Lo básico para entrenar la patada, marca brasileña."),
        item("Pull buoy Speedo", "Speedo pull buoy", "Pull buoy Speedo",
             "pull buoy Speedo",
             "Isola as pernas para focar na braçada e na rotação.", "Isolates the legs to focus on the pull and rotation.", "Aísla las piernas para enfocarte en la brazada."),
        item("Nadadeira curta Arena Powerfin Pro", "Arena Powerfin Pro short fins", "Aletas cortas Arena Powerfin Pro",
             "nadadeira Arena Powerfin Pro",
             "Fortalece a pernada sem mudar o ritmo do nado.", "Builds kick strength without changing your tempo.", "Fortalece la patada sin cambiar el ritmo."),
    ],
    "roupa-competicao": [
        item("Linha de treino Speedo Endurance (sunga e maiô)", "Speedo Endurance training swimwear", "Línea de entreno Speedo Endurance",
             "Speedo Endurance sunga maiô",
             "Tecido resistente ao cloro, feito para durar muitos treinos.", "Chlorine-resistant fabric built for many sessions.", "Tejido resistente al cloro, hecho para durar."),
        item("Traje Arena Powerskin ST Next", "Arena Powerskin ST Next race suit", "Traje Arena Powerskin ST Next",
             "Arena Powerskin ST Next",
             "Primeiro traje tecnológico para competir, com bom custo.", "A first tech suit for racing at a fair price.", "Primer traje técnico para competir, a buen precio."),
        item("Traje Speedo Fastskin LZR Pure Intent", "Speedo Fastskin LZR Pure Intent", "Traje Speedo Fastskin LZR Pure Intent",
             "Speedo Fastskin LZR Pure Intent",
             "Traje de alta performance, usado em competições de elite.", "A high-performance suit used at elite meets.", "Traje de alto rendimiento usado en competiciones de élite."),
    ],
    # ---------------------------------------------------------------- Triathlon
    "aguas-abertas": [
        item("Boia de segurança Zone3", "Zone3 safety buoy", "Boya de seguridad Zone3",
             "boia de segurança natação Zone3",
             "Deixa você visível e dá apoio para descansar.", "Keeps you visible and gives you something to rest on.", "Te hace visible y te da apoyo para descansar."),
        item("Óculos Aqua Sphere Vista", "Aqua Sphere Vista goggles", "Gafas Aqua Sphere Vista",
             "óculos Aqua Sphere Vista",
             "Visão ampla para se orientar pelas boias no mar.", "Wide view to sight buoys at sea.", "Visión amplia para orientarte por las boyas."),
        item("Roupa de neoprene Orca", "Orca wetsuit", "Neopreno Orca",
             "roupa de neoprene triathlon Orca",
             "Aquece, ajuda a flutuar e é referência no triathlon.", "Warms you, adds buoyancy and is a triathlon reference.", "Abriga, ayuda a flotar y es referencia en triatlón."),
    ],
    "primeiro-triathlon": [
        item("Cadarço elástico Lock Laces", "Lock Laces elastic laces", "Cordones elásticos Lock Laces",
             "cadarço elástico Lock Laces",
             "Calçar o tênis em segundos na transição.", "Shoes on in seconds in transition.", "Zapatillas puestas en segundos en la transición."),
        item("Capacete de ciclismo Giro", "Giro cycling helmet", "Casco de ciclismo Giro",
             "capacete de ciclismo Giro",
             "Item obrigatório, de marca referência em segurança.", "Mandatory gear from a safety-leading brand.", "Obligatorio, de una marca referente en seguridad."),
        item("Macaquinho de triathlon Mormaii", "Mormaii tri suit", "Traje de triatlón Mormaii",
             "macaquinho de triathlon Mormaii",
             "Uma peça só para nadar, pedalar e correr.", "One piece to swim, bike and run.", "Una sola prenda para nadar, pedalear y correr."),
    ],
    "corrida-triathlon": [
        item("Tênis de corrida Olympikus Corre", "Olympikus Corre running shoes", "Zapatillas Olympikus Corre",
             "tênis Olympikus Corre",
             "Tênis nacional leve, ótimo custo para treinar.", "Light Brazilian shoe with great value for training.", "Zapatilla brasileña ligera, gran valor para entrenar."),
        item("Tênis Mizuno Wave Rider", "Mizuno Wave Rider shoes", "Zapatillas Mizuno Wave Rider",
             "tênis Mizuno Wave Rider",
             "Equilíbrio entre amortecimento e resposta para o dia a dia.", "Balanced cushioning and response for everyday runs.", "Equilibrio entre amortiguación y respuesta."),
        item("Tênis Asics Gel-Nimbus", "Asics Gel-Nimbus shoes", "Zapatillas Asics Gel-Nimbus",
             "tênis Asics Gel Nimbus",
             "Amortecimento máximo para poupar as pernas depois do ciclismo.", "Maximum cushioning to spare your legs after the bike.", "Máxima amortiguación para cuidar las piernas tras la bici."),
    ],
    # ---------------------------------------------------------------- Treino e recuperação
    "medir-treinos": [
        item("Pulseira Xiaomi Smart Band 9", "Xiaomi Smart Band 9", "Pulsera Xiaomi Smart Band 9",
             "Xiaomi Smart Band 9",
             "Conta voltas na piscina e cabe em qualquer orçamento.", "Counts pool laps and fits any budget.", "Cuenta largos en la piscina y cabe en cualquier presupuesto."),
        item("Relógio Garmin Swim 2", "Garmin Swim 2 watch", "Reloj Garmin Swim 2",
             "Garmin Swim 2",
             "Feito para natação: piscina e águas abertas, com dados detalhados.", "Built for swimming: pool and open water, detailed data.", "Hecho para nadar: piscina y aguas abiertas, datos detallados."),
        item("Relógio Garmin Forerunner 55", "Garmin Forerunner 55 watch", "Reloj Garmin Forerunner 55",
             "Garmin Forerunner 55",
             "GPS e modos de corrida, ciclismo e piscina para o triathlon.", "GPS with run, bike and pool modes for triathlon.", "GPS con modos de carrera, ciclismo y piscina para triatlón."),
    ],
    "ombro-nadador": [
        item("Kit de faixas elásticas Acte Sports", "Acte Sports resistance band set", "Kit de bandas elásticas Acte Sports",
             "kit faixas elásticas Acte Sports",
             "Fortalece os músculos que estabilizam o ombro, em poucos minutos.", "Strengthens shoulder stabilizers in minutes.", "Fortalece los estabilizadores del hombro en minutos."),
        item("Rolo de liberação miofascial Acte Sports", "Acte Sports foam roller", "Rodillo miofascial Acte Sports",
             "rolo de liberação miofascial Acte Sports",
             "Solta a musculatura depois dos treinos mais pesados.", "Loosens muscles after hard sessions.", "Suelta la musculatura tras los entrenos duros."),
        item("Pistola de massagem Relaxmedic", "Relaxmedic massage gun", "Pistola de masaje Relaxmedic",
             "pistola de massagem Relaxmedic",
             "Massagem profunda para recuperar ombros e costas.", "Deep massage to recover shoulders and back.", "Masaje profundo para recuperar hombros y espalda."),
    ],
    # ---------------------------------------------------------------- Nutrição
    "energia-prova": [
        item("Gel de carboidrato Max Titanium", "Max Titanium carb gel", "Gel de carbohidratos Max Titanium",
             "gel de carboidrato Max Titanium",
             "Energia rápida e fácil de levar no bolso.", "Quick energy that fits in a pocket.", "Energía rápida y fácil de llevar."),
        item("Repositor hidroeletrolítico Integralmedica", "Integralmedica electrolyte drink", "Reponedor hidroelectrolítico Integralmedica",
             "repositor hidroeletrolítico Integralmedica",
             "Repõe sais minerais nos treinos longos e no calor.", "Replaces electrolytes on long sessions and in heat.", "Repone sales en entrenos largos y con calor."),
        item("Garrafa térmica Stanley Quencher", "Stanley Quencher tumbler", "Vaso térmico Stanley Quencher",
             "copo térmico Stanley Quencher",
             "Água gelada o treino inteiro, de uma marca que virou febre.", "Cold water all session long, from a cult brand.", "Agua fría todo el entreno, de una marca de moda."),
    ],
    "proteina-creatina": [
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
    # ---------------------------------------------------------------- Mente do atleta
    "ansiedade-prova": [
        item("Livro Mindset (Carol Dweck)", "Mindset by Carol Dweck", "Libro Mindset (Carol Dweck)",
             "livro Mindset Carol Dweck",
             "Ensina a encarar a prova como desafio, não como ameaça.", "Teaches you to see a race as a challenge, not a threat.", "Enseña a ver la prueba como reto, no como amenaza."),
        item("Livro O Jogo Interior do Tênis (Timothy Gallwey)", "The Inner Game of Tennis", "Libro El juego interior del tenis",
             "livro O Jogo Interior do Tênis Gallwey",
             "Clássico sobre calar a mente e confiar no corpo, útil em qualquer esporte.", "A classic on quieting the mind, useful in any sport.", "Un clásico sobre calmar la mente, útil en cualquier deporte."),
        item("Livro Psicologia do Esporte e do Exercício (Weinberg e Gould)", "Foundations of Sport and Exercise Psychology", "Libro Fundamentos de psicología del deporte",
             "livro Psicologia do Esporte e do Exercício Weinberg",
             "A referência acadêmica, para quem quer se aprofundar.", "The academic reference for those who want depth.", "La referencia académica para profundizar."),
    ],
    "disciplina-treino": [
        item("Livro Hábitos Atômicos (James Clear)", "Atomic Habits by James Clear", "Libro Hábitos atómicos (James Clear)",
             "livro Hábitos Atômicos",
             "Como criar a rotina de treino que se mantém sozinha.", "How to build a training routine that sticks.", "Cómo crear una rutina de entrenamiento que se mantenga."),
        item("Livro Nascido para Correr (Christopher McDougall)", "Born to Run by Christopher McDougall", "Libro Nacidos para correr",
             "livro Nascido para Correr",
             "História inspiradora sobre o prazer de treinar.", "An inspiring story about the joy of training.", "Una historia inspiradora sobre el placer de entrenar."),
        item("Livro Do que eu falo quando eu falo de corrida (Haruki Murakami)", "What I Talk About When I Talk About Running", "Libro De qué hablo cuando hablo de correr",
             "livro Do que eu falo quando eu falo de corrida",
             "Reflexão sobre disciplina e constância de um escritor que virou triatleta.", "A writer-turned-triathlete on discipline and consistency.", "Un escritor triatleta reflexiona sobre disciplina y constancia."),
    ],
}

# Páginas que reaproveitam produtos de outras (nenhuma hoje).
REFERENCIAS: dict[str, list[str]] = {}


def link_amazon(busca: str, tag: str) -> str:
    return f"https://www.amazon.com.br/s?k={quote_plus(busca)}&tag={quote_plus(tag)}"


PLATAFORMA_ML = "mercadolivre"
LOJA_ML = "Mercado Livre"


def _aplicar_mercadolivre(db: Session) -> int:
    """Mesmo produto, segunda loja: oferta do Mercado Livre para cada item da curadoria que tem link
    de afiliado gerado (LINKS_ML, por termo de busca)."""
    from .curadoria_ml import LINKS_ML
    existentes = {o.external_product_id: o for o in db.scalars(select(Oferta).where(Oferta.platform == PLATAFORMA_ML))}
    usados: set[str] = set()
    criadas = 0
    for slug, lista in CURADORIA.items():
        for n, it in enumerate(lista):
            link = LINKS_ML.get(it["busca"])
            if not link:
                continue
            ext = f"{slug}:{n}"
            usados.add(ext)
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
            o.category = "curadoria > " + slug
            o.active = o.published = True
            flag_modified(o, "translations")
    for ext, o in existentes.items():
        if ext not in usados:
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
