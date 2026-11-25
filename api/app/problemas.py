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


def _p(slug, titulo, resumo, considerar):
    return {"slug": slug, "titulo": _t(*titulo), "resumo": _t(*resumo), "considerar": [_t(*c) for c in considerar],
            "busca": [], "preco": [0, 0]}


_PROFISSIONAL = ("Dor que persiste ou piora precisa de avaliação de um fisioterapeuta ou médico do esporte.",
                 "Pain that persists or worsens needs a physiotherapist or sports doctor.",
                 "El dolor que persiste o empeora necesita un fisioterapeuta o médico deportivo.")

# Foco: natação e triathlon. O Robô Global é uma iniciativa da Cremeni.
TEMAS: list[dict[str, Any]] = [
    {"slug": "natacao", "icone": "🏊", "titulo": _t("Natação", "Swimming", "Natación"),
     "problemas": [
        _p("oculos-natacao", ("Óculos que não embaçam nem vazam", "Goggles that don't fog or leak", "Gafas que no se empañan ni filtran"),
           ("Enxergar bem a borda e o relógio muda o treino.", "Seeing the wall and the clock changes your training.", "Ver bien la pared y el reloj cambia el entrenamiento."),
           [("Teste a vedação: encoste no rosto sem a tira; bom óculos fica preso sozinho.", "Test the seal: press them on without the strap; good goggles stay on.", "Prueba el sellado: apóyalas sin la tira; las buenas se quedan solas."),
            ("Lente espelhada ajuda em piscina aberta e águas abertas; clara, em piscina coberta.", "Mirrored lenses help outdoors; clear lenses suit indoor pools.", "Lentes espejadas ayudan al aire libre; claras, en piscina cubierta."),
            ("Não passe o dedo por dentro da lente: isso tira o antiembaçante.", "Don't rub inside the lens: it removes the anti-fog coating.", "No frotes el interior de la lente: quita el antiempañante.")]),
        _p("natacao-basico", ("Começar a nadar com o equipamento certo", "Start swimming with the right gear", "Empezar a nadar con el equipo correcto"),
           ("O básico que faz diferença desde a primeira aula.", "The basics that matter from day one.", "Lo básico que importa desde la primera clase."),
           [("Touca de silicone dura mais e protege melhor o cabelo que a de tecido.", "Silicone caps last longer and protect hair better than fabric ones.", "El gorro de silicona dura más y protege mejor el cabello."),
            ("Enxágue tudo com água doce depois do treino: o cloro desgasta o material.", "Rinse everything in fresh water after training: chlorine wears gear out.", "Enjuaga todo con agua dulce: el cloro desgasta el material."),
            ("Uma mochila ventilada evita mau cheiro e mofo no equipamento.", "A ventilated bag prevents odor and mold.", "Una mochila ventilada evita olores y moho.")]),
        _p("tecnica-natacao", ("Evoluir a técnica nos treinos", "Improve your technique in training", "Mejorar la técnica en los entrenamientos"),
           ("Acessórios que isolam braço e perna para corrigir o nado.", "Tools that isolate arms and legs to fix your stroke.", "Accesorios que aíslan brazos y piernas para corregir la brazada."),
           [("Prancha trabalha a pernada; pull buoy trabalha a braçada.", "Kickboards train the kick; pull buoys train the pull.", "La tabla trabaja la patada; el pull buoy, la brazada."),
            ("Nadadeira curta melhora a pernada sem tirar o ritmo do nado.", "Short fins improve the kick without changing your rhythm.", "Las aletas cortas mejoran la patada sin cambiar el ritmo."),
            ("Peça ao seu treinador para encaixar os acessórios na série certa.", "Ask your coach to fit the tools into the right sets.", "Pide a tu entrenador que los incluya en las series correctas.")]),
        _p("roupa-competicao", ("Sunga e maiô: do treino à competição", "Swimwear: from training to racing", "Bañador: del entrenamiento a la competición"),
           ("Do tecido que resiste ao cloro ao traje tecnológico de prova.", "From chlorine-resistant fabric to high-tech race suits.", "Del tejido resistente al cloro al traje técnico de competición."),
           [("Para treinar, prefira tecido resistente ao cloro: dura muito mais.", "For training, choose chlorine-resistant fabric: it lasts much longer.", "Para entrenar, elige tejido resistente al cloro: dura mucho más."),
            ("Traje de competição é justo de propósito: siga a tabela de tamanhos da marca.", "Race suits are meant to be tight: follow the brand's size chart.", "El traje de competición es ajustado a propósito: sigue la tabla de tallas."),
            ("Confira se a sua competição exige traje aprovado pela federação (World Aquatics).", "Check whether your meet requires a federation-approved suit (World Aquatics).", "Comprueba si tu competición exige traje aprobado (World Aquatics).")]),
     ]},
    {"slug": "triathlon", "icone": "🏅", "titulo": _t("Triathlon", "Triathlon", "Triatlón"),
     "problemas": [
        _p("aguas-abertas", ("Nadar em águas abertas com segurança", "Open-water swimming safely", "Nadar en aguas abiertas con seguridad"),
           ("Mar, rio e represa pedem cuidados que a piscina não pede.", "Sea, river and lake need care a pool doesn't.", "Mar, río y lago exigen cuidados que la piscina no."),
           [("Nunca nade sozinho em águas abertas; a boia de segurança deixa você visível.", "Never swim alone in open water; a safety buoy keeps you visible.", "Nunca nades solo; la boya de seguridad te hace visible."),
            ("Roupa de neoprene aquece e ajuda a flutuar; verifique se a prova permite.", "Wetsuits warm you and add buoyancy; check the race rules.", "El neopreno abriga y ayuda a flotar; revisa las reglas de la prueba."),
            ("Óculos de visão ampla ajudam a se orientar pelas boias.", "Wide-view goggles help you sight the buoys.", "Las gafas de visión amplia ayudan a orientarte con las boyas.")]),
        _p("primeiro-triathlon", ("Meu primeiro triathlon: o essencial", "My first triathlon: the essentials", "Mi primer triatlón: lo esencial"),
           ("O mínimo para nadar, pedalar e correr sem perder tempo na transição.", "The minimum to swim, bike and run without wasting time in transition.", "Lo mínimo para nadar, pedalear y correr sin perder tiempo en la transición."),
           [("Capacete é obrigatório no ciclismo de qualquer prova.", "A helmet is mandatory on the bike in every race.", "El casco es obligatorio en el ciclismo de cualquier prueba."),
            ("Macaquinho de triathlon serve para as três modalidades: sem troca de roupa.", "A tri suit works for all three legs: no changing.", "El traje de triatlón sirve para las tres disciplinas: sin cambiarse."),
            ("Cadarço elástico economiza segundos preciosos na transição para a corrida.", "Elastic laces save precious seconds in the run transition.", "Los cordones elásticos ahorran segundos en la transición.")]),
        _p("corrida-triathlon", ("Correr melhor no triathlon", "Run better in triathlon", "Correr mejor en el triatlón"),
           ("O tênis certo para a última e mais dura parte da prova.", "The right shoe for the last and hardest leg.", "La zapatilla correcta para la última y más dura etapa."),
           [("Tênis com bom amortecimento poupa as pernas depois do ciclismo.", "Well-cushioned shoes spare your legs after the bike.", "Una buena amortiguación cuida las piernas tras el ciclismo."),
            ("Experimente no fim do dia, quando o pé está mais inchado.", "Try them on late in the day, when feet are larger.", "Pruébatelas al final del día, cuando el pie está más hinchado."),
            ("Troque o tênis a cada 600 a 800 km de uso.", "Replace shoes every 600 to 800 km.", "Cambia las zapatillas cada 600 a 800 km.")]),
     ]},
    {"slug": "treino", "icone": "💪", "titulo": _t("Treino e recuperação", "Training and recovery", "Entrenamiento y recuperación"),
     "problemas": [
        _p("medir-treinos", ("Medir treinos e contar voltas", "Track workouts and count laps", "Medir entrenamientos y contar largos"),
           ("Saber o que você nadou, pedalou e correu para evoluir de verdade.", "Know what you swam, rode and ran to really improve.", "Saber lo que nadaste, pedaleaste y corriste para mejorar."),
           [("Para natação, o relógio precisa ter modo piscina e ser à prova d'água (5 ATM ou mais).", "For swimming, the watch needs a pool mode and 5 ATM+ water resistance.", "Para nadar, el reloj necesita modo piscina y 5 ATM o más."),
            ("Para triathlon, prefira modelos com GPS e modo multiesporte.", "For triathlon, prefer GPS and multisport mode.", "Para triatlón, prefiere GPS y modo multideporte."),
            ("O registro só ajuda se você olhar a evolução semana a semana.", "Data only helps if you review progress weekly.", "Los datos solo ayudan si revisas la evolución semanal.")]),
        _p("ombro-nadador", ("Prevenir dor no ombro e fortalecer", "Prevent shoulder pain and get stronger", "Prevenir el dolor de hombro y fortalecerse"),
           ("O \"ombro de nadador\" se previne fora d'água.", "Swimmer's shoulder is prevented out of the water.", "El \"hombro de nadador\" se previene fuera del agua."),
           [("Elásticos fortalecem os músculos que estabilizam o ombro: poucos minutos antes do treino.", "Bands strengthen the stabilizing muscles: a few minutes before training.", "Las bandas fortalecen los estabilizadores: unos minutos antes de entrenar."),
            ("Liberação miofascial e massagem ajudam na recuperação, não tratam lesão.", "Foam rolling and massage aid recovery; they don't treat injuries.", "La liberación miofascial y el masaje ayudan a recuperar; no tratan lesiones."),
            _PROFISSIONAL]),
     ]},
    {"slug": "nutricao", "icone": "🥤", "titulo": _t("Nutrição esportiva", "Sports nutrition", "Nutrición deportiva"),
     "problemas": [
        _p("energia-prova", ("Hidratação e energia na prova longa", "Hydration and energy for long races", "Hidratación y energía en pruebas largas"),
           ("Não deixar a energia acabar antes da linha de chegada.", "Don't run out of energy before the finish.", "No quedarte sin energía antes de la meta."),
           [("Em provas acima de 1 hora, gel de carboidrato evita a quebra.", "In races over an hour, carb gels prevent bonking.", "En pruebas de más de una hora, el gel evita el bajón."),
            ("Repor sais minerais importa no calor e em suor intenso.", "Replacing electrolytes matters in heat and heavy sweat.", "Reponer sales importa con calor y sudor intenso."),
            ("Teste tudo nos treinos; nunca estreie suplemento no dia da prova.", "Test everything in training; never try something new on race day.", "Prueba todo en los entrenamientos; nada nuevo el día de la prueba.")]),
        _p("proteina-creatina", ("Proteína e creatina para treinar mais", "Protein and creatine to train more", "Proteína y creatina para entrenar más"),
           ("O básico da suplementação para força e recuperação.", "The basics of supplements for strength and recovery.", "Lo básico de la suplementación para fuerza y recuperación."),
           [("Converse com um nutricionista esportivo antes de começar.", "Talk to a sports nutritionist before starting.", "Habla con un nutricionista deportivo antes de empezar."),
            ("Prefira marcas com registro na Anvisa e laudo de pureza.", "Prefer brands with regulatory approval and purity reports.", "Prefiere marcas con registro sanitario y análisis de pureza."),
            ("Suplemento complementa a alimentação, não substitui.", "Supplements complement food, they don't replace it.", "El suplemento complementa la alimentación, no la sustituye.")]),
     ]},
    {"slug": "mente", "icone": "🧠", "titulo": _t("Mente do atleta", "Athlete's mind", "Mente del atleta"),
     "problemas": [
        _p("ansiedade-prova", ("Controlar a ansiedade antes da prova", "Handle pre-race anxiety", "Controlar la ansiedad antes de la prueba"),
           ("Transformar o nervosismo em foco na hora que importa.", "Turn nerves into focus when it matters.", "Convertir los nervios en foco cuando importa."),
           [("Um pouco de ansiedade é normal e até ajuda o desempenho.", "Some anxiety is normal and can even help performance.", "Algo de ansiedad es normal e incluso ayuda."),
            ("Rotina de aquecimento e respiração antes da largada acalma o corpo.", "A warm-up and breathing routine calms the body before the start.", "Una rutina de calentamiento y respiración calma el cuerpo."),
            ("Se a ansiedade atrapalha o sono ou o treino, procure um psicólogo do esporte.", "If anxiety affects sleep or training, see a sports psychologist.", "Si la ansiedad afecta el sueño o el entrenamiento, busca un psicólogo deportivo.")]),
        _p("disciplina-treino", ("Motivação e disciplina para treinar", "Motivation and discipline to train", "Motivación y disciplina para entrenar"),
           ("Constância vence talento quando o talento não treina.", "Consistency beats talent when talent doesn't train.", "La constancia vence al talento cuando el talento no entrena."),
           [("Metas pequenas e semanais funcionam melhor que metas enormes.", "Small weekly goals work better than huge ones.", "Metas pequeñas y semanales funcionan mejor que metas enormes."),
            ("Treinar em grupo ou com equipe aumenta a frequência.", "Training with a group or team raises consistency.", "Entrenar en grupo aumenta la constancia."),
            ("Histórias de atletas reais ajudam nos dias sem vontade.", "Real athletes' stories help on low-motivation days.", "Las historias de atletas reales ayudan en los días sin ganas.")]),
     ]},
]

