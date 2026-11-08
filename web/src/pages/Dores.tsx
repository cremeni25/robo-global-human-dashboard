import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { localizeEditorial, localizeOffer } from "../catalogCopy";
import { requestCatalog } from "../catalogRequest";
import { useLanguage } from "../contexts/LanguageContext";
import { API_URL } from "../config";
import LeadForm from "../components/LeadForm";

type Item = {id:string;slug:string;title:string;description?:string;translations?:Record<string,{title?:string;description?:string}>};
type State = "loading"|"ready"|"error";
type Solution = {id:string;title:string;description?:string;url:string};
const copy={
 pt:{title:"Explore seu caminho",intro:"Escolha um assunto para conhecer suas possibilidades.",sub:"Escolha um caminho",pain:"O que mais importa para você?",empty:"Ainda não há conteúdo validado para este caminho.",noMatch:"Ainda não há oferta elegível com correspondência verificada para esta necessidade.",error:"Não foi possível consultar este caminho agora.",retry:"Tentar novamente",back:"Voltar aos temas",next:"Ver necessidades",detail:"Necessidade identificada",select:"Selecione um tema na página anterior.",solutions:"Soluções relacionadas",open:"Conhecer solução",loading:"Consultando ofertas verificadas. Aguarde alguns instantes…"},
 en:{title:"Explore your path",intro:"Choose a topic and explore the possibilities.",sub:"Choose a path",pain:"What matters most to you?",empty:"Verified content is not available for this path yet.",noMatch:"No eligible offer has a verified match for this need yet.",error:"We couldn't load this path right now.",retry:"Try again",back:"Back to topics",next:"Explore needs",detail:"Need identified",select:"Select a topic on the previous page.",solutions:"Related solutions",open:"Explore solution",loading:"Checking verified offers. Please wait a moment…"},
 es:{title:"Explora tu camino",intro:"Elige un tema y descubre posibilidades.",sub:"Elige un camino",pain:"¿Qué es lo más importante para ti?",empty:"Todavía no hay contenido validado para este camino.",noMatch:"Aún no hay una oferta elegible con una correspondencia verificada para esta necesidad.",error:"No pudimos consultar este camino.",retry:"Intentar de nuevo",back:"Volver a los temas",next:"Ver necesidades",detail:"Necesidad identificada",select:"Selecciona un tema en la página anterior.",solutions:"Soluciones relacionadas",open:"Conocer solución",loading:"Consultando ofertas verificadas. Espera unos instantes…"}
};
const bases=[API_URL];
async function getItems(path:string,signal:AbortSignal):Promise<Item[]>{
 const data=await requestCatalog(bases,path,signal);
 return data.filter((x):x is Item=>!!x&&typeof x==="object"&&"id" in x&&typeof x.id==="string"&&"slug" in x&&typeof x.slug==="string"&&"title" in x&&typeof x.title==="string");
}
export default function Dores(){
 const [params]=useSearchParams();
 return <DoresPath key={[params.get("niche"),params.get("sub"),params.get("pain")].join(":")}/>;
}
function DoresPath(){
 const {lang}=useLanguage();const t=copy[lang];const [params,setParams]=useSearchParams();
 const niche=params.get("niche")||"";const sub=params.get("sub")||"";const pain=params.get("pain")||"";
 const [items,setItems]=useState<Item[]>([]);const [solutions,setSolutions]=useState<Solution[]>([]);const [solutionsState,setSolutionsState]=useState<State>("loading");const [state,setState]=useState<State>("loading");const [retry,setRetry]=useState(0);
 useEffect(()=>{
  const controller=new AbortController();
  if(!niche)return()=>controller.abort();
  const path=sub?"/public/subnichos/"+encodeURIComponent(sub)+"/dores":"/public/nichos/"+encodeURIComponent(niche)+"/subnichos";
  getItems(path,controller.signal).then(data=>{if(!controller.signal.aborted){setItems(data);setState("ready");}}).catch(()=>{if(!controller.signal.aborted)setState("error");});
  return()=>controller.abort();
 },[niche,sub,retry]);
 useEffect(()=>{
  const controller=new AbortController();
  if(!pain||!sub)return()=>controller.abort();
  requestCatalog(bases,"/public/dores/"+encodeURIComponent(pain)+"/solucoes",controller.signal)
   .then(data=>{if(controller.signal.aborted)return;
     const eligible=data.filter((raw):raw is Solution=>{const x=raw as Partial<Solution>|null;return !!x&&typeof x.id==="string"&&typeof x.title==="string"&&typeof x.url==="string"&&x.url==="/r/"+x.id&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(x.id);});
     setSolutions(eligible);setSolutionsState("ready");
   }).catch(()=>{if(!controller.signal.aborted)setSolutionsState("error");});
  return()=>controller.abort();
 },[pain,sub,retry]);
 return <div className="rg-interior"><section className="rg-interior-hero"><span className="rg-kicker">ROBÔ GLOBAL</span><h1>{sub?t.pain:t.title}</h1><p>{t.intro}</p></section><section className="rg-interior-body">
 {!niche?<p>{t.select}</p>:state==="loading"?<p role="status">…</p>:state==="error"?<div role="alert"><p>{t.error}</p><button className="rg-retry" onClick={()=>{setState("loading");setSolutionsState("loading");setRetry(v=>v+1);}}>{t.retry}</button></div>:(items.length===0||(pain&&!items.some(item=>item.id===pain)))?<p role="status">{t.empty}</p>:<div className="rg-topic-grid">{items.filter(item=>!pain||item.id===pain).map((item,i)=><article className="rg-topic" key={item.id}><span className="rg-path-number">0{i+1}</span><h2>{localizeEditorial(item,lang).title}</h2><p>{localizeEditorial(item,lang).description}</p>{!sub?<button className="rg-retry" onClick={()=>setParams({niche,sub:item.id})}>{t.next} ↗</button>:!pain?<button className="rg-retry" onClick={()=>setParams({niche,sub,pain:item.id})}>{t.detail} ↗</button>:null}</article>)}</div>}
 
 {pain&&state==="ready"&&items.some(item=>item.id===pain)&&<section aria-label={t.solutions}><h2>{t.solutions}</h2>{solutionsState==="loading"?<p role="status">{t.loading}</p>:solutionsState==="error"?<div role="alert"><p>{t.error}</p><button className="rg-retry" onClick={()=>{setState("loading");setSolutionsState("loading");setRetry(v=>v+1);}}>{t.retry}</button></div>:solutions.length===0?<><p role="status">{t.noMatch}</p><LeadForm dorId={pain}/></>:<div className="rg-topic-grid">{solutions.map(solution=><article className="rg-topic" key={solution.id}><h3>{localizeOffer(solution,lang).title}</h3><p>{solution.description||""}</p><a className="rg-retry" href={API_URL+solution.url+"?d="+encodeURIComponent(pain)} target="_blank" rel="noopener noreferrer sponsored">{t.open} ↗</a></article>)}</div>}{solutionsState==="ready"&&solutions.length>0&&<LeadForm dorId={pain} compact/>}</section>}
 <Link className="rg-back" to={pain?"/dores?niche="+encodeURIComponent(niche)+"&sub="+encodeURIComponent(sub):sub?"/dores?niche="+encodeURIComponent(niche):"/nichos"}>← {t.back}</Link></section></div>;
}
