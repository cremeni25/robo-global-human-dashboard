type Language = "pt" | "en" | "es";
type Editorial = {id:string|number; title:string; description?:string; translations?:Record<string,{title?:string;description?:string}>};
type Copy = {title:string;description:string};

// Editorial translations are keyed by verified source IDs. They never establish
// a commercial relationship or alter the taxonomy in the database.
const needDescription = {
  en:"An informational catalogue topic, without promises of results or a commercial recommendation.",
  es:"Un tema informativo del catálogo, sin promesas de resultados ni recomendación comercial."
};
const subDescription = {
  en:"Topics from the existing editorial catalogue. No commercial offer is linked.",
  es:"Temas del catálogo editorial existente. No hay una oferta comercial vinculada."
};
const translations:Record<string,Record<"en"|"es",Copy>> = {
  "eb912761-7cec-4f25-b73d-ede2775b05f0":{
    en:{title:"Business services",description:"Partner services for specific business needs."},
    es:{title:"Servicios empresariales",description:"Servicios de socios para necesidades específicas de empresas."}
  },
  "025a4d94-1a78-4095-a2e0-5685a2d3fbc9":{
    en:{title:"Advertising a business for sale",description:"Channels for advertising a business for sale, without promises of a sale or financial returns."},
    es:{title:"Anunciar una empresa en venta",description:"Canales para anunciar una empresa en venta, sin promesas de venta ni de retorno económico."}
  },
  "7a814649-fcd3-4103-9f50-1e7c7afcb405":{
    en:{title:"Advertise a business for sale",description:"Find a channel to advertise a business for sale. The service is an advertising plan; a sale is not guaranteed."},
    es:{title:"Publicar un anuncio de una empresa en venta",description:"Encontrar un canal para anunciar una empresa en venta. El servicio es un plan de anuncios; no se garantiza la venta."}
  },
  "a0afa6c9-0514-4b87-aac4-aaa8c73b4ca0":{
    en:{title:"Weight management",description:"Information about weight management goals and challenges, without promises of results."},
    es:{title:"Control del peso",description:"Información sobre objetivos y dificultades para controlar el peso, sin promesas de resultados."}
  },
  "2d76cde0-b06a-4f60-b96f-235b0d51036f":{
    en:{title:"Extra income",description:"Information about financial challenges and ways to earn additional income, without promises of earnings."},
    es:{title:"Ingresos adicionales",description:"Información sobre dificultades económicas y opciones para generar ingresos, sin promesas de ganancias."}
  },
  ...Object.fromEntries(["45a0b438-4e91-40de-ab84-61414e13decc","6a80a1fd-7e9c-4bb4-aed2-59d7a15e98cc"].map(id=>[id,{
    en:{title:"Identified needs",description:subDescription.en},
    es:{title:"Necesidades identificadas",description:subDescription.es}
  }])),
  ...Object.fromEntries([
    ["d58e83e6-f353-4a7a-baf1-8baed27cc208","Money concerns","Dificultades económicas"],
    ["fa3303f8-cc26-43ac-bd74-6aa6f310d02a","Earning online","Generar ingresos por internet"],
    ["05ad9116-a456-4f3d-aa3b-566ef3780991","Abdominal fat","Grasa abdominal"],
    ["55b55d6a-6d84-40b2-90dc-d6ca52d3d1ea","Losing weight quickly","Bajar de peso rápidamente"]
  ].map(([id,en,es])=>[id,{
    en:{title:en,description:needDescription.en},es:{title:es,description:needDescription.es}
  }]))
};

export function localizeEditorial(item:Editorial,lang:Language):Copy {
  if(lang==="pt")return {title:item.title,description:item.description||""};
  const copy=item.translations?.[lang]||translations[String(item.id)]?.[lang];
  return {title:copy?.title||item.title,description:copy?.description||item.description||""};
}

export function localizeOffer<T extends {id:string;title:string;need_problem?:string;solution_angle?:string}>(item:T,lang:Language):T {
  if(item.id!=="659339cf-ab62-444b-9bcc-676e7ba680d1"||lang==="en")return item;
  const copy={
    pt:{title:"World Businesses for Sale — planos para anunciar empresas à venda",need_problem:"Encontrar um canal para anunciar uma empresa à venda",solution_angle:"Conheça os planos de anúncio de empresas à venda"},
    es:{title:"World Businesses for Sale — planes para anunciar empresas en venta",need_problem:"Encontrar un canal para anunciar una empresa en venta",solution_angle:"Conoce los planes de anuncios de empresas en venta"}
  }[lang];
  return {...item,...copy};
}
