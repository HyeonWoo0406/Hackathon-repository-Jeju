import {afterEach,beforeEach,expect,test,vi} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import Sales from './Sales';
beforeEach(()=>{
 Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:function(this:HTMLDialogElement){this.setAttribute('open','')}});
 Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:function(this:HTMLDialogElement){this.removeAttribute('open')}});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals()});
const store={name:'검토 가게',emd:'애월읍',industry:'카페',stops:[{id:'0003291',name:'애월'}]};
const status={online:false,hub_key:true,data_key:true,llm:true,latest_hub_date:'2026-11-08'};
const ready={ready:true,detail:'자료 준비 완료',missing_sources:[]};
const sales=[{date:'2026-10-05',amount:0,closed:false},{date:'2026-11-02',amount:0,closed:false}];
test('loading dialog stays open until report completion then hands off the report',async()=>{
 let finish!:(value:unknown)=>void;
 const pending=new Promise(resolve=>{finish=resolve});
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>({ok:true,json:async()=>{
  if(url.endsWith('/report-jobs'))return {job_id:'job'};
  if(url.endsWith('/report-jobs/job'))return pending;
  if(url.includes('/sales?'))return sales;
  return url.includes('/data-availability?')?ready:[];
 }})));
 const done=vi.fn();render(<Sales status={status} store={store} onReport={done} onDirty={()=>{}}/>);
 await screen.findAllByPlaceholderText('매출 (원)');
 fireEvent.click(screen.getByRole('button',{name:'결산 보기 →'}));
 expect(await screen.findByRole('dialog')).toBeTruthy();
 expect(screen.getByText(/보통 수 초/)).toBeTruthy();expect(done).not.toHaveBeenCalled();
 await waitFor(()=>expect(vi.mocked(fetch).mock.calls.some(([url])=>String(url).endsWith('/report-jobs/job'))).toBe(true));
 finish({state:'complete',result:{week_start:'2026-11-02'}});
 await waitFor(()=>expect(done).toHaveBeenCalledWith({week_start:'2026-11-02'}));
 expect(screen.queryByRole('dialog')).toBeNull();
});
test('real job error closes loading and preserves the input screen',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>({ok:true,json:async()=>url.endsWith('/report-jobs')?{job_id:'job'}:url.endsWith('/report-jobs/job')?{state:'failed',detail:'선택한 날짜의 자료가 없습니다.'}:url.includes('/sales?')?sales:url.includes('/data-availability?')?ready:[]})));
 const done=vi.fn();render(<Sales status={status} store={store} onReport={done} onDirty={()=>{}}/>);
 await screen.findAllByPlaceholderText('매출 (원)');fireEvent.click(screen.getByRole('button',{name:'결산 보기 →'}));
 expect(await screen.findByRole('alert')).toBeTruthy();
 expect(screen.queryByRole('dialog')).toBeNull();expect(done).not.toHaveBeenCalled();
});

test('empty sales cannot start a report',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>({ok:true,json:async()=>url.includes('/data-availability?')?ready:[]})));
 render(<Sales status={status} store={store} onReport={()=>{}} onDirty={()=>{}}/>);
 await screen.findAllByPlaceholderText('매출 (원)');
 const button=screen.getByRole('button',{name:'결산 보기 →'}) as HTMLButtonElement;
 expect(button.disabled).toBe(true);fireEvent.click(button);
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(vi.mocked(fetch).mock.calls.some(([url])=>String(url).includes('report-jobs'))).toBe(false);
});

test('missing public data blocks calculation and only queues a preparation request',async()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>({ok:true,json:async()=>{
  if(url.includes('/sales?'))return sales;
  if(url.includes('/data-availability?'))return {ready:false,detail:'공개 자료 수집 대기',missing_sources:[{source:'검증 정류소',dates:['2026-11-02']}]};
  if(url.endsWith('/data-requests'))return {detail:'자료 준비 요청을 등록했습니다.'};
  return [];
 }})));
 render(<Sales status={status} store={store} onReport={()=>{}} onDirty={()=>{}}/>);
 const request=await screen.findByRole('button',{name:'자료 준비 요청'});
 expect((screen.getByRole('button',{name:'결산 보기 →'}) as HTMLButtonElement).disabled).toBe(true);
 fireEvent.click(request);
 expect(await screen.findByText('자료 준비 요청을 등록했습니다.')).toBeTruthy();
 expect(vi.mocked(fetch).mock.calls.some(([url])=>String(url).includes('report-jobs'))).toBe(false);
 expect(screen.queryByRole('dialog')).toBeNull();
});

test('cancel requests server cancellation and does not navigate to a report',async()=>{
 let finish!:(value:unknown)=>void;
 const pending=new Promise(resolve=>{finish=resolve});
 vi.stubGlobal('fetch',vi.fn(async(url:string,options?:RequestInit)=>({ok:true,json:async()=>{
  if(options?.method==='DELETE')return {state:'cancelled'};
  if(url.endsWith('/report-jobs'))return {job_id:'job'};
  if(url.endsWith('/report-jobs/job'))return pending;
  return url.includes('/sales?')?sales:url.includes('/data-availability?')?ready:[];
 }})));
 const done=vi.fn();render(<Sales status={status} store={store} onReport={done} onDirty={()=>{}}/>);
 await screen.findAllByPlaceholderText('매출 (원)');fireEvent.click(screen.getByRole('button',{name:'결산 보기 →'}));
 await waitFor(()=>expect(vi.mocked(fetch).mock.calls.some(([url])=>String(url).endsWith('/report-jobs/job'))).toBe(true));
 fireEvent.click(screen.getByRole('button',{name:'결산 취소'}));
 finish({state:'processing'});
 await waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull());
 expect(vi.mocked(fetch).mock.calls.some(([,options])=>options?.method==='DELETE')).toBe(true);
 expect(done).not.toHaveBeenCalled();
 expect((screen.getByRole('button',{name:'결산 보기 →'}) as HTMLButtonElement).disabled).toBe(false);
});
