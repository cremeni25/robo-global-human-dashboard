/** Read-only catalogue requests with bounded waiting and the existing V2 fallback. */
export async function requestCatalog(
  bases:string[], path:string, signal:AbortSignal, timeoutMs=15000
):Promise<unknown[]> {
  for(const base of [...new Set(bases)]) {
    if(signal.aborted)throw new Error("aborted");
    const controller=new AbortController();
    let timer:ReturnType<typeof setTimeout>|undefined;
    let cancel:()=>void=()=>{};
    try {
      const interrupted=new Promise<never>((_,reject)=>{
        cancel=()=>{controller.abort();reject(new Error("aborted"));};
        signal.addEventListener("abort",cancel,{once:true});
        timer=setTimeout(()=>{controller.abort();reject(new Error("catalogue_timeout"));},timeoutMs);
      });
      const load=async()=>{
        const response=await fetch(base.replace(/\/$/,"")+path,{
          signal:controller.signal,headers:{Accept:"application/json"}
        });
        if(!response.ok)throw new Error("catalogue_unavailable");
        const payload:unknown=await response.json();
        const data=Array.isArray(payload)?payload:
          payload&&typeof payload==="object"&&"data" in payload?payload.data:undefined;
        if(!Array.isArray(data))throw new Error("invalid_catalogue");
        return data;
      };
      return await Promise.race([load(),interrupted]);
    } catch {
      if(signal.aborted)throw new Error("aborted");
    } finally {
      clearTimeout(timer);
      signal.removeEventListener("abort",cancel);
    }
  }
  throw new Error("catalogue_unavailable");
}
