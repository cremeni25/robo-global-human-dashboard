import { Link } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";

const copy = {
  pt: {
    eyebrow:"INTELIGÊNCIA PARA ESCOLHAS REAIS",
    title:"O mundo oferece possibilidades. Você merece encontrar as suas.",
    lead:"O Robô Global aproxima necessidades reais de caminhos úteis. Sem complicação, sem pressão e no seu ritmo.",
    primary:"Explorar possibilidades",secondary:"Entender como funciona",
    note:"Você escolhe o caminho. A tecnologia ajuda a enxergar as opções.",
    intro:"Um espaço feito para pessoas, não para cliques.",
    introText:"Seja para aprender, cuidar do cotidiano ou encontrar soluções, comece pelo que faz sentido para você.",
    paths:[["Descobrir","Encontre possibilidades que combinam com seu momento."],["Entender","Compare informações e avance com mais clareza."],["Decidir","Siga apenas quando a escolha fizer sentido."]],
    promise:"Sua confiança vale mais que uma visita.",
    promiseText:"Indicações identificadas, informações claras e liberdade para decidir. Algumas recomendações podem gerar remuneração de afiliado, sem custo adicional informado por nós.",
    action:"Conhecer os temas", foot:"Robô Global · Tecnologia a serviço de escolhas humanas.",
    status:"Catálogo disponível: explore as soluções verificadas."
  },
  en: {
    eyebrow:"INTELLIGENCE FOR REAL-LIFE CHOICES",
    title:"A world of possibilities. Find what matters to you.",
    lead:"Robô Global connects everyday needs with useful paths forward. No pressure, no needless complexity. Your pace, your choice.",
    primary:"Explore possibilities",secondary:"How it works",
    note:"You set the direction. Technology helps you see your options.",
    intro:"Built around people, not page views.",
    introText:"Whether you want to learn, simplify daily life or find solutions, start with what matters to you.",
    paths:[["Discover","Explore ideas that fit where you are today."],["Understand","Look at your options and move forward with clarity."],["Choose","Take the next step only when it feels right."]],
    promise:"Your trust matters more than a single visit.",
    promiseText:"Clear information, transparent recommendations and room to decide. Some recommendations may earn us an affiliate commission.",
    action:"Explore topics",foot:"Robô Global · Technology shaped around people.",
    status:"Catalogue available: explore verified solutions."
  },
  es: {
    eyebrow:"INTELIGENCIA PARA DECISIONES REALES",
    title:"Un mundo de posibilidades. Encuentra las que son para ti.",
    lead:"Robô Global conecta tus necesidades con opciones útiles. Sin presiones, sin complicaciones y a tu ritmo.",
    primary:"Explorar posibilidades",secondary:"Cómo funciona",
    note:"Tú marcas el rumbo. La tecnología te ayuda a ver las opciones.",
    intro:"Un espacio pensado para personas, no para visitas.",
    introText:"Si buscas aprender, resolver algo cotidiano o descubrir nuevas opciones, empieza por lo que te importa.",
    paths:[["Descubre","Explora posibilidades que encajan con tu momento."],["Comprende","Conoce tus opciones y avanza con claridad."],["Decide","Da el siguiente paso solo cuando tenga sentido para ti."]],
    promise:"Tu confianza vale más que una visita.",
    promiseText:"Información clara, recomendaciones transparentes y libertad para elegir. Algunas recomendaciones pueden generar comisiones de afiliación.",
    action:"Explorar temas",foot:"Robô Global · Tecnología al servicio de las personas.",
    status:"Catálogo disponible: explora soluciones verificadas."
  }
};
export default function Home() {
  const {lang}=useLanguage(); const t=copy[lang];
  return <div className="rg-home">
    <section className="rg-hero"><div className="rg-orbit rg-orbit-one"/><div className="rg-orbit rg-orbit-two"/>
      <div className="rg-hero-content"><div className="rg-eyebrow"><span className="rg-dot"/> {t.eyebrow}</div>
      <h1>{t.title}</h1><p className="rg-lead">{t.lead}</p>
      <div className="rg-actions"><Link className="rg-button rg-button-primary" to="/nichos">{t.primary} <span aria-hidden>↗</span></Link><a className="rg-button rg-button-outline" href="#como-funciona">{t.secondary} <span aria-hidden>↓</span></a></div>
      <p className="rg-hero-note">✦ {t.note}</p></div>
      <div className="rg-hero-art" aria-hidden="true"><div className="rg-globe"><div className="rg-globe-line rg-l1"/><div className="rg-globe-line rg-l2"/><div className="rg-globe-core">RG<span>∞</span></div></div></div>
    </section>
    <section className="rg-section" id="como-funciona"><div className="rg-section-heading"><span className="rg-kicker">01 / ROBÔ GLOBAL</span><h2>{t.intro}</h2><p>{t.introText}</p></div>
      <div className="rg-paths">{t.paths.map((item,i)=><article className="rg-path" key={i}><span className="rg-path-number">0{i+1}</span><div className="rg-path-symbol">{["✳","◎","↗"][i]}</div><h3>{item[0]}</h3><p>{item[1]}</p></article>)}</div></section>
    <section className="rg-promise"><div><span className="rg-kicker">02 / {lang==="pt"?"CONFIANÇA":lang==="en"?"TRUST":"CONFIANZA"}</span><h2>{t.promise}</h2><p>{t.promiseText}</p><Link className="rg-button rg-button-light" to="/nichos">{t.action} ↗</Link></div><div className="rg-promise-mark" aria-hidden="true">✳</div></section>
    <div className="rg-status" role="status">● {t.status}</div><footer className="rg-footer">{t.foot}</footer>
  </div>;
}
