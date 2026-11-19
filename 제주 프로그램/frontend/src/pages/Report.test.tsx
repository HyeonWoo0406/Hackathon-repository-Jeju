import {afterEach,beforeEach,expect,test,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import {ReportData} from '../api';
import Report from './Report';

const initialWidth=window.innerWidth;
function viewport(width:number){
 Object.defineProperty(window,'innerWidth',{configurable:true,value:width});
 vi.stubGlobal('matchMedia',vi.fn(()=>({matches:width>=1280,addEventListener:vi.fn(),removeEventListener:vi.fn()})));
}
beforeEach(()=>{
 viewport(1440);
 Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:function(this:HTMLDialogElement){this.setAttribute('open','')}});
 Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:function(this:HTMLDialogElement){this.removeAttribute('open');this.dispatchEvent(new Event('close'))}});
});
afterEach(()=>{cleanup();vi.unstubAllGlobals();Object.defineProperty(window,'innerWidth',{configurable:true,value:initialWidth});document.body.style.overflow=''});

const data:ReportData={
 week_start:'2026-11-02',week_end:'2026-11-08',base_start:'2026-10-05',base_end:'2026-11-01',name:'검수 카페',emd:'애월읍',industry:'카페',verdict:'area',verdict_text:'동네와 함께 줄었어요',neighborhood:-.08,example:true,limits:'원인을 확정하지 않습니다.',
 indicators:[{key:'store',label:'우리 가게 매출',avg_target:100000,avg_base:120000,change:-.12,valid:true,note:null},{key:'wifi',label:'동네 와이파이',avg_target:null,avg_base:null,change:null,valid:false,note:'자료 부족'}],
 days:['월','화','수','목','금','토','일'].map((dow,i)=>({date:`2026-11-0${i+2}`,dow,store:i===2?0:-.05,area:i===2?null:-.03,flag:i===5,excluded:false,rain_mm:i===5?12:0,holiday:null})),
 excluded:[],sources:[],note:{text:'가게 매출과 동네 이용 지표가 함께 줄었습니다.',by:'template'},sources_status:[],weather:{rain_days:1,rain_days_base_per_week:1,wind_days:0,wind_days_base_per_week:0,holiday_days:0,holiday_days_base_per_week:0},
};

test('selecting a date updates the inspector and survives folding and reopening',()=>{
 render(<Report data={data} onDelete={()=>{}}/>);
 const panel=screen.getByRole('complementary',{name:'가게 결산'});
 expect(within(panel).getByRole('heading',{name:'토요일'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'2026-11-02 월요일 선택'}));
 expect(within(panel).getByRole('heading',{name:'월요일'})).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'가게 결산 접기'}));
 const reopen=screen.getByRole('button',{name:'가게 결산 열기'});
 expect(document.activeElement).toBe(reopen);
 fireEvent.click(reopen);
 expect(within(screen.getByRole('complementary',{name:'가게 결산'})).getByRole('heading',{name:'월요일'})).toBeTruthy();
 expect(screen.queryByText(/시간대/)).toBeNull();
});

test('missing values keep their meaning separately from a zero percent change',()=>{
 render(<Report data={data} onDelete={()=>{}}/>);
 fireEvent.click(screen.getByRole('button',{name:'2026-11-04 수요일 선택'}));
 const panel=screen.getByRole('complementary',{name:'가게 결산'});
 expect(within(panel).getByText('0.0%')).toBeTruthy();
 expect(within(panel).getByText('비교 불가')).toBeTruthy();
 expect(within(screen.getByRole('table',{name:'지표별 상세 비교'})).getAllByText('자료 없음')).toHaveLength(2);
 expect(screen.queryByText('자료 없음명')).toBeNull();
});

