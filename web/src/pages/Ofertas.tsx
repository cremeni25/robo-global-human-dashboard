import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { localizeOffer } from "../catalogCopy";
import { useLanguage } from "../contexts/LanguageContext";
import { API_URL } from "../config";

type Offer = { id:string; title:string; description?:string; image_url?:string; market:string; language:string; url:string; provider?:string; need_category?:string; need_problem?:string; solution_angle?:string };
type Phase = "loading" | "ready" | "error";
const copy = {
 pt:{eyebrow:"CATÁLOGO ROBÔ GLOBAL",title:"Possibilidades reais. Escolhas suas.",lead:"Explore soluções de parceiros com autorização comercial verificada. Você decide se deseja visitar o fornecedor.",search:"Buscar uma solução",all:"Todas",services:"Serviços",count:"solução disponível",counts:"soluções disponíveis",open:"Conhecer no site do parceiro",notice:"Alguns links são de afiliados. Podemos receber uma comissão por compras qualificadas, sem cobrança adicional do ROBÔ GLOBAL.",empty:"Nenhuma solução corresponde à sua busca.",error:"Não foi possível carregar o catálogo neste momento.",retry:"Tentar novamente",back:"Voltar ao início",illustrative:"Imagem ilustrativa",type:"Serviços para empresas",secure:"Fornecedor externo · Link rastreável"},
 en:{eyebrow:"ROBÔ GLOBAL CATALOGUE",title:"Real possibilities. Your choice.",lead:"Explore solutions from commercially verified partners. You decide whether to visit the provider.",search:"Search solutions",all:"All",services:"Services",count:"solution available",counts:"solutions available",open:"Visit partner website",notice:"Some links are affiliate links. We may earn a commission on qualifying purchases at no additional ROBÔ GLOBAL charge.",empty:"No solutions match your search.",error:"We couldn't load the catalogue right now.",retry:"Try again",back:"Back to home",illustrative:"Illustrative photo",type:"Business services",secure:"External partner · Tracked link"},
 es:{eyebrow:"CATÁLOGO ROBÔ GLOBAL",title:"Posibilidades reales. Tú decides.",lead:"Explora soluciones de socios con autorización comercial verificada. Tú decides si visitar al proveedor.",search:"Buscar soluciones",all:"Todas",services:"Servicios",count:"solución disponible",counts:"soluciones disponibles",open:"Visitar al proveedor",notice:"Algunos enlaces son de afiliación. Podemos recibir una comisión por compras válidas, sin cargo adicional de ROBÔ GLOBAL.",empty:"Ninguna solución coincide con tu búsqueda.",error:"No pudimos cargar el catálogo ahora.",retry:"Intentar de nuevo",back:"Volver al inicio",illustrative:"Imagen ilustrativa",type:"Servicios empresariales",secure:"Proveedor externo · Enlace rastreable"}
};
const localizedTitle = (offer:Offer,lang:"pt"|"en"|"es") => localizeOffer(offer,lang).title;

export default function Ofertas(){
 const {lang}=useLanguage();const t=copy[lang];const [params]=useSearchParams();
 const [items,setItems]=useState<Offer[]>([]),[phase,setPhase]=useState<Phase>("loading");
 const [attempt,setAttempt]=useState(0),[query,setQuery]=useState(()=>params.get("q")||""),[category,setCategory]=useState("all");
 useEffect(()=>{
  const controller=new AbortController();
  (async()=>{
   try{
    const response=await fetch(API_URL+"/public/ofertas",{signal:controller.signal,headers:{Accept:"application/json"}});
    if(!response.ok)throw new Error("catalogue_unavailable");
    const body:unknown=await response.json();
    if(!body||typeof body!=="object"||!("data" in body)||!Array.isArray(body.data))throw new Error("invalid_catalogue");
    const valid=(body.data as unknown[]).filter((v):v is Offer=>{
     if(!v||typeof v!=="object")return false;
     const x=v as Partial<Offer>;
     return typeof x.id==="string"&&typeof x.title==="string"&&typeof x.url==="string"&&x.url.startsWith("/r/");
    });
    if(!controller.signal.aborted){setItems(valid);setPhase("ready");}
   }catch{if(!controller.signal.aborted)setPhase("error");}
  })();
  return()=>controller.abort();
 },[attempt]);
 const shown=useMemo(()=>items.filter(item=>{
  const term=query.toLocaleLowerCase().trim();
  const localized=localizeOffer(item,lang);
  return (category==="all"||category==="services")&&(!term||[item.title,localized.title,item.market,item.need_category,item.need_problem,item.solution_angle,localized.need_problem,localized.solution_angle].join(" ").toLocaleLowerCase().includes(term));
 }),[items,query,category,lang]);
 return <div className="rg-catalog">
  <section className="rg-catalog-hero"><div className="rg-catalog-hero-inner">
   <span className="rg-catalog-eyebrow">✳ {t.eyebrow}</span><h1>{t.title}</h1><p>{t.lead}</p>
   <div className="rg-catalog-search"><span aria-hidden="true">⌕</span><input aria-label={t.search} placeholder={t.search} value={query} onChange={e=>setQuery(e.target.value)}/></div>
  </div></section>
  <section className="rg-catalog-content">
   <div className="rg-catalog-toolbar"><div className="rg-catalog-filters"><button type="button" className={category==="all"?"selected":""} onClick={()=>setCategory("all")}>{t.all}</button><button type="button" className={category==="services"?"selected":""} onClick={()=>setCategory("services")}>{t.services}</button></div><span aria-live="polite">{phase==="ready"?shown.length+" "+(shown.length===1?t.count:t.counts):""}</span></div>
   {phase==="loading"?<div className="rg-catalog-loading" role="status">•••</div>:phase==="error"?<div className="rg-catalog-feedback" role="alert"><p>{t.error}</p><button onClick={()=>{setPhase("loading");setAttempt(x=>x+1);}}>{t.retry} ↻</button></div>:shown.length===0?<div className="rg-catalog-feedback" role="status">{t.empty}</div>:<div className="rg-catalog-grid">{shown.map(item=><article className="rg-product-card" key={item.id}>
    
    <div className="rg-product-content"><div className="rg-product-category">{t.type} <span>· {item.market}</span></div><h2>{localizedTitle(item,lang)}</h2>{item.description&&<p>{item.description}</p>}{item.need_problem&&<p>{localizeOffer(item,lang).need_problem}</p>}{item.solution_angle&&<p>{localizeOffer(item,lang).solution_angle}</p>}{item.provider&&<p className="rg-product-provider">{item.provider}</p>}<p className="rg-product-trust">✓ {t.secure}</p><a className="rg-product-action" href={API_URL+item.url} target="_blank" rel="noopener noreferrer sponsored">{t.open}<span aria-hidden="true">↗</span></a></div>
   </article>)}</div>}
   <p className="rg-catalog-disclosure">{t.notice}</p><Link className="rg-back" to="/">← {t.back}</Link>
  </section>
 </div>;
}
