import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';

export default function ReportLoading({onCancel,cancelling}:{onCancel:()=>void;cancelling:boolean}){
 const dialog=useRef<HTMLDialogElement>(null);
 const [elapsed,setElapsed]=useState(0);
 useEffect(()=>{const started=Date.now();const timer=setInterval(()=>setElapsed(Math.floor((Date.now()-started)/1000)),1000);return()=>clearInterval(timer)},[]);
 useEffect(()=>{
  const element=dialog.current;
  if(element){if(typeof element.showModal==='function')element.showModal();else element.setAttribute('open','')}
  return()=>{if(element?.open&&typeof element.close==='function')element.close()};
 },[]);
 return createPortal(<dialog ref={dialog} className="report-loading no-print" aria-labelledby="report-loading-title" aria-describedby="report-loading-description" onCancel={event=>{event.preventDefault();onCancel()}}>
  <div className="loading-spinner" aria-hidden="true"/>
  <h2 id="report-loading-title">결산표를 만들고 있어요</h2>
  <p className="loading-elapsed" role="timer" aria-label="결산 진행 시간">진행 시간 <strong>{String(Math.floor(elapsed/60)).padStart(2,'0')}:{String(elapsed%60).padStart(2,'0')}</strong></p>
  <div id="report-loading-description" role="status" aria-live="polite">
   <p>{elapsed<60?<>저장된 자료로 계산하고 있어요. 보통 수 초 안에 완료됩니다.</>:<>자료를 계속 확인하고 있습니다.<br/>진행 중이며 완료되면 자동으로 이동합니다.</>}</p>
   <p>매출과 저장된 공개 자료를 비교하고 설명을 준비합니다.<br/>완료되면 자동으로 결산표로 이동합니다.</p>
   <small>자료가 저장되어 있으면 더 빨리 끝나요.<br/>60초가 지나도 자동으로 중단하지 않습니다.<br/>잠시만 기다려 주세요. 새로고침하면 진행 중인 화면을 잃을 수 있습니다.</small>
  </div>
  <button type="button" className="loading-cancel" disabled={cancelling} onClick={onCancel}>{cancelling?'취소하고 있어요…':'결산 취소'}</button>
  <p className="hint">취소해도 입력한 매출과 이미 받은 자료는 남습니다.</p>
 </dialog>,document.body)
}