test('mobile summary opens as a modal and cancellation restores the page',()=>{
 viewport(390);render(<Report data={data} onDelete={()=>{}}/>);
 const overview=screen.getByRole('region',{name:'주간 결산 요약'});
 expect(within(overview).getByRole('heading',{name:data.verdict_text})).toBeTruthy();
 expect(within(overview).getByText('-12.0%')).toBeTruthy();
 expect(within(overview).getByText('-8.0%')).toBeTruthy();
 expect(screen.queryByRole('dialog',{name:'가게 결산'})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'가게 결산 열기'}));
 const modal=screen.getByRole('dialog',{name:'가게 결산'});
 expect(document.body.style.overflow).toBe('hidden');
 fireEvent(modal,new Event('cancel',{bubbles:true,cancelable:true}));
 expect(screen.queryByRole('dialog',{name:'가게 결산'})).toBeNull();
 expect(document.body.style.overflow).toBe('');
 expect(document.activeElement).toBe(screen.getByRole('button',{name:'가게 결산 열기'}));
});

test('the mobile summary hands off to the existing report question panel',()=>{
 viewport(390);render(<Report data={data} onDelete={()=>{}}/>);
 fireEvent.click(screen.getByRole('button',{name:'가게 결산 열기'}));
 fireEvent.click(within(screen.getByRole('dialog',{name:'가게 결산'})).getByRole('button',{name:'결산에 질문하기 ↗'}));
 expect(screen.queryByRole('dialog',{name:'가게 결산'})).toBeNull();
 expect(screen.getByRole('dialog',{name:'결산에 질문하기'})).toBeTruthy();
 expect(document.activeElement).toBe(screen.getByLabelText('궁금한 점'));
});


test('resizing from the desktop sidebar never opens a mobile modal automatically',()=>{
 const listeners=new Set<()=>void>();
 vi.stubGlobal('matchMedia',vi.fn((query:string)=>({
  get matches(){return window.innerWidth>=Number(query.match(/\d+/)?.[0]??1280)},
  addEventListener:(_type:string,listener:()=>void)=>listeners.add(listener),
  removeEventListener:(_type:string,listener:()=>void)=>listeners.delete(listener),
 })));
 render(<Report data={data} onDelete={()=>{}}/>);
 fireEvent.click(screen.getByRole('button',{name:'2026-11-02 월요일 선택'}));
 act(()=>{
  Object.defineProperty(window,'innerWidth',{configurable:true,value:390});
  listeners.forEach(listener=>listener());
 });
 expect(screen.queryByRole('dialog',{name:'가게 결산'})).toBeNull();
 expect(document.body.style.overflow).toBe('');
 fireEvent.click(screen.getByRole('button',{name:'가게 결산 열기'}));
 const panel=screen.getByRole('dialog',{name:'가게 결산'});
 expect(within(panel).getByRole('heading',{name:'월요일'})).toBeTruthy();
});


test('positive and negative changes use the same bar scale after empty space is removed',()=>{
 const mixed={...data,days:data.days.map((day,index)=>index===0?{...day,store:.04,area:-.04}:day)};
 render(<Report data={mixed} onDelete={()=>{}}/>);
 const chart=screen.getByRole('img',{name:/월요일부터 일요일까지/});
 const bars=Array.from(chart.querySelectorAll('rect'));
 const increase=bars.find(bar=>bar.querySelector('title')?.textContent==='월요일 우리 가게 +4.0%')!;
 const decrease=bars.find(bar=>bar.querySelector('title')?.textContent==='월요일 동네 이용 지표 -4.0%')!;
 const height=Number(increase.getAttribute('height'));
 expect(height).toBeGreaterThan(0);
 expect(height).toBeCloseTo(Number(decrease.getAttribute('height')));
 expect(Number(increase.getAttribute('y'))+height).toBeCloseTo(Number(decrease.getAttribute('y')));
 for(const bar of bars){
  expect(Number(bar.getAttribute('y'))).toBeGreaterThanOrEqual(0);
  expect(Number(bar.getAttribute('y'))+Number(bar.getAttribute('height'))).toBeLessThanOrEqual(220);
 }
});