# Nome curto de cada caso, para os botões de tema
CURTOS: dict[str, dict[str, str]] = {
    "oculos-natacao": _t("Óculos", "Goggles", "Gafas"),
    "natacao-basico": _t("Começar a nadar", "Getting started", "Empezar a nadar"),
    "tecnica-natacao": _t("Técnica", "Technique", "Técnica"),
    "roupa-competicao": _t("Sunga e maiô", "Swimwear", "Bañador"),
    "aguas-abertas": _t("Águas abertas", "Open water", "Aguas abiertas"),
    "primeiro-triathlon": _t("Primeiro triathlon", "First triathlon", "Primer triatlón"),
    "corrida-triathlon": _t("Corrida", "Running", "Carrera"),
    "medir-treinos": _t("Medir treinos", "Tracking", "Medir entrenos"),
    "ombro-nadador": _t("Ombro do nadador", "Swimmer's shoulder", "Hombro de nadador"),
    "energia-prova": _t("Energia na prova", "Race fuel", "Energía en carrera"),
    "proteina-creatina": _t("Proteína e creatina", "Protein and creatine", "Proteína y creatina"),
    "ansiedade-prova": _t("Ansiedade na prova", "Race anxiety", "Ansiedad en carrera"),
    "disciplina-treino": _t("Disciplina", "Discipline", "Disciplina"),
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
