"""Páginas de problema: o coração do Robô Global.

Problema do dia a dia → página que explica o que considerar → 3 escolhas
(para começar, melhor custo-benefício, mais completa) → loja parceira.

Os textos são editoriais (escritos uma vez). Os produtos de cada página vêm de:
1. escolhas fixadas no painel (qualquer oferta no ar, inclusive links diretos
   cadastrados à mão, como Amazon ou Mercado Livre); ou
2. seleção automática por palavras-chave, só em lojas confiáveis.
Página sem pelo menos 2 produtos não aparece ao público.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Optional

from sqlalchemy import not_, or_, select
from sqlalchemy.orm import Session

from .config import Settings
from .core import select_ofertas_visiveis
from .models import Configuracao, Oferta

CHAVE_ESCOLHAS = "problemas_escolhas"
EXCLUIR_SEMPRE = ["replacement", "spare part", "peça de reposição", "filter for", "filtro para", "cable for",
                  "cabo para", "case for", "capa para", "cover for", "sticker", "adesivo", "plugue ue",
                  "plugue uk", "eu plug", "uk plug", "for parts"]

NIVEIS = [
    {"chave": "comecar", "pt": "Para começar", "en": "To get started", "es": "Para empezar",
     "motivo": {"pt": "A opção mais acessível para resolver o básico.",
                "en": "The most affordable way to cover the basics.",
                "es": "La opción más accesible para resolver lo básico."}},
    {"chave": "equilibrio", "pt": "Melhor custo-benefício", "en": "Best value", "es": "Mejor relación calidad-precio",
     "motivo": {"pt": "Equilíbrio entre preço e recursos para o uso do dia a dia.",
                "en": "A balance of price and features for everyday use.",
                "es": "Equilibrio entre precio y prestaciones para el día a día."}},
    {"chave": "completa", "pt": "Mais completa", "en": "Most complete", "es": "Más completa",
     "motivo": {"pt": "Para quem quer mais recursos e durabilidade.",
                "en": "For those who want more features and durability.",
                "es": "Para quien busca más funciones y durabilidad."}},
]


def _t(pt: str, en: str, es: str) -> dict[str, str]:
    return {"pt": pt, "en": en, "es": es}


_CONSIDERAR_PRESENTE = [
    _t("Pense no dia a dia de quem vai receber: o melhor presente resolve algo real.",
       "Think about the person's daily life: the best gift solves something real.",
       "Piensa en el día a día de quien lo recibe: el mejor regalo resuelve algo real."),
    _t("Marcas conhecidas facilitam troca e garantia, se precisar.",
       "Well-known brands make returns and warranty easier.",
       "Las marcas conocidas facilitan cambios y garantía."),
    _t("Compre com antecedência: perto do Natal, as entregas demoram mais.",
       "Buy early: deliveries take longer close to Christmas.",
       "Compra con tiempo: cerca de Navidad las entregas tardan más."),
]


def _presente(slug: str, pt: str, en: str, es: str, rpt: str, ren: str, res: str) -> dict[str, Any]:
    return {"slug": slug, "titulo": _t(pt, en, es), "resumo": _t(rpt, ren, res), "considerar": _CONSIDERAR_PRESENTE,
            "busca": [], "preco": [0, 0]}


TEMAS: list[dict[str, Any]] = [
    # Tema da época: produtos já escolhidos nas outras áreas, reunidos por quem vai ganhar.
    {"slug": "presentes", "icone": "🎁", "titulo": _t("Presentes de Natal", "Christmas gifts", "Regalos de Navidad"),
     "problemas": [
        _presente("presente-musica", "Presente para quem ama música", "A gift for music lovers", "Regalo para quien ama la música",
                  "Som de marca conhecida para curtir em qualquer lugar.", "Trusted-brand sound to enjoy anywhere.", "Sonido de marca conocida para disfrutar donde sea."),
        _presente("presente-treino", "Presente para quem treina", "A gift for people who work out", "Regalo para quien entrena",
                  "Itens que ajudam a treinar e a se recuperar melhor.", "Gear that helps training and recovery.", "Artículos que ayudan a entrenar y recuperarse."),
        _presente("presente-pet", "Presente para quem tem pet", "A gift for pet owners", "Regalo para quien tiene mascota",
                  "Mais conforto para o pet e tranquilidade para o dono.", "More comfort for the pet, peace of mind for the owner.", "Más comodidad para la mascota y tranquilidad para el dueño."),
        _presente("presente-casa", "Presente para a casa", "A gift for the home", "Regalo para el hogar",
                  "Conforto e praticidade para o dia a dia em casa.", "Comfort and convenience at home.", "Comodidad y practicidad en casa."),
        _presente("presente-tecnologia", "Presente de tecnologia útil", "A useful tech gift", "Regalo tecnológico útil",
                  "Tecnologia que a pessoa vai usar todos os dias.", "Tech they'll use every day.", "Tecnología que usará todos los días."),
     ]},
    {"slug": "esporte", "icone": "🏃", "titulo": _t("Esporte", "Sports", "Deporte"),
     "problemas": [
        {"slug": "treinar-em-casa", "titulo": _t("Treinar em casa sem academia", "Work out at home without a gym", "Entrenar en casa sin gimnasio"),
         "resumo": _t("Pouco espaço e pouco tempo não precisam ser desculpa.", "Little space and time don't have to stop you.", "Poco espacio y poco tiempo no tienen que ser excusa."),
         "considerar": [_t("Comece com itens versáteis: elásticos e tapete servem para dezenas de exercícios.", "Start with versatile items: bands and a mat cover dozens of exercises.", "Empieza con artículos versátiles: bandas y esterilla sirven para decenas de ejercicios."),
                        _t("Veja se cabe no seu espaço e se é fácil de guardar.", "Check it fits your space and stores easily.", "Comprueba que cabe en tu espacio y se guarda fácil."),
                        _t("Constância vale mais que equipamento caro.", "Consistency matters more than expensive gear.", "La constancia vale más que el equipo caro.")],
         "busca": ["resistance band", "yoga mat", "jump rope", "dumbbell", "kettlebell", "faixa elástica", "tapete de yoga", "corda de pular", "halter"],
         "preco": [15, 1500]},
        {"slug": "roupa-de-treino", "titulo": _t("Roupa confortável para treinar", "Comfortable workout clothes", "Ropa cómoda para entrenar"),
         "resumo": _t("Tecido que respira e não atrapalha o movimento.", "Breathable fabric that moves with you.", "Tejido que respira y no estorba el movimiento."),
         "considerar": [_t("Prefira tecidos de secagem rápida (dry-fit, poliamida).", "Prefer quick-dry fabrics.", "Prefiere tejidos de secado rápido."),
                        _t("Confira a tabela de medidas da loja antes de comprar.", "Check the store's size chart first.", "Revisa la tabla de tallas de la tienda."),
                        _t("Para corrida, o tênis é o item que mais importa.", "For running, shoes matter most.", "Para correr, las zapatillas son lo más importante.")],
         "busca": ["sports bra", "gym leggings", "yoga pants", "compression shirt", "running shorts", "legging fitness", "top fitness", "camiseta dry"],
         "preco": [25, 800]},
        {"slug": "suplementos", "titulo": _t("Suplementação para treinar melhor", "Supplements to train better", "Suplementos para entrenar mejor"),
         "resumo": _t("O básico que ajuda na recuperação e na força.", "The basics that help recovery and strength.", "Lo básico que ayuda a la recuperación y la fuerza."),
         "considerar": [_t("Converse com um nutricionista ou médico antes de começar.", "Talk to a nutritionist or doctor first.", "Consulta a un nutricionista o médico antes de empezar."),
                        _t("Prefira marcas com registro na Anvisa e laudo de pureza.", "Prefer brands with regulatory approval and purity reports.", "Prefiere marcas con registro sanitario y análisis de pureza."),
                        _t("Suplemento complementa a alimentação, não substitui.", "Supplements complement food, they don't replace it.", "El suplemento complementa la alimentación, no la sustituye.")],
         "busca": ["whey", "creatina", "creatine", "protein powder", "proteína"],
         "preco": [40, 600]},
     ]},
    {"slug": "saude", "icone": "💚", "titulo": _t("Saúde corporal", "Body health", "Salud corporal"),
     "problemas": [
        {"slug": "dores-nas-costas", "titulo": _t("Aliviar dores nas costas e no pescoço", "Relieve back and neck pain", "Aliviar el dolor de espalda y cuello"),
         "resumo": _t("Para quem passa o dia sentado ou carrega tensão no corpo.", "For those who sit all day or carry tension.", "Para quien pasa el día sentado o acumula tensión."),
         "considerar": [_t("Dor forte ou persistente precisa de avaliação profissional.", "Strong or persistent pain needs a professional.", "El dolor fuerte o persistente requiere un profesional."),
                        _t("Ajustar a postura no trabalho resolve muita coisa.", "Fixing your work posture solves a lot.", "Ajustar la postura en el trabajo resuelve mucho."),
                        _t("Massageadores ajudam no relaxamento, não tratam lesões.", "Massagers help you relax; they don't treat injuries.", "Los masajeadores ayudan a relajar; no tratan lesiones.")],
         "busca": ["posture corrector", "massage gun", "neck massager", "back massager", "massageador", "corretor postural", "lumbar pillow", "almofada lombar"],
         "preco": [25, 1500]},
        {"slug": "acompanhar-peso", "titulo": _t("Acompanhar peso e medidas", "Track weight and measurements", "Controlar peso y medidas"),
         "resumo": _t("Ver a evolução motiva e ajuda a ajustar a rotina.", "Seeing progress motivates and helps you adjust.", "Ver la evolución motiva y ayuda a ajustar la rutina."),
         "considerar": [_t("Pese-se sempre no mesmo horário e nas mesmas condições.", "Weigh yourself at the same time and conditions.", "Pésate siempre a la misma hora y en las mismas condiciones."),
                        _t("Balanças com aplicativo guardam o histórico sozinhas.", "App-connected scales keep your history.", "Las básculas con app guardan el historial."),
                        _t("Percentual de gordura em balança é uma estimativa.", "Body fat on scales is an estimate.", "El porcentaje de grasa en básculas es una estimación.")],
         "busca": ["body fat scale", "bathroom scale", "smart scale", "balança digital", "balança de bioimpedância"],
         "preco": [40, 800]},
     ]},
    {"slug": "bem-estar", "icone": "🌿", "titulo": _t("Bem-estar", "Well-being", "Bienestar"),
     "problemas": [
        {"slug": "dormir-melhor", "titulo": _t("Dormir melhor", "Sleep better", "Dormir mejor"),
         "resumo": _t("Pequenos ajustes no quarto fazem diferença no descanso.", "Small bedroom changes make a real difference.", "Pequeños cambios en el dormitorio marcan la diferencia."),
         "considerar": [_t("Escuro, silêncio e temperatura amena ajudam o sono.", "Darkness, quiet and a cool room help sleep.", "Oscuridad, silencio y temperatura agradable ayudan al sueño."),
                        _t("Evite telas na última hora antes de dormir.", "Avoid screens in the last hour before bed.", "Evita pantallas en la última hora antes de dormir."),
                        _t("Insônia frequente merece conversa com um médico.", "Frequent insomnia deserves a doctor's visit.", "El insomnio frecuente merece consultar a un médico.")],
         "busca": ["sleep mask", "eye mask", "ear plugs", "earplugs", "white noise", "máscara de dormir", "protetor auricular"],
         "preco": [8, 600]},
        {"slug": "relaxar-em-casa", "titulo": _t("Relaxar depois de um dia cheio", "Unwind after a busy day", "Relajarte después de un día intenso"),
         "resumo": _t("Um ambiente mais calmo para desacelerar.", "A calmer space to slow down.", "Un ambiente más tranquilo para desconectar."),
         "considerar": [_t("Aromas suaves e luz baixa ajudam a desacelerar.", "Soft scents and low light help you slow down.", "Aromas suaves y luz tenue ayudan a relajarte."),
                        _t("Umidificador também alivia o ar seco do inverno.", "A humidifier also eases dry winter air.", "Un humidificador también alivia el aire seco."),
                        _t("Use óleos essenciais próprios para difusor.", "Use oils made for diffusers.", "Usa aceites esenciales aptos para difusor.")],
         "busca": ["aroma diffuser", "essential oil diffuser", "humidifier", "difusor", "umidificador"],
         "preco": [12, 800]},
     ]},
    {"slug": "casa", "icone": "🏠", "titulo": _t("Casa", "Home", "Hogar"),
     "problemas": [
        {"slug": "cozinha-organizada", "titulo": _t("Organizar a cozinha", "Organize your kitchen", "Organizar la cocina"),
         "resumo": _t("Mais espaço, tudo à mão e menos bagunça.", "More space, everything at hand, less clutter.", "Más espacio, todo a mano y menos desorden."),
         "considerar": [_t("Meça o espaço antes de comprar móveis ou organizadores.", "Measure the space before buying.", "Mide el espacio antes de comprar."),
                        _t("Aproveite paredes e portas: espaço vertical rende muito.", "Use walls and doors: vertical space pays off.", "Aprovecha paredes y puertas: el espacio vertical rinde."),
                        _t("Materiais laváveis facilitam a limpeza.", "Washable materials make cleaning easier.", "Los materiales lavables facilitan la limpieza.")],
         "busca": ["kitchen organizer", "spice rack", "drawer organizer", "organizador de cozinha", "porta-temperos", "organizador de gaveta"],
         "preco": [10, 600]},
        {"slug": "limpeza-facil", "titulo": _t("Limpar a casa com menos esforço", "Clean the house with less effort", "Limpiar la casa con menos esfuerzo"),
         "resumo": _t("Menos tempo limpando, mais tempo para você.", "Less time cleaning, more time for you.", "Menos tiempo limpiando, más tiempo para ti."),
         "considerar": [_t("Robôs aspiradores funcionam melhor em casas com piso livre.", "Robot vacuums work best on clear floors.", "Los robots aspiradores rinden mejor con el suelo despejado."),
                        _t("Aspiradores sem fio são práticos para o dia a dia.", "Cordless vacuums are handy for daily use.", "Las aspiradoras sin cable son prácticas a diario."),
                        _t("Confira voltagem e garantia antes de comprar.", "Check voltage and warranty first.", "Revisa voltaje y garantía antes de comprar.")],
         "busca": ["robot vacuum", "cordless vacuum", "robô aspirador", "aspirador sem fio", "aspirador vertical", "spin mop", "mop giratório"],
         "preco": [60, 6000]},
     ]},
    {"slug": "pet", "icone": "🐾", "titulo": _t("Pet", "Pets", "Mascotas"),
     "problemas": [
        {"slug": "pet-sozinho-em-casa", "titulo": _t("Pet bem cuidado quando você sai", "Pets cared for while you're out", "Tu mascota bien cuidada cuando sales"),
         "resumo": _t("Comida e água garantidas mesmo fora de casa.", "Food and water covered while you're away.", "Comida y agua garantizadas aunque no estés."),
         "considerar": [_t("Alimentador automático com horários programáveis dá tranquilidade.", "Programmable feeders give peace of mind.", "Los comederos programables dan tranquilidad."),
                        _t("Fonte de água estimula gatos a beber mais.", "Water fountains encourage cats to drink more.", "Las fuentes animan a los gatos a beber más."),
                        _t("Teste o equipamento com você em casa antes de viajar.", "Test it while you're home before traveling.", "Pruébalo estando en casa antes de viajar.")],
         "busca": ["automatic pet feeder", "automatic cat feeder", "automatic dog feeder", "pet water fountain", "cat water fountain", "alimentador automático", "bebedouro fonte"],
         "preco": [30, 1500]},
        {"slug": "passeio-seguro", "titulo": _t("Passeio seguro com o cachorro", "Safe walks with your dog", "Paseos seguros con tu perro"),
         "resumo": _t("Conforto para o pet e controle para você.", "Comfort for your dog, control for you.", "Comodidad para tu perro y control para ti."),
         "considerar": [_t("Peitoral distribui melhor a força que a coleira no pescoço.", "Harnesses spread pressure better than collars.", "El arnés reparte mejor la fuerza que el collar."),
                        _t("Meça o tórax do pet para acertar o tamanho.", "Measure your dog's chest for the right size.", "Mide el pecho de tu perro para acertar la talla."),
                        _t("Itens refletivos ajudam em passeios à noite.", "Reflective gear helps on night walks.", "Los elementos reflectantes ayudan de noche.")],
         "busca": ["dog harness", "dog leash", "peitoral para cachorro", "guia para cachorro", "coleira"],
         "preco": [15, 500]},
     ]},
    {"slug": "eletronicos", "icone": "🎧", "titulo": _t("Eletrônicos", "Electronics", "Electrónica"),
     "problemas": [
        {"slug": "fone-sem-fio", "titulo": _t("Ouvir música e falar sem fio", "Listen and talk wire-free", "Escuchar música y hablar sin cables"),
         "resumo": _t("Liberdade para treinar, trabalhar e se deslocar.", "Freedom to train, work and commute.", "Libertad para entrenar, trabajar y moverte."),
         "considerar": [_t("Veja a duração da bateria com o estojo de carga.", "Check battery life including the case.", "Revisa la batería incluyendo el estuche."),
                        _t("Para treinar, prefira resistência a suor (IPX4 ou mais).", "For workouts, look for sweat resistance (IPX4+).", "Para entrenar, busca resistencia al sudor (IPX4+)."),
                        _t("Cancelamento de ruído ajuda em ônibus e escritórios.", "Noise cancelling helps on buses and offices.", "La cancelación de ruido ayuda en transporte y oficinas.")],
         "busca": ["earbuds", "tws", "fone de ouvido", "fones de ouvido", "headphones", "wireless headphone"],
         "excluir": ["ear tips", "eartips", "hook", "holder", "stand", "suporte", "estojo para", "pouch", "silicone case", "charging case for"],
         "preco": [25, 2500]},
        {"slug": "bateria-do-celular", "titulo": _t("Celular sem bateria fora de casa", "Phone dying when you're out", "El móvil sin batería fuera de casa"),
         "resumo": _t("Energia de reserva para o dia inteiro.", "Backup power for the whole day.", "Energía de reserva para todo el día."),
         "considerar": [_t("10.000 mAh carrega a maioria dos celulares duas vezes.", "10,000 mAh charges most phones twice.", "10.000 mAh cargan la mayoría de móviles dos veces."),
                        _t("Carregamento rápido (PD) economiza tempo.", "Fast charging (PD) saves time.", "La carga rápida (PD) ahorra tiempo."),
                        _t("Para viagens de avião, até 20.000 mAh costuma ser permitido.", "For flights, up to 20,000 mAh is usually allowed.", "En avión, hasta 20.000 mAh suele estar permitido.")],
         "busca": ["power bank", "powerbank", "carregador portátil", "bateria externa"],
         "preco": [30, 1500]},
        {"slug": "som-para-reunir", "titulo": _t("Som para reunir a família e os amigos", "Sound for family and friends", "Música para reunir a familia y amigos"),
         "resumo": _t("Música boa no churrasco, na viagem e em casa.", "Good music at barbecues, trips and home.", "Buena música en asados, viajes y en casa."),
         "considerar": [_t("Resistência à água é útil para piscina e praia.", "Water resistance helps at the pool and beach.", "La resistencia al agua sirve en piscina y playa."),
                        _t("Bateria acima de 10 horas aguenta a festa inteira.", "10+ hours of battery lasts the whole party.", "Más de 10 horas de batería aguantan toda la fiesta."),
                        _t("Potência maior importa para ambientes abertos.", "More power matters outdoors.", "Más potencia importa al aire libre.")],
         "busca": ["bluetooth speaker", "alto-falante", "caixa de som", "party speaker"],
         "excluir": ["mount", "bracket", "speaker cable", "cabo de alto"],
         "preco": [40, 3000]},
     ]},
]

# Nome curto de cada caso, para os botões de tema ("Treinar em casa · Roupa para treinar")
CURTOS: dict[str, dict[str, str]] = {
    "presente-musica": _t("Música", "Music", "Música"),
    "presente-treino": _t("Quem treina", "Fitness", "Quien entrena"),
    "presente-pet": _t("Quem tem pet", "Pet owners", "Con mascota"),
    "presente-casa": _t("Casa", "Home", "Hogar"),
    "presente-tecnologia": _t("Tecnologia", "Tech", "Tecnología"),
    "treinar-em-casa": _t("Treinar em casa", "Home workouts", "Entrenar en casa"),
    "roupa-de-treino": _t("Roupa para treinar", "Workout clothes", "Ropa para entrenar"),
    "suplementos": _t("Suplementação", "Supplements", "Suplementos"),
    "dores-nas-costas": _t("Dores nas costas", "Back pain", "Dolor de espalda"),
    "acompanhar-peso": _t("Acompanhar o peso", "Tracking weight", "Controlar el peso"),
    "dormir-melhor": _t("Dormir melhor", "Sleep better", "Dormir mejor"),
    "relaxar-em-casa": _t("Relaxar depois do dia", "Unwinding", "Relajarte"),
    "cozinha-organizada": _t("Cozinha organizada", "Tidy kitchen", "Cocina ordenada"),
    "limpeza-facil": _t("Limpeza fácil", "Easy cleaning", "Limpieza fácil"),
    "pet-sozinho-em-casa": _t("Pet sozinho em casa", "Pet home alone", "Mascota sola en casa"),
    "passeio-seguro": _t("Passeio seguro", "Safe walks", "Paseos seguros"),
    "fone-sem-fio": _t("Fone sem fio", "Wireless earbuds", "Auriculares inalámbricos"),
    "bateria-do-celular": _t("Bateria do celular", "Phone battery", "Batería del móvil"),
    "som-para-reunir": _t("Som para reunir", "Sound for gatherings", "Música para reunir"),
}

_cache: dict[str, Any] = {"ts": 0.0, "data": None}
_lock = threading.Lock()


def _problemas() -> dict[str, tuple[dict, dict]]:
    return {p["slug"]: (tema, p) for tema in TEMAS for p in tema["problemas"]}


def escolhas_fixas(db: Session) -> dict[str, list[str]]:
    row = db.get(Configuracao, CHAVE_ESCOLHAS)
    return dict(row.value) if row and isinstance(row.value, dict) else {}


def filtro_lojas_publicas(s: Settings):
    """Ao público só chegam lojas confiáveis das redes, ou ofertas cadastradas à mão no painel
    (links diretos, como Amazon ou Mercado Livre)."""
    if "*" in s.lojas_confiaveis:
        return Oferta.id.is_not(None)  # LOJAS_CONFIAVEIS=* libera todas
    return or_(Oferta.provider.in_(s.lojas_confiaveis), Oferta.platform.not_in(["admitad", "awin"]))


def _automatico(db: Session, s: Settings, p: dict) -> list[Oferta]:
    termos = [Oferta.title.ilike(f"%{k}%") for k in p["busca"]]
    fora = [Oferta.title.ilike(f"%{k}%") for k in EXCLUIR_SEMPRE + p.get("excluir", [])]
    mn, mx = p["preco"]
    q = (select_ofertas_visiveis()
         .where(filtro_lojas_publicas(s), Oferta.image_url != "", Oferta.currency == "BRL",
                Oferta.price.is_not(None), Oferta.price >= mn, Oferta.price <= mx,
                or_(*termos), not_(or_(*fora)))
         .order_by(Oferta.price, Oferta.id).limit(400))
    cands = list(db.scalars(q))
    if len(cands) < 2:
        return cands
    # Uma de cada faixa: a mais acessível, a do meio e a mais completa (top 15% de preço).
    escolha = [cands[0], cands[len(cands) // 2], cands[int(len(cands) * 0.85)]]
    vistos, out = set(), []
    for o in escolha:
        if o.id not in vistos:
            vistos.add(o.id)
            out.append(o)
    return out


def _escolhas(db: Session, s: Settings, slug: str, p: dict, fixas: dict[str, list[str]]) -> list[Oferta]:
    ids = [i for i in fixas.get(slug, []) if isinstance(i, str)]
    if ids:
        por_id = {o.id: o for o in db.scalars(select_ofertas_visiveis().where(Oferta.id.in_(ids)))}
        fixadas = [por_id[i] for i in ids if i in por_id]
        if len(fixadas) >= 2:
            return fixadas[:3]
    if not s.problemas_automatico:
        return []  # curadoria: sem escolhas feitas à mão, a página não vai ao ar
    return _automatico(db, s, p)


def _lojas(db: Session, o: Oferta) -> list[dict[str, str]]:
    """O mesmo produto em cada loja parceira (curadoria): o visitante escolhe onde comprar."""
    lojas = [{"loja": o.provider, "url": f"/r/{o.id}"}]
    if o.source == "curadoria" and o.external_product_id:
        outras = db.scalars(select_ofertas_visiveis().where(
            Oferta.external_product_id == o.external_product_id, Oferta.source == "curadoria",
            Oferta.id != o.id).order_by(Oferta.platform))
        lojas += [{"loja": x.provider, "url": f"/r/{x.id}"} for x in outras]
    return lojas


def _motivo(o: Oferta, i: int) -> dict[str, str]:
    """Motivo escrito para o produto (curadoria); sem ele, o texto padrão da faixa."""
    tr = o.translations or {}
    return {l: ((tr.get(l) or {}).get("description") or (o.description if l == "pt" else "") or NIVEIS[i]["motivo"][l])
            for l in ("pt", "en", "es")}


def _resumo(tema: dict, p: dict, n: int) -> dict[str, Any]:
    return {"slug": p["slug"], "titulo": p["titulo"], "curto": CURTOS.get(p["slug"], p["titulo"]),
            "resumo": p["resumo"], "tema": tema["slug"], "produtos": n}


def montar(db: Session, s: Settings) -> dict[str, Any]:
    from .routers.public import _oferta
    fixas = escolhas_fixas(db)
    temas, detalhes = [], {}
    for tema in TEMAS:
        itens = []
        for p in tema["problemas"]:
            ofertas = _escolhas(db, s, p["slug"], p, fixas)
            if len(ofertas) < 2:
                continue  # sem produtos bons, a página não vai ao ar
            escolhas = [{"nivel": {k: NIVEIS[i][k] for k in ("chave", "pt", "en", "es")}, "motivo": _motivo(o, i),
                         "oferta": _oferta(o), "lojas": _lojas(db, o)} for i, o in enumerate(ofertas)]
            detalhes[p["slug"]] = {**_resumo(tema, p, len(ofertas)), "considerar": p["considerar"],
                                   "tema_titulo": tema["titulo"], "tema_icone": tema["icone"], "escolhas": escolhas}
            itens.append(_resumo(tema, p, len(ofertas)))
        if itens:
            temas.append({"slug": tema["slug"], "titulo": tema["titulo"], "icone": tema["icone"], "problemas": itens})
    return {"temas": temas, "detalhes": detalhes}


def obter(db: Session, s: Settings, ttl: float = 1800) -> dict[str, Any]:
    """Páginas prontas na memória. Se estiverem velhas, quem pede recebe a versão pronta na hora
    e a atualização acontece em segundo plano: o visitante nunca espera a montagem."""
    with _lock:
        data, idade = _cache["data"], time.time() - _cache["ts"]
    if data is not None:
        if idade >= ttl:
            _atualizar_em_segundo_plano(s)
        return data
    data = montar(db, s)
    with _lock:
        _cache.update(ts=time.time(), data=data)
    return data


_sessionmaker = None
_atualizando = threading.Event()


def reiniciar() -> None:
    """Nova aplicação: esquece o banco e as páginas da anterior."""
    global _sessionmaker
    _sessionmaker = None
    with _lock:
        _cache.update(ts=0.0, data=None)


def configurar(sessionmaker, s: Settings) -> None:
    """Chamado na inicialização: guarda como abrir sessões e já deixa as páginas prontas."""
    global _sessionmaker
    _sessionmaker = sessionmaker
    _atualizar_em_segundo_plano(s)


def _atualizar_em_segundo_plano(s: Settings) -> None:
    if _sessionmaker is None or _atualizando.is_set():
        return
    _atualizando.set()

    def tarefa():
        try:
            with _sessionmaker() as db:
                data = montar(db, s)
            with _lock:
                _cache.update(ts=time.time(), data=data)
        except Exception:
            pass
        finally:
            _atualizando.clear()

    threading.Thread(target=tarefa, daemon=True).start()


def limpar_cache() -> None:
    """Após mudança de produtos: com sessão configurada, remonta em segundo plano mantendo a versão
    atual no ar; sem ela (testes), descarta para a próxima leitura montar de novo."""
    if _sessionmaker is not None:
        with _lock:
            _cache["ts"] = 0.0
        return
    with _lock:
        _cache.update(ts=0.0, data=None)


def status_painel(db: Session, s: Settings) -> list[dict[str, Any]]:
    """Para o painel: cada problema, se está no ar e de onde vêm os produtos."""
    fixas = escolhas_fixas(db)
    out = []
    for slug, (tema, p) in _problemas().items():
        ofertas = _escolhas(db, s, slug, p, fixas)
        out.append({"slug": slug, "tema": tema["titulo"]["pt"], "titulo": p["titulo"]["pt"],
                    "no_ar": len(ofertas) >= 2,
                    "fixadas": fixas.get(slug, []),
                    "produtos": [{"id": o.id, "title": o.title, "price": float(o.price) if o.price is not None else None,
                                  "provider": o.provider} for o in ofertas]})
    return out


def fixar(db: Session, slug: str, ids: list[str]) -> Optional[list[str]]:
    if slug not in _problemas():
        return None
    row = db.get(Configuracao, CHAVE_ESCOLHAS)
    valor = dict(row.value) if row and isinstance(row.value, dict) else {}
    valor[slug] = [i.strip() for i in ids if i.strip()][:3]
    if not valor[slug]:
        valor.pop(slug)
    if row is None:
        db.add(Configuracao(key=CHAVE_ESCOLHAS, value=valor))
    else:
        row.value = valor
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(row, "value")
    db.commit()
    limpar_cache()
    return valor.get(slug, [])


def ids_publicos(db: Session, s: Settings) -> list[str]:
    data = obter(db, s)
    return [e["oferta"]["id"] for d in data["detalhes"].values() for e in d["escolhas"]]
