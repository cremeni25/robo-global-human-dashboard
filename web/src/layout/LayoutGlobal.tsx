import { Link, Outlet, useLocation } from "react-router-dom";
import { useLanguage } from "../contexts/LanguageContext";
const labels={pt:["Início","Sobre"],en:["Home","About"],es:["Inicio","Acerca de"]};
const rodape={pt:"Uma iniciativa Cremeni. Produtos vendidos e entregues pelas lojas parceiras Amazon e Mercado Livre. Como Associado da Amazon, o Robô Global recebe por compras qualificadas.",en:"A Cremeni initiative. Products sold and shipped by partner stores Amazon and Mercado Livre. As an Amazon Associate, Robô Global earns from qualifying purchases.",es:"Una iniciativa de Cremeni. Productos vendidos y enviados por las tiendas asociadas Amazon y Mercado Livre. Como Afiliado de Amazon, Robô Global recibe ingresos por compras válidas."};
export default function LayoutGlobal(){
 const {lang,setLang}=useLanguage();const loc=useLocation();
 const nav=[["/",""],["/sobre",""]];
 return <div className="rg-shell"><header className="rg-header"><div className="rg-header-inner">
 <Link className="rg-brand" to="/" aria-label={lang==="pt"?"Robô Global, início":lang==="en"?"Robô Global, home":"Robô Global, inicio"}><span className="rg-brand-icon">✳</span><span>ROBÔ <strong>GLOBAL</strong><small>BY CREMENI</small></span></Link>
 <nav className="rg-nav" aria-label={lang==="pt"?"Navegação principal":lang==="en"?"Main navigation":"Navegación principal"}>{nav.map(([url],i)=><Link key={url} className={loc.pathname===url?"rg-nav-active":""} to={url}>{labels[lang][i]}</Link>)}</nav>
 <div className="rg-languages" aria-label={lang==="en"?"Language":"Idioma"}>{(["pt","en","es"] as const).map(code=><button key={code} type="button" aria-pressed={lang===code} className={lang===code?"rg-lang-active":""} onClick={()=>setLang(code)}>{code.toUpperCase()}</button>)}</div>
 </div></header><main><Outlet/></main><footer className="rg-rodape">✳ Robô Global · {rodape[lang]}</footer></div>
}
