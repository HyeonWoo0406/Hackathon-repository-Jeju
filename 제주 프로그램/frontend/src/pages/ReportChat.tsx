import {useEffect,useRef,useState} from 'react';
import {api} from '../api';

type Message={role:'user'|'assistant';text:string;by?:string};
const shortcuts=[['day_detail','요일별 자세히'],['rain','비 온 날'],['island','제주 전체 비교'],['excluded','뺀 날과 이유'],['sources','쓴 자료'],['history','지난 결산']];

export default function ReportChat({weekStart}:{weekStart:string}){
 const [open,setOpen]=useState(false),[question,setQuestion]=useState(''),[messages,setMessages]=useState<Message[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const input=useRef<HTMLInputElement>(null),launcher=useRef<HTMLButtonElement>(null),log=useRef<HTMLDivElement>(null),pending=useRef(false),mounted=useRef(true);
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false}},[]);
 useEffect(()=>{if(open)input.current?.focus()},[open]);
 useEffect(()=>{if(log.current)log.current.scrollTop=log.current.scrollHeight},[messages,busy,open]);
 function close(){setOpen(false);launcher.current?.focus()}
 async function ask(intent?:string,label?:string){
  const text=label??question.trim();if(!text||pending.current)return;
  pending.current=true;setBusy(true);setError('');setMessages(old=>[...old,{role:'user',text}]);setQuestion('');
  try{
   const answer=await api<{answer:string;by:string;notice?:string}>('ask','POST',{week_start:weekStart,...(intent?{intent}:{question:text})});
   if(mounted.current)setMessages(old=>[...old,{role:'assistant',text:answer.answer,by:answer.by}]);
  }catch(e){if(mounted.current){setError((e as Error).message);if(!intent)setQuestion(text)}}
  finally{pending.current=false;if(mounted.current)setBusy(false)}
 }
 return <aside className="report-chat no-print">
 {open&&<section id="report-chat-panel" className="chat-panel" role="dialog" aria-labelledby="report-chat-title" onKeyDown={e=>{if(e.key==='Escape'){e.stopPropagation();close()}}}>
  <div className="chat-heading"><div><h2 id="report-chat-title">결산에 질문하기</h2><small>{weekStart} 주간 결산 기준</small></div><button type="button" onClick={close} aria-label="채팅 닫기">×</button></div>
  <p className="chat-guide">매출 변화·요일별 비교·날씨·출처를 물어보세요. 각 질문은 현재 결산을 기준으로 답합니다.</p>
  <div className="chat-log" ref={log} role="log" aria-label="결산 질문과 답변" aria-live="polite" aria-relevant="additions">
   {!messages.length&&<p className="chat-message assistant">어떤 점이 궁금하세요? 예: “토요일은 어땠어?”</p>}
   {messages.map((message,index)=><div className={'chat-message '+message.role} key={index}><small>{message.role==='user'?'나':message.by==='model'?'AI 답변':message.by==='unsupported'?'답변 안내':'결산 자료 안내'}</small><p>{message.text}</p></div>)}
   {busy&&<p className="chat-pending" role="status">결산 근거를 확인하고 있어요…</p>}
  </div>
  {error&&<p className="error" role="alert">{error}</p>}
  <div className="chat-shortcuts">{shortcuts.map(([intent,label])=><button type="button" key={intent} disabled={busy} onClick={()=>ask(intent,label)}>{label}</button>)}</div>
  <form className="chat-compose" onSubmit={e=>{e.preventDefault();void ask()}}><label htmlFor="report-chat-question">궁금한 점</label><div><input id="report-chat-question" ref={input} value={question} maxLength={500} disabled={busy} onChange={e=>setQuestion(e.target.value)} placeholder="결산에 대해 질문해 주세요"/><button type="submit" disabled={busy||!question.trim()}>보내기</button></div></form>
 </section>}
 <button ref={launcher} className="chat-launcher" type="button" aria-label={open?'결산 채팅 닫기':'결산 채팅 열기'} aria-expanded={open} aria-controls="report-chat-panel" onClick={()=>open?close():setOpen(true)}><svg viewBox="0 0 24 24" width="25" height="25" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M5 4h14a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H9l-5 3V5a1 1 0 0 1 1-1Z"/></svg><span>결산 질문</span></button>
 </aside>
}
