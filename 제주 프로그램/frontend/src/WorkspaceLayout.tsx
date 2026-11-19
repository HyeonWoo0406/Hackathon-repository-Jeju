import {ReactNode} from 'react';
import {Status,Store} from './api';

export type Page='setup'|'sales'|'report';
function MenuIcon({kind}:{kind:Page}){
 return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
 {kind==='setup'?<><path d="M3 10h18l-2-6H5l-2 6Z"/><path d="M5 10v10h14V10M9 20v-6h6v6"/></>:kind==='sales'?<><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h3M8 16h3M15 12h1M15 16h1"/></>:<><path d="M4 4v16h16M8 15v-4M13 15V7M18 15V9"/></>}
 </svg>;
}
const items:[Page,string,string][]=[['sales','매출 입력','02 매출 입력'],['report','주간 결산','03 결산표'],['setup','가게 설정','01 가게 등록']];
export default function WorkspaceLayout({page,store,status,ready=true,onNavigate,onDelete,children}:{page:Page;store:Store|null;status:Status|null;ready?:boolean;onNavigate:(page:Page)=>void;onDelete?:()=>void;children:ReactNode}){
 return <>
 <header className="app-header"><svg className="header-pattern" viewBox="0 0 720 72" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path d="M160 72C268 12 328 16 418 44S598 90 720 18V72Z" fill="#bfd2e5"/><path d="M280 72C376 30 436 18 526 36S640 56 720 34V72Z" fill="#d4e2ef"/><path d="M140 64C262 4 332 8 422 36S602 82 720 10" fill="none" stroke="#a9c1d9" strokeWidth="1"/></svg><a href="/" className="brand"><span className="brand-mark">J</span><span>제주 가게 <b>주간 장사 결산</b></span></a><div className="header-meta"><span className="connection-dot"/><span>{status?.demo?'시연 환경':'내 가게 워크스페이스'}</span></div></header>
 <div className="app-shell">
  <aside className="workspace-sidebar no-print">
   <div className="store-identity"><span className="sidebar-caption">내 가게</span><strong>{store?.name|| (store?store.emd+' '+store.industry:'가게를 등록해 주세요')}</strong><small>{store?store.emd+' · '+store.industry:'처음 한 번 설정하면 됩니다'}</small></div>
   <nav className="workspace-nav" aria-label="작업 단계">{items.map(([key,label,name])=><button type="button" key={key} aria-label={name} aria-current={page===key?'page':undefined} disabled={!ready} className={page===key?'active':''} onClick={()=>onNavigate(key)}><MenuIcon kind={key}/><span>{label}</span></button>)}</nav>
   <div className="sidebar-bottom"><p>우리 가게의 변화,<br/>동네 흐름과 함께.</p></div>
  </aside>
  <main className={'workspace-main'+(page==='report'?' workspace-main-report':'')}><div className="workspace-context no-print"><span>{page==='setup'?'가게 설정':page==='sales'?'매출 관리':'분석 리포트'}</span><span>{status?.latest_hub_date?'공개 자료 기준 '+status.latest_hub_date:'공개 자료 기준일 미확인'}</span></div>{children}{onDelete&&<div className="workspace-data-control no-print"><button className="manage-data" type="button" disabled={!ready} onClick={onDelete}>내 자료 지우기</button></div>}</main>
 </div>
 </>;
}
