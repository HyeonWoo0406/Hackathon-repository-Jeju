// Development-only visual audit. This page never reads or writes a real store.
import {useState} from 'react';
import {createRoot} from 'react-dom/client';
import Sales from '../src/pages/Sales';
import Report from '../src/pages/Report';
import ReportLoading from '../src/pages/ReportLoading';
import Setup from '../src/pages/Setup';
import WorkspaceLayout from '../src/WorkspaceLayout';
import {addDays,ReportData,Status,Store} from '../src/api';
import '../src/style.css';
import '../src/typography.css';
import '../src/report-comparison.css';
import '../src/surface-theme.css';
import '../src/print.css';

const store:Store={name:'검수용 애월 작은 카페',emd:'애월읍',industry:'카페',stops:[{id:'0003291',name:'애월환승정류장(애월리)'}]};
const status:Status={online:false,hub_key:false,data_key:false,llm:false,latest_hub_date:'2026-11-08'};
const report:ReportData={
 week_start:'2026-11-02',week_end:'2026-11-08',base_start:'2026-10-05',base_end:'2026-11-01',
 name:store.name,emd:store.emd,industry:store.industry,verdict_text:'동네와 함께 줄었어요',verdict:'area',neighborhood:-.081,example:true,
 limits:'버스·와이파이는 동네 흐름의 일부이며, 매출 변화의 원인을 확정하지 않습니다.',
 indicators:[
  {key:'store',label:'우리 가게 매출',avg_target:175200,avg_base:200000,change:-.124,valid:true,note:null},
  {key:'stop_bus',label:'선택 정류소 승차',avg_target:919,avg_base:1000,change:-.081,valid:true,note:'선택한 정류소의 승차량'},
  {key:'wifi',label:'동네 와이파이 이용',avg_target:1838,avg_base:2000,change:-.081,valid:true,note:'고유 방문객 수가 아닙니다.'},
  {key:'island_bus',label:'제주 전체 버스 승차',avg_target:98000,avg_base:100000,change:-.02,valid:true,note:null},
 ],
 days:['월','화','수','목','금','토','일'].map((dow,i)=>({date:addDays('2026-11-02',i),dow,store:[-.05,-.08,.04,-.12,-.15,-.24,-.1][i],area:[-.03,-.05,.02,-.06,-.12,-.09,-.08][i],flag:i===5,rain_mm:i===5?12:0,holiday:null,excluded:false})),
 excluded:[],sources:[{name:'제주데이터허브 · 검수용 가상 버스·와이파이',range:'2026-10-05 ~ 2026-11-08',fetched_at:'가상 데이터: 실제 수집 이력 없음'}],
 note:{text:'지난주 가게 매출과 동네 지표가 모두 줄었습니다. 토요일은 가게 매출과 동네 지표의 차이를 확인할 날입니다.',by:'template'},sources_status:[],weather:{rain_days:1,rain_days_base_per_week:1,wind_days:0,wind_days_base_per_week:0,holiday_days:0,holiday_days_base_per_week:0},
};
let ready=false;
// All requests from imported UI components end here, including destructive actions.
window.fetch=async(input,init)=>{
 const url=new URL(String(input),window.location.origin);
 let body:unknown;
 if(url.pathname==='/api/emds')body=['애월읍','연동','노형동'];
 else if(url.pathname==='/api/stops')body=store.stops;
 else if(url.pathname==='/api/store')body=store;
 else if(url.pathname==='/api/sales')body=init?.method==='PUT'?{saved:true}:[];
 else if(url.pathname==='/api/data-availability')body={ready,detail:ready?'검수용 공개 자료 준비 완료':'검수용 공개 자료가 부족합니다.',missing_sources:ready?[]:[{source:'정류소 버스',dates:['2026-11-02','2026-11-03']},{source:'와이파이',dates:['2026-11-04']}]};
 else if(url.pathname==='/api/data-requests')body={detail:'검수 화면에서는 실제 자료를 요청하지 않습니다.'};
 else if(url.pathname==='/api/ask')body={answer:'검수용 답변입니다. 토요일 가게 매출은 기준 4주 같은 요일 대비 24.0%, 동네 지표는 9.0% 줄었습니다. 실제 분석 결과가 아닙니다.',by:'template'};
 else if(url.pathname==='/api/my-data')body={deleted:true};
 else return new Response(JSON.stringify({detail:'검수 화면에서는 지원하지 않는 요청입니다.'}),{status:400,headers:{'Content-Type':'application/json'}});
 return new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});
};
function Audit(){
 const [view,setView]=useState('sales-empty'),[loading,setLoading]=useState(false);
 ready=view==='sales-ready';
 const longReport:ReportData={...report,name:'애월 해안도로 로스터리 카페와 베이커리 — 긴 가게 이름 검수',verdict_text:'가게 매출의 감소 폭이 동네 이용 지표보다 커요'};
 const missing:ReportData={...report,verdict:'hold',verdict_text:'비교를 보류했어요',neighborhood:null,limits:'공개 자료와 비교 가능한 날짜가 부족합니다.',indicators:report.indicators.map(i=>i.key==='store'?i:{...i,avg_target:null,avg_base:null,change:null,valid:false,note:'자료 부족'}),days:report.days.map(d=>({...d,area:null,excluded:true})),note:{text:'비교할 공개 자료가 부족해 판정을 보류했습니다.',by:'template'}};
 return <><div className="audit-controls no-print"><label>프론트엔드 검수 · 실제 자료 사용 안 함<select value={view} onChange={e=>setView(e.target.value)}><option value="setup">가게 설정</option><option value="sales-empty">매출 입력 · 최초 / 자료 부족</option><option value="sales-ready">매출 입력 · 공개 자료 준비됨</option><option value="report">결산표 · 정상</option><option value="report-long">결산표 · 긴 가게 이름과 문구</option><option value="report-missing">결산표 · 자료 부족</option></select></label><button onClick={()=>setLoading(true)}>로딩 화면 보기</button></div>
 <WorkspaceLayout page={view==='setup'?'setup':view.startsWith('sales')?'sales':'report'} store={store} status={status} onNavigate={page=>setView(page==='sales'?'sales-empty':page)}>
 {view==='setup'?<Setup store={store} onSave={()=>setView('sales-empty')}/>:view.startsWith('sales')?<Sales key={view} store={store} status={status} onReport={()=>setView('report')} onDirty={()=>{}}/>:<Report key={view} data={view==='report-missing'?missing:view==='report-long'?longReport:report} onDelete={()=>setView('sales-empty')}/>}
 </WorkspaceLayout>
 {loading&&<ReportLoading onCancel={()=>setLoading(false)} cancelling={false}/>}</>;
}
const css=document.createElement('style');css.textContent='.audit-controls{display:flex;flex-wrap:wrap;gap:12px;align-items:end;background:#fff;padding:12px 20px;border-bottom:2px dashed #777}.audit-controls label{margin:0;flex:1;min-width:0;font-size:13px}.audit-controls select{max-width:420px}.audit-controls button{font-size:13px}';document.head.append(css);
createRoot(document.getElementById('audit-root')!).render(<Audit/>);
