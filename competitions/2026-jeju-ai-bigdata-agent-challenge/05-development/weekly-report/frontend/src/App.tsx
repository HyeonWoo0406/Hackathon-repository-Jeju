import {useEffect,useState} from 'react';
import {api,Status,Store,ReportData} from './api';
import Setup from './pages/Setup';
import Sales from './pages/Sales';
import Report from './pages/Report';
type Page='setup'|'sales'|'report';
export default function App(){
 const [status,setStatus]=useState<Status|null>(null),[store,setStore]=useState<Store|null>(null),[page,setPage]=useState<Page>('setup'),[report,setReport]=useState<ReportData|null>(null),[error,setError]=useState(''),[ready,setReady]=useState(false),[searchRequest,setSearchRequest]=useState(0),[revision,setRevision]=useState(0),[confirmDelete,setConfirmDelete]=useState(false),[deleting,setDeleting]=useState(false);
 useEffect(()=>{api<Status>('status').then(setStatus).catch(()=>{});api<Store|null>('store').then(s=>{setStore(s);setPage(s?'sales':'setup');setReady(true)}).catch(e=>setError(e.message))},[]);
 function navigate(next:Page){setError('');if(next==='sales'&&!store){setError('가게와 정류소를 저장한 뒤 매출을 입력해 주세요.');setPage('setup');return}setPage(next)}
 function searchStops(){navigate('setup');setSearchRequest(n=>n+1)}
 function reset(){setError('');setConfirmDelete(false);setStore(null);setReport(null);setRevision(n=>n+1);setPage('setup')}
 async function deleteData(){setDeleting(true);setError('');try{await api('my-data','DELETE');reset()}catch(e){setError((e as Error).message)}finally{setDeleting(false)}}
 return <><header><a href="/" className="brand"><span>週</span>제주 가게 <b>주간 장사 결산</b></a><small>{status?.online?'공공자료 연결됨':'저장된 자료 사용'} · {status?.llm?'로컬 AI':'기본 문장'}</small></header><main>
 {status?.demo&&<p className="hint no-print">웹 시연 · 가게 등록 후 가상 매출 파일을 직접 올려 주세요. 정기 수집된 공개 자료로 결산합니다. 선택 후 자료 준비 상태를 확인해 주세요. 변경 내용은 브라우저별로 분리해 데모 서버에 저장합니다. 실제 매출·개인정보는 입력하지 마세요.</p>}
 <div className="topline no-print"><span>지난 기록에서 찾는 우리 가게의 흐름</span><span>자료 기준일 {status?.latest_hub_date??'확인 중'}</span></div>
 <nav className="steps no-print" aria-label="작업 단계">{([['setup','01 가게 등록'],['sales','02 매출 입력'],['report','03 결산표']] as [Page,string][]).map(([key,text])=><button key={key} type="button" className={page===key?'active':''} aria-current={page===key?'step':undefined} disabled={!ready} onClick={()=>navigate(key)}>{text}</button>)}</nav>
 {ready&&<div className="page-navigation no-print">{(page!=='setup'||store)&&<button type="button" onClick={()=>navigate(page==='report'?'sales':page==='sales'?'setup':'sales')}>← {page==='sales'?'가게 등록': '매출 입력'}으로 돌아가기</button>}{page!=='setup'&&<button type="button" onClick={searchStops}>정류소 검색·변경</button>}</div>}
 {ready&&<div className="no-print data-controls"><button type="button" onClick={()=>setConfirmDelete(true)}>내 자료 지우기</button>{confirmDelete&&<section className="confirm" role="alertdialog" aria-label="내 자료 삭제 확인"><p>가게 정보·매출·저장한 결산과 입력 중인 내용을 모두 지우고 처음부터 시작할까요? 공공자료는 남습니다.</p><button disabled={deleting} onClick={deleteData}>{deleting?'지우는 중…':'모두 지우고 처음부터 시작'}</button><button disabled={deleting} onClick={()=>setConfirmDelete(false)}>취소</button></section>}</div>}
 {error&&<p className="error" role="alert">{error}</p>}
 {!ready?<p>가게 자료를 확인하고 있습니다.</p>:<>
 <div hidden={page!=='setup'}><Setup key={revision} store={store} searchRequest={searchRequest} onSave={s=>{setStore(s);setReport(null);setPage('sales')}}/></div>
 {store&&<div hidden={page!=='sales'}><Sales key={revision} status={status} store={store} onDirty={()=>setReport(null)} onReport={r=>{setReport(r);setPage('report')}}/></div>}
 {page==='report'&&(report?<Report data={report} onDelete={reset}/>:<section className="card"><h1>아직 만든 결산표가 없어요.</h1><p>{store?'매출 입력 화면에서 대상 주를 고르고 ‘결산 보기’를 눌러 주세요.':'가게와 정류소를 먼저 등록해 주세요.'}</p><button className="primary" onClick={()=>navigate(store?'sales':'setup')}>{store?'매출 입력으로 이동':'가게 등록으로 이동'}</button></section>)}
 </>}
 <footer>{status?.demo?'시연 자료는 브라우저별로 분리해 데모 서버에 저장됩니다.':'매출은 이 PC에만 저장됩니다.'} 버스·와이파이는 동네 흐름의 일부이며, 매출 변화의 원인을 확정하지 않습니다.</footer></main></>;
}
