import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { localizeEditorial } from "../catalogCopy";
import { useLanguage } from "../contexts/LanguageContext";
import { API_URL } from "../config";
type Niche={id:string|number;slug:string;title:string;description?:string;translations?:Record<string,{title?:string;description?:string}>};
const words={
 pt:{tag:"EXPLORE NO SEU RITMO",title:"Por onde você quer começar?",intro:"Cada pessoa tem seu próprio momento. Escolha um assunto e descubra caminhos que fazem sentido para você.",loading:"Buscando caminhos disponíveis…",empty:"Estamos preparando novas possibilidades para você.",error:"Não conseguimos consultar os temas agora. Volte em instantes.",action:"Conhecer este caminho",back:"Voltar ao início",retry:"Tentar novamente",preparing:"Novos temas estão a caminho."},
 en:{tag:"EXPLORE AT YOUR OWN PACE",title:"Where would you like to begin?",intro:"Everyone has a different starting point. Choose what matters to you and explore a path forward.",loading:"Finding available topics…",empty:"We're preparing more possibilities for you.",error:"We couldn't load the topics right now. Please try again soon.",action:"Explore this topic",back:"Back to home",retry:"Try again",preparing:"More topics are on their way."},
 es:{tag:"EXPLORA A TU RITMO",title:"¿Por dónde te gustaría empezar?",intro:"Cada persona tiene su propio momento. Elige lo que te importa y descubre nuevas posibilidades.",loading:"Buscando temas disponibles…",empty:"Estamos preparando nuevas posibilidades para ti.",error:"No pudimos consultar los temas ahora. Vuelve a intentarlo pronto.",action:"Explorar este tema",back:"Volver al inicio",retry:"Intentar de nuevo",preparing:"Pronto habrá más temas."}
};
function normalize(raw:unknown):Niche[]{
 const data=Array.isArray(raw)?raw:(raw&&typeof raw==="object"&&"data" in raw?(raw as {data:unknown}).data:[]);
 if(!Array.isArray(data))return [];
 return data.filter((x):x is Niche=>!!x&&typeof x==="object"&&typeof x.slug==="string"&&typeof x.title==="string"&&(typeof x.id==="string"||typeof x.id==="number"));
}
export default function Nichos(){
 const {lang}=useLanguage();const t=words[lang];const [items,setItems]=useState<Niche[]>([]);const [state,setState]=useState<"loading"|"ready"|"error">("loading");const [attempt,setAttempt]=useState(0);
 useEffect(()=>{
  const controller=new AbortController();
  const endpoints=[API_URL+"/public/nichos"];
  const load=async()=>{
   for(const endpoint of [...new Set(endpoints)]){
    try{
     const response=await fetch(endpoint,{signal:controller.signal,headers:{"Accept":"application/json"}});
     if(!response.ok)continue;
     const payload=await response.json();
     if(!Array.isArray(payload)&&(!payload||!Array.isArray(payload.data)))continue;
     if(controller.signal.aborted)return;
     setItems(normalize(payload));setState("ready");return;
    }catch{if(controller.signal.aborted)return;}
   }
   if(!controller.signal.aborted)setState("error");
  };
  void load();
  return ()=>controller.abort();
 },[attempt]);
 return <div className="rg-interior"><section className="rg-interior-hero"><span className="rg-kicker">{t.tag}</span><h1>{t.title}</h1><p>{t.intro}</p></section>
 <section className="rg-interior-body">{state==="loading"?<p role="status">{t.loading}</p>:state==="error"?<div role="alert"><p>{t.error}</p><button className="rg-retry" onClick={()=>{setState("loading");setAttempt(a=>a+1);}}>{t.retry} ↻</button></div>:items.length===0?<p role="status">{t.empty}</p>:<div className="rg-topic-grid">{items.map((item,i)=>{
  const localized=localizeEditorial(item,lang);
  return <article className="rg-topic" key={item.id}><span className="rg-path-number">0{i+1}</span><h2>{localized?.title||t.preparing}</h2><p>{localized?.description||""}</p>{localized?.title&&<Link to={"/dores?niche="+encodeURIComponent(item.slug)+"&index=0"}>{t.action} ↗</Link>}</article>;
 })}</div>}
 <Link className="rg-back" to="/">← {t.back}</Link></section></div>;
}
