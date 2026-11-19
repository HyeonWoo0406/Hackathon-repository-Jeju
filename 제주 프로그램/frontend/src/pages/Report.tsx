import {useEffect,useRef,useState} from 'react';
import {ReportData,pct,num} from '../api';
import ReportChat from './ReportChat';

function useWideReport(minWidth=1280){
 const [wide,setWide]=useState(()=>window.innerWidth>=minWidth);
 useEffect(()=>{
  if(!window.matchMedia)return;
  const media=window.matchMedia(`(min-width: ${minWidth}px)`);
  const update=()=>setWide(media.matches);
  update();media.addEventListener('change',update);
  return()=>media.removeEventListener('change',update);
 },[minWidth]);
 return wide;
}

export default function Report({data:r}:{data:ReportData;onDelete:()=>void}){
 const wide=useWideReport();
 const fullChart=useWideReport(761);
 const [panelOpen,setPanelOpen]=useState(()=>window.innerWidth>=1280);
 const [selectedDate,setSelectedDate]=useState(()=>r.days.find(d=>d.flag)?.date??r.days[0]?.date);
 const [chatRequest,setChatRequest]=useState(0);
 const dialog=useRef<HTMLDialogElement>(null);
 const openButton=useRef<HTMLButtonElement>(null);
 const wasOpen=useRef(panelOpen);
 const previousWide=useRef(wide);
 const selected=r.days.find(d=>d.date===selectedDate)??r.days[0];
 const chartWidth=fullChart?840:360;
 const chartLeft=12;
 const chartRight=chartWidth-8;
 const columnWidth=(chartRight-chartLeft)/7;
 const barWidth=fullChart?20:11;
 const values=r.days.flatMap(d=>[d.store??0,d.area??0]);
 const positiveLimit=Math.ceil(Math.max(0,...values)*20)/20;
 const negativeLimit=-Math.ceil(Math.max(0,...values.map(v=>-v))*20)/20;
 const chartUpper=positiveLimit===negativeLimit ? .05 : positiveLimit;
 const chartLower=positiveLimit===negativeLimit ? -.05 : negativeLimit;
 const plotTop=16,plotBottom=196;
 const chartScale=(plotBottom-plotTop)/(chartUpper-chartLower);
 const zeroY=plotTop+chartUpper*chartScale;
 const ticks=[...new Set([chartUpper,0,chartLower])].map(value=>({value,y:zeroY-value*chartScale}));
 const dayPercent=(value:number|null)=>value==null?'—':fullChart?pct(value):`${value>0?'+':''}${Math.round(value*100)}%`;
 const amount=(value:number|null,key:string)=>value==null?'자료 없음':num(value)+(key==='store'?'원':'명');
 const excludedReason=selected&&r.excluded.find(d=>d.date===selected.date)?.reason;
 const rain=selected?.rain_mm==null?'강수량 자료 없음':`강수량 ${num(selected.rain_mm)}mm`;

 useEffect(()=>{
  if(previousWide.current!==wide){
   previousWide.current=wide;
   if(!wide){setPanelOpen(false);return}
  }
  const element=dialog.current;
  if(!wide&&panelOpen&&element&&!element.open)element.showModal();
  if((wide||!panelOpen)&&element?.open)element.close();
  if(!wide&&panelOpen){
   const previous=document.body.style.overflow;
   document.body.style.overflow='hidden';
   return()=>{document.body.style.overflow=previous};
  }
 },[wide,panelOpen]);
 useEffect(()=>{
  if(wasOpen.current&&!panelOpen)openButton.current?.focus({preventScroll:true});
  wasOpen.current=panelOpen;
 },[panelOpen]);

 function ask(){if(!wide)setPanelOpen(false);setChatRequest(n=>n+1)}
 const summaryContent=<>
  <div className="inspector-heading"><h2 id="report-inspector-title">가게 결산</h2><button type="button" className="inspector-close" onClick={()=>setPanelOpen(false)} aria-label={wide?'가게 결산 접기':'가게 결산 닫기'}>{wide?'접기 ›':'닫기 ×'}</button></div>
  <div className="inspector-content">
   <section className="inspector-week"><span className="eyebrow">{r.week_start} — {r.week_end}</span><h3>{r.verdict_text}</h3><p>그 전 4주의 같은 요일 대비</p><div className="inspector-metrics"><div><span>우리 가게</span><strong>{pct(r.indicators[0].change)}</strong></div><div><span>동네 지표</span><strong>{pct(r.neighborhood)}</strong></div></div></section>
   {selected&&<section className="inspector-day"><div className="inspector-day-title"><h3>{selected.dow}요일</h3><span>{selected.date.slice(5)}</span></div><div className="day-badges"><span>{rain}</span>{selected.holiday&&<span>{selected.holiday}</span>}{selected.excluded&&<span>비교 제외</span>}{selected.flag&&!selected.excluded&&<span>확인할 날</span>}</div><dl><div><dt>우리 가게</dt><dd>{pct(selected.store)}</dd></div><div><dt>동네 지표</dt><dd>{pct(selected.area)}</dd></div></dl>{selected.excluded&&<p className="hint">{excludedReason||'이 날짜는 비교에서 제외됐습니다.'}</p>}</section>}
   <section className="inspector-note"><span className="eyebrow">결산 요약</span><p>{r.note.text}</p></section>
   <button type="button" className="inspector-ask" hidden={wide} onClick={ask}>결산에 질문하기 ↗</button>
  </div>
 </>;

 return <article className="report-page">
  <div className="report-page-heading"><div><span className="eyebrow">주간 결산 {r.example?'· 예시 자료':''}</span><h1>{r.name||r.emd+' '+r.industry}</h1><p>{r.emd} <span className="text-divider">/</span> {r.week_start} — {r.week_end}</p></div><div className="report-heading-actions"><button type="button" className="no-print" onClick={()=>window.print()}>인쇄 / PDF</button>{!wide&&<button ref={openButton} className="summary-launcher no-print" type="button" onClick={()=>setPanelOpen(true)} aria-expanded={panelOpen} aria-controls="report-inspector">가게 결산 열기</button>}</div></div>
  <section className="report-print-summary"><h2>{r.verdict_text}</h2><p>우리 가게 {pct(r.indicators[0].change)} / 동네 이용 지표 {pct(r.neighborhood)}</p><p>{r.note.text}</p></section>
  <div className={'report-layout '+(wide&&!panelOpen?'inspector-collapsed':'')}>
   <div className="report-analysis">
    {!wide&&<section className="report-overview no-print" aria-label="주간 결산 요약"><h2>{r.verdict_text}</h2><p>그 전 4주의 같은 요일 대비</p><dl><div><dt>우리 가게</dt><dd>{pct(r.indicators[0].change)}</dd></div><div><dt>동네 이용 지표</dt><dd>{pct(r.neighborhood)}</dd></div></dl></section>}
    <section className="report-chart-panel">
     <div className="section-heading"><div><h2>일별 변화 비교</h2></div><span className="chart-unit">단위 · %</span></div>
     <p className="legend"><span><i/>우리 가게</span><span><i/>동네 이용 지표</span><span className="legend-explanation">— 자료 없음 · 테두리 확인할 날</span></p>
     <div className="primary-bar-chart"><svg viewBox={`0 0 ${chartWidth} 220`} preserveAspectRatio="none" role="img" aria-label="월요일부터 일요일까지 가게 매출과 동네 이용 지표의 변화율 막대그래프. 아래 요일을 선택하면 정확한 수치를 확인할 수 있습니다.">
      <title>일별 변화율 비교</title>
      {r.days.map((d,i)=>selected?.date===d.date?<rect key={d.date} x={chartLeft+i*columnWidth+2} y="8" width={columnWidth-4} height="196" rx="5" fill="#f0f5ff"/>:null)}
      {ticks.map(({value,y},i)=><g key={i}><line x1={chartLeft} y1={y} x2={chartRight} y2={y} stroke={value===0?'#a8b4c5':'#e9edf3'}/></g>)}
      {r.days.map((d,i)=><g key={d.date} transform={`translate(${chartLeft+i*columnWidth},0)`}>
       {d.flag&&<rect x="2" y="8" width={columnWidth-4} height="196" rx="5" fill="none" stroke="#a4bce6"/>}
       {[d.store,d.area].map((v,j)=>v==null?<text key={j} x={columnWidth/2+(j===0?-1:1)*(barWidth/2+2)} y={zeroY-7} textAnchor="middle" fontSize={fullChart?18:14}>—</text>:<rect key={j} x={columnWidth/2+(j===0?-barWidth-2:2)} y={v>0?zeroY-v*chartScale:v===0?zeroY-1:zeroY} width={barWidth} height={v===0?2:Math.abs(v)*chartScale} rx="2" fill={j===0?'var(--chart-store)':'var(--chart-area)'}><title>{d.dow}요일 {j===0?'우리 가게':'동네 이용 지표'} {pct(v)}</title></rect>)}
       <text className="chart-print-day" x={columnWidth/2} y="215" textAnchor="middle" fontSize="16">{d.dow}</text>
      </g>)}
     </svg></div>
     <p className="chart-comparison-basis">그 전 4주 같은 요일 대비 · 기준선 0%</p>
     <div className="report-day-picker no-print" role="group" aria-label="비교할 요일 선택">{r.days.map(d=><button key={d.date} type="button" aria-pressed={selected?.date===d.date} aria-label={`${d.date} ${d.dow}요일 선택`} onClick={()=>setSelectedDate(d.date)}><b>{d.dow}</b><span>{d.date.slice(5)}</span><span className="day-change day-change-store" title={`우리 가게 ${pct(d.store)}`}><span className="sr-only">우리 가게 </span>{dayPercent(d.store)}</span><span className="day-change day-change-area" title={`동네 지표 ${pct(d.area)}`}><span className="sr-only">동네 지표 </span>{dayPercent(d.area)}</span><i aria-hidden="true" className={d.flag?'day-has-flag':''}/></button>)}</div>
     {!fullChart&&<p className="chart-rounding-hint">날짜 아래 수치는 반올림 · 날짜 선택 시 소수점 표시</p>}
     <details className="daily-values no-print"><summary>요일별 수치 보기</summary><div className="scroll-table"><table aria-label="요일별 변화율 수치"><thead><tr><th>변화율</th>{r.days.map(d=><th key={d.date}>{d.dow}</th>)}</tr></thead><tbody><tr><th scope="row">우리 가게</th>{r.days.map(d=><td key={d.date}>{pct(d.store)}</td>)}</tr><tr><th scope="row">동네 지표</th>{r.days.map(d=><td key={d.date}>{pct(d.area)}</td>)}</tr></tbody></table></div></details>
     {selected?<section className="selected-day-context" hidden={wide&&panelOpen} aria-live="polite" aria-atomic="true"><div><strong>{selected.dow}요일</strong><span>{selected.date}</span><span>{rain}</span><span>{selected.holiday||'공휴일 표시 없음'}</span></div><div className="selected-day-values"><span>우리 가게 <b>{pct(selected.store)}</b></span><span>동네 지표 <b>{pct(selected.area)}</b></span></div><p>{selected.excluded?excludedReason||'이 날짜는 비교에서 제외됐습니다.':selected.flag?'가게 매출과 동네 이용 지표의 차이를 확인할 날이에요.':'그 전 4주의 같은 요일과 비교한 수치예요.'}</p></section>:<p className="hint">비교할 요일별 자료가 없습니다.</p>}
    </section>
    <section className="report-table-panel"><div className="section-heading"><div><h2>지표별 상세 비교</h2><p>비교 기준 {r.base_start} — {r.base_end}</p></div></div><div className="scroll-table"><table className="indicator-table" aria-label="지표별 상세 비교"><thead><tr><th>비교 항목</th><th>대상 하루 평균</th><th>그 전 4주 하루 평균</th><th>변화</th></tr></thead><tbody>{r.indicators.map(i=><tr key={i.key} className={!i.valid?'muted':''}><th scope="row">{i.label}<small>{i.note}</small></th><td data-label="대상 하루 평균">{amount(i.avg_target,i.key)}</td><td data-label="그 전 4주 하루 평균">{amount(i.avg_base,i.key)}</td><td data-label="변화" className="metric-change">{pct(i.change)}</td></tr>)}</tbody></table></div></section>
    <div className="report-evidence-panel"><div className="weather-summary"><span>비 온 날 <b>{num(r.weather.rain_days)}일</b></span><span>강풍 <b>{num(r.weather.wind_days)}일</b></span><span>공휴일 <b>{num(r.weather.holiday_days)}일</b></span></div><details className="evidence no-print"><summary>비교 기준과 사용 자료 확인</summary><p>{r.limits}</p><h3>비교에서 제외한 날</h3><p>{r.excluded.length?r.excluded.map(d=>`${d.date.slice(5)} ${d.reason}`).join(' · '):'비교에서 제외한 날 없음'}</p><h3>날씨 비교</h3><p>기준 주당 비 온 날 {num(r.weather.rain_days_base_per_week)}일 · 강풍 {num(r.weather.wind_days_base_per_week)}일 · 공휴일 {num(r.weather.holiday_days_base_per_week)}일</p><h3>사용 자료</h3>{r.sources.map(s=><p key={s.name}>{s.name} · {s.range} · 조회 {s.fetched_at}</p>)}{r.sources_status.map(s=><p key={s}>{s}</p>)}</details><section className="print-evidence"><h3>비교 기준과 사용 자료</h3><p>{r.limits}</p><p>비교 기준: {r.base_start} — {r.base_end}</p><p>기준 주당 비 {num(r.weather.rain_days_base_per_week)}일 · 강풍 {num(r.weather.wind_days_base_per_week)}일 · 공휴일 {num(r.weather.holiday_days_base_per_week)}일</p><p>비교 제외: {r.excluded.length?r.excluded.map(d=>`${d.date} ${d.reason}`).join(' · '):'없음'}</p>{r.sources.map(s=><p key={s.name}>{s.name} · {s.range} · 조회 {s.fetched_at}</p>)}{r.sources_status.map(s=><p key={s}>{s}</p>)}</section></div>
   </div>
   {wide?<aside id="report-inspector" className="report-inspector no-print" aria-label="가게 결산" onKeyDown={e=>{if(e.key==='Escape')setPanelOpen(false)}}>{panelOpen?summaryContent:<button ref={openButton} type="button" className="inspector-reopen" onClick={()=>setPanelOpen(true)} aria-expanded="false" aria-controls="report-inspector" aria-label="가게 결산 열기"><span aria-hidden="true">‹</span><span>결산 열기</span></button>}</aside>:<dialog ref={dialog} id="report-inspector" className="report-inspector-dialog no-print" aria-labelledby="report-inspector-title" onCancel={e=>{e.preventDefault();setPanelOpen(false)}} onClose={()=>{if(!wide)setPanelOpen(false)}}>{summaryContent}</dialog>}
  </div>
  <ReportChat key={r.week_start} weekStart={r.week_start} openRequest={chatRequest}/>
 </article>;
}
