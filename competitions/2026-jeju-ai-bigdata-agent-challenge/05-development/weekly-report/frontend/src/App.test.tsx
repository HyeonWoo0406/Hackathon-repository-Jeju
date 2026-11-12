import {afterEach,beforeEach,expect,test,vi} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import App from './App';
const stop={id:'0003291',name:'애월환승정류장(애월리)'};
beforeEach(()=>{
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>({ok:true,json:async()=>{
  if(url.endsWith('/status'))return {online:false,llm:false,latest_hub_date:'2026-11-08'};
  if(url.endsWith('/store'))return {id:1,name:'검토 카페',emd:'애월읍',industry:'카페',stops:[stop]};
  if(url.includes('/data-availability?'))return {ready:true,detail:'자료 준비 완료',missing_sources:[]};
  if(url.endsWith('/emds'))return ['애월읍'];
  if(url.includes('/stops?'))return url.includes('no-match')?[]:[stop];
  return [];
 }})));
});
afterEach(()=>{cleanup();vi.unstubAllGlobals()});

test('step buttons navigate and back keeps unsaved sales',async()=>{
 render(<App/>);
 const inputs=await screen.findAllByPlaceholderText('매출 (원)');
 fireEvent.change(inputs[0],{target:{value:'123456'}});
 fireEvent.click(screen.getByRole('button',{name:'01 가게 등록'}));
 expect(screen.getByRole('heading',{name:'어디에서 장사하시나요?'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'← 매출 입력으로 돌아가기'}));
 expect((screen.getAllByPlaceholderText('매출 (원)')[0] as HTMLInputElement).value).toBe('123,456');
 fireEvent.click(screen.getByRole('button',{name:'03 결산표'}));
 expect(screen.getByRole('heading',{name:'아직 만든 결산표가 없어요.'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'← 매출 입력으로 돌아가기'}));
 expect(screen.getByRole('heading',{name:'지난주 장사, 숫자부터.'})).toBeTruthy();
});

test('station shortcut focuses search and number is sent on Enter',async()=>{
 render(<App/>);await screen.findAllByPlaceholderText('매출 (원)');
 fireEvent.click(screen.getByRole('button',{name:'정류소 검색·변경'}));
 const input=screen.getByRole('textbox',{name:'정류소 검색'});
 expect(document.activeElement).toBe(input);
 fireEvent.change(input,{target:{value:'0003291'}});
 fireEvent.submit(input.closest('form')!);
 await waitFor(()=>expect(vi.mocked(fetch).mock.calls.some(([url])=>String(url).endsWith('stops?q=0003291'))).toBe(true));
 expect(screen.getByText('0003291')).toBeTruthy();
});

test('empty station results explain how to try again',async()=>{
 render(<App/>);await screen.findAllByPlaceholderText('매출 (원)');
 fireEvent.click(screen.getByRole('button',{name:'01 가게 등록'}));
 fireEvent.change(screen.getByRole('textbox',{name:'정류소 검색'}),{target:{value:'no-match'}});
 expect(await screen.findByText('검색 결과가 없습니다. 이름 일부나 번호로 다시 검색해 주세요.')).toBeTruthy();
});

test('resaving a loaded legacy store omits its internal identifier',async()=>{
 render(<App/>);await screen.findAllByPlaceholderText('매출 (원)');
 fireEvent.click(screen.getByRole('button',{name:'01 가게 등록'}));
 fireEvent.click(screen.getByRole('button',{name:'저장하고 매출 입력 →'}));
 await waitFor(()=>expect(vi.mocked(fetch).mock.calls.some(([,options])=>options?.method==='PUT')).toBe(true));
 const call=vi.mocked(fetch).mock.calls.find(([,options])=>options?.method==='PUT')!;
 expect(JSON.parse(String(call[1]?.body))).toEqual({name:'검토 카페',emd:'애월읍',industry:'카페',stops:[stop]});
});

test('records can be cleared before a report exists and cancellation preserves them',async()=>{
 render(<App/>);await screen.findAllByPlaceholderText('매출 (원)');
 fireEvent.click(screen.getByRole('button',{name:'내 자료 지우기'}));
 fireEvent.click(screen.getByRole('button',{name:'취소'}));
 expect(vi.mocked(fetch).mock.calls.some(([,options])=>options?.method==='DELETE')).toBe(false);
 fireEvent.click(screen.getByRole('button',{name:'내 자료 지우기'}));
 fireEvent.click(screen.getByRole('button',{name:'모두 지우고 처음부터 시작'}));
 await waitFor(()=>expect(screen.getByRole('heading',{name:'어디에서 장사하시나요?'})).toBeTruthy());
 expect((screen.getByPlaceholderText('예: 애월 작은 카페') as HTMLInputElement).value).toBe('');
 expect(vi.mocked(fetch).mock.calls.filter(([,options])=>options?.method==='DELETE')).toHaveLength(1);
});
