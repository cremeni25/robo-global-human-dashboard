import { Link } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";

const copy = {
  pt: { tag: "QUEM SOMOS", title: "Feito por quem vive o esporte.",
    lead: "O Robô Global é uma iniciativa da Cremeni para ajudar nadadores e triatletas a escolher melhor: o que considerar, e três boas opções de marcas conhecidas para cada situação do treino e da prova.",
    blocos: [
      ["Cremeni", "Uma empresa dedicada ao esporte e à vida ativa, com campanhas contra o sedentarismo e a favor da prática esportiva."],
      ["Experiência com atletas e clubes", "A curadoria se apoia na experiência da Cremeni com atletas e clubes, incluindo a AGP Intelligence, sistema de avaliação longitudinal de atletas usado por clubes."],
      ["Como escolhemos", "Só indicamos marcas conhecidas, vendidas por lojas em que você já confia. Explicamos o motivo de cada escolha e dizemos quando procurar um profissional."],
    ],
    cta: "Ver os temas" },
  en: { tag: "ABOUT US", title: "Made by people who live sport.",
    lead: "Robô Global is a Cremeni initiative to help swimmers and triathletes choose better: what to consider, and three good options from trusted brands for each training and racing situation.",
    blocos: [
      ["Cremeni", "A company dedicated to sport and active living, running campaigns against sedentary lifestyles."],
      ["Experience with athletes and clubs", "Our picks draw on Cremeni's experience with athletes and clubs, including AGP Intelligence, a longitudinal athlete assessment system used by clubs."],
      ["How we choose", "We only recommend well-known brands sold by stores you already trust. We explain every pick and tell you when to see a professional."],
    ],
    cta: "See topics" },
  es: { tag: "QUIÉNES SOMOS", title: "Hecho por quienes viven el deporte.",
    lead: "Robô Global es una iniciativa de Cremeni para ayudar a nadadores y triatletas a elegir mejor: qué tener en cuenta y tres buenas opciones de marcas conocidas para cada situación.",
    blocos: [
      ["Cremeni", "Una empresa dedicada al deporte y a la vida activa, con campañas contra el sedentarismo."],
      ["Experiencia con atletas y clubes", "La selección se apoya en la experiencia de Cremeni con atletas y clubes, incluida AGP Intelligence, sistema de evaluación longitudinal de atletas usado por clubes."],
      ["Cómo elegimos", "Solo recomendamos marcas conocidas, vendidas por tiendas en las que ya confías. Explicamos cada elección y te decimos cuándo buscar a un profesional."],
    ],
    cta: "Ver los temas" },
};

export default function Sobre() {
  const { lang } = useLanguage(); const t = copy[lang];
  return <div className="rg-store">
    <section className="rg-store-hero"><div className="rg-store-inner">
      <span className="rg-catalog-eyebrow">✳ {t.tag}</span><h1>{t.title}</h1><p>{t.lead}</p>
    </div></section>
    <div className="rg-store-inner rg-store-body">
      <div className="rg-problemas">{t.blocos.map(([titulo, texto]) =>
        <article className="rg-problema-card" key={titulo}><strong>{titulo}</strong><span>{texto}</span></article>)}</div>
      <p className="rg-store-more"><Link className="rg-retry" to="/">{t.cta} →</Link></p>
    </div>
  </div>;
}
