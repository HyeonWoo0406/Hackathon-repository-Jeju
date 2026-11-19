export type Stop={id:string;name:string};
export type Store={name:string;emd:string;industry:string;stops:Stop[]};
export type Sale={date:string;amount:number|null;closed:boolean};
export type Status={demo?:boolean;online:boolean;hub_key:boolean;data_key:boolean;llm:boolean;latest_hub_date:string|null};
export type Day={date:string;dow:string;store:number|null;area:number|null;flag:boolean;rain_mm:number|null;holiday:string|null;excluded:boolean};
export type ReportData={week_start:string;week_end:string;base_start:string;base_end:string;name:string;emd:string;industry:string;verdict_text:string;verdict:string;neighborhood:number|null;example:boolean;limits:string;indicators:{key:string;label:string;avg_target:number|null;avg_base:number|null;change:number|null;valid:boolean;note:string|null}[];days:Day[];excluded:{date:string;reason:string}[];sources:{name:string;range:string;fetched_at:string}[];note:{text:string;by:string};sources_status:string[];weather:Record<string,number|null>};
export async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
 const isFile=body instanceof FormData;
 const r=await fetch('/api/'+path,{method,headers:{'X-Weekly-Client':'1',...(!isFile&&body!==undefined?{'Content-Type':'application/json'}:{})},body:body===undefined?undefined:isFile?body:JSON.stringify(body)});
 const data=await r.json();
 if(!r.ok){
  const fields:Record<string,string>={name:'가게 이름',emd:'읍면동',industry:'업종',stops:'정류소',amount:'매출',date:'날짜',id:'내부 번호'};
  const detail=typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((issue:{loc?:Array<string|number>;msg?:string;type?:string})=>{
   const field=(issue.loc??[]).filter(x=>x!=='body').map(x=>typeof x==='number'?`${x+1}번째`:fields[x]??x).join(' / ');
   const message=issue.msg?.replace(/^Value error, /,'');
   return message&&/[가-힣]/.test(message)?message:`${field||'입력 항목'}: ${issue.type==='extra_forbidden'?'허용되지 않은 항목이 포함됐습니다. 새로고침 후 다시 시도해 주세요.':'입력값을 확인해 주세요.'}`;
  }).join(' '):'입력 내용을 확인하세요.';
  throw new Error(detail);
 }
 return data;
}
export const addDays=(day:string,n:number)=>{const d=new Date(day+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10)};
export async function requestReport(weekStart:string,cancelled:()=>boolean=()=>false):Promise<ReportData|null>{
 const job=await api<{job_id:string}>('report-jobs','POST',{week_start:weekStart});
 for(;;){
  if(cancelled()){await api('report-jobs/'+job.job_id,'DELETE');return null}
  const status=await api<{state:string;result?:ReportData;detail?:string}>('report-jobs/'+job.job_id);
  if(cancelled())continue;
  if(status.state==='cancelled')return null;
  if(status.state==='complete'&&status.result)return status.result;
  if(status.state==='failed')throw new Error(status.detail??'결산을 완료하지 못했습니다.');
  await new Promise(resolve=>setTimeout(resolve,1500));
 }
}
export const pct=(v:number|null)=>v==null?'비교 불가':`${v>0?'+':''}${(v*100).toFixed(1)}%`;
export const num=(v:number|null)=>v==null?'자료 없음':v.toLocaleString('ko-KR',{maximumFractionDigits:1});
