export async function api<T=any>(path:string,body?:unknown,method?:string):Promise<T>{
 const response=await fetch('/api'+path,{method:method??(body?'POST':'GET'),credentials:'same-origin',headers:body instanceof FormData?{}:body?{'Content-Type':'application/json'}:{},body:body instanceof FormData?body:body?JSON.stringify(body):undefined});
 const data=await response.json();if(!response.ok)throw new Error(data.error||'Request failed');return data;
}
