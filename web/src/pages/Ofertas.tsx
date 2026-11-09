import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { localizeOffer } from "../catalogCopy";
import { useLanguage } from "../contexts/LanguageContext";
import { API_URL } from "../config";

type Offer = { id:string; title:string; description?:string; image_url?:string; price?:number|null; currency?:string; market:string; language:string; url:string; provider?:string };
type Phase = "loading" | "ready" | "error";
const PAGE = 24;
const copy = {
 pt:{eyebrow:"CATÁLOGO ROBÔ GLOBAL",title:"Possibilidades reais. Escolhas suas.",lead:"Explore soluções de parceiros com autorização comercial verificada. Você decide se deseja visitar o fornecedor.",search:"Buscar uma solução",count:"solução disponível",counts:"soluções disponíveis",open:"Conhecer no site do parceiro",more:"Ver mais",notice:"Alguns links são de afiliados. Podemos receber uma comissão por compras qualificadas, sem cobrança adicional do ROBÔ GLOBAL. Preços e disponibilidade são definidos pelo parceiro.",empty:"Nenhuma solução corresponde à sua busca.",error:"Não foi possível carregar o catálogo neste momento.",retry:"Tentar novamente",back:"Voltar ao início",secure:"Fornecedor externo · Link rastreável",from:"a partir de"},
 en:{eyebrow:"ROBÔ GLOBAL CATALOGUE",title:"Real possibilities. Your choice.",lead:"Explore solutions from commercially verified partners. You decide whether to visit the provider.",search:"Search solutions",count:"solution available",counts:"solutions available",open:"Visit partner website",more:"Show more",notice:"Some links are affiliate links. We may earn a commission on qualifying purchases at no additional ROBÔ GLOBAL charge. Prices and availability are set by the partner.",empty:"No solutions match your search.",error:"We couldn't load the catalogue right now.",retry:"Try again",back:"Back to home",secure:"External partner · Tracked link",from:"from"},
 es:{eyebrow:"CATÁLOGO ROBÔ GLOBAL",title:"Posibilidades reales. Tú decides.",lead:"Explora soluciones de socios con autorización comercial verificada. Tú decides si visitar al proveedor.",search:"Buscar soluciones",count:"solución disponible",counts:"soluciones disponibles",open:"Visitar al proveedor",more:"Ver más",notice:"Algunos enlaces son de afiliación. Podemos recibir una comisión por compras válidas, sin cargo adicional de ROBÔ GLOBAL. Precios y disponibilidad los define el socio.",empty:"Ninguna solución coincide con tu búsqueda.",error:"No pudimos cargar el catálogo ahora.",retry:"Intentar de nuevo",back:"Volver al inicio",secure:"Proveedor externo · Enlace rastreable",from:"desde"}
};
const locales = { pt: "pt-BR", en: "en-US", es: "es-ES" } as const;

function isOffer(v: unknown): v is Offer {
 if (!v || typeof v !== "object") return false;
 const x = v as Partial<Offer>;
 return typeof x.id === "string" && typeof x.title === "string" && typeof x.url === "string" && x.url.startsWith("/r/");
}

export default function Ofertas(){
 const {lang}=useLanguage();const t=copy[lang];const [params]=useSearchParams();
 const [query,setQuery]=useState(()=>params.get("q")||"");
 const [term,setTerm]=useState(query);
 const [items,setItems]=useState<Offer[]>([]),[total,setTotal]=useState(0),[page,setPage]=useState(1);
 const [phase,setPhase]=useState<Phase>("loading"),[attempt,setAttempt]=useState(0);
 const dor=params.get("dor")||"";

 // A busca acontece no servidor: funciona com centenas de milhares de produtos.
 useEffect(()=>{const id=setTimeout(()=>{setTerm(query.trim());setPage(1);},350);return()=>clearTimeout(id);},[query]);
 useEffect(()=>{
  const controller=new AbortController();
  const qs=new URLSearchParams({page:String(page),limit:String(PAGE)});
  if(term)qs.set("q",term);
  if(dor)qs.set("dor",dor);
  fetch(API_URL+"/public/ofertas?"+qs,{signal:controller.signal,headers:{Accept:"application/json"}})
   .then(r=>{if(!r.ok)throw new Error("catalogue_unavailable");return r.json();})
   .then((body:unknown)=>{
    if(!body||typeof body!=="object"||!("data" in body)||!Array.isArray(body.data))throw new Error("invalid_catalogue");
    const valid=(body.data as unknown[]).filter(isOffer);
    const count=Number((body as {total?:unknown}).total)||0;
    setItems(prev=>page===1?valid:[...prev,...valid]);setTotal(count);setPhase("ready");
   })
   .catch(()=>{if(!controller.signal.aborted)setPhase("error");});
  return()=>controller.abort();
 },[term,page,dor,attempt]);

 const price=(o:Offer)=>o.price!=null&&o.currency?new Intl.NumberFormat(locales[lang],{style:"currency",currency:o.currency}).format(o.price):"";
 return <div className="rg-catalog">
  <section className="rg-catalog-hero"><div className="rg-catalog-hero-inner">
   <span className="rg-catalog-eyebrow">✳ {t.eyebrow}</span><h1>{t.title}</h1><p>{t.lead}</p>
   <div className="rg-catalog-search"><span aria-hidden="true">⌕</span><input aria-label={t.search} placeholder={t.search} value={query} onChange={e=>setQuery(e.target.value)}/></div>
  </div></section>
  <section className="rg-catalog-content">
   <div className="rg-catalog-toolbar"><span aria-live="polite">{phase==="ready"?total.toLocaleString(locales[lang])+" "+(total===1?t.count:t.counts):""}</span></div>
   {phase==="error"?<div className="rg-catalog-feedback" role="alert"><p>{t.error}</p><button onClick={()=>{setPhase("loading");setAttempt(x=>x+1);}}>{t.retry} ↻</button></div>
   :phase==="loading"&&items.length===0?<div className="rg-catalog-loading" role="status">•••</div>
   :items.length===0?<div className="rg-catalog-feedback" role="status">{t.empty}</div>
   :<div className="rg-catalog-grid">{items.map(item=>{const l=localizeOffer(item,lang);return <article className="rg-product-card" key={item.id}>
    {item.image_url&&<div className="rg-product-image"><img src={item.image_url} alt="" loading="lazy" referrerPolicy="no-referrer"/></div>}
    <div className="rg-product-content"><div className="rg-product-category">{item.provider||"Robô Global"} <span>· {item.market}</span></div><h2>{l.title}</h2>
     {price(item)&&<p className="rg-product-price">{t.from} <strong>{price(item)}</strong></p>}
     {item.description&&<p className="rg-product-desc">{item.description}</p>}
     <p className="rg-product-trust">✓ {t.secure}</p><a className="rg-product-action" href={API_URL+item.url} target="_blank" rel="noopener noreferrer sponsored">{t.open}<span aria-hidden="true">↗</span></a></div>
   </article>;})}</div>}
   {phase==="ready"&&items.length<total&&<div className="rg-catalog-more"><button className="rg-retry" onClick={()=>{setPhase("loading");setPage(p=>p+1);}}>{t.more}</button></div>}
   <p className="rg-catalog-disclosure">{t.notice}</p><Link className="rg-back" to="/">← {t.back}</Link>
  </section>
 </div>;
}
