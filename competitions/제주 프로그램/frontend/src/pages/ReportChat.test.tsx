import {afterEach,expect,test,vi} from 'vitest';
import {render,screen,fireEvent,cleanup,waitFor} from '@testing-library/react';
import ReportChat from './ReportChat';
afterEach(()=>{cleanup();vi.unstubAllGlobals()});

test('floating panel submits report context and keeps rejection visible after reopening',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({answer:'답변을 드릴 수 없는 질문입니다.',by:'unsupported'})})));
 render(<ReportChat weekStart="2026-11-02"/>);
 expect(screen.queryByRole('dialog')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'결산 채팅 열기'}));
 const input=screen.getByLabelText('궁금한 점');expect(document.activeElement).toBe(input);
 fireEvent.change(input,{target:{value:'점심 뭐 먹지?'}});
 fireEvent.submit(input.closest('form')!);
 expect(await screen.findByText('답변을 드릴 수 없는 질문입니다.')).toBeTruthy();
 expect(JSON.parse(String(vi.mocked(fetch).mock.calls[0][1]?.body))).toEqual({week_start:'2026-11-02',question:'점심 뭐 먹지?'});
 expect(screen.getByText('답변 안내')).toBeTruthy();
 fireEvent.keyDown(screen.getByRole('dialog'),{key:'Escape'});
 expect(screen.queryByRole('dialog')).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:'결산 채팅 열기'}));
 expect(screen.getByText('답변을 드릴 수 없는 질문입니다.')).toBeTruthy();
});

test('failed requests preserve the question for retry',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,json:async()=>({detail:'연결을 확인하세요.'})})));
 render(<ReportChat weekStart="2026-11-02"/>);
 fireEvent.click(screen.getByRole('button',{name:'결산 채팅 열기'}));
 const input=screen.getByLabelText('궁금한 점') as HTMLInputElement;
 fireEvent.change(input,{target:{value:'토요일은 어땠어?'}});fireEvent.submit(input.closest('form')!);
 await waitFor(()=>expect(input.value).toBe('토요일은 어땠어?'));
 expect(await screen.findByRole('alert')).toBeTruthy();
 expect((screen.getByRole('button',{name:'보내기'}) as HTMLButtonElement).disabled).toBe(false);
});
