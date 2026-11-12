import {afterEach,expect,test,vi} from 'vitest';
import {render,screen,act,fireEvent,cleanup} from '@testing-library/react';
import ReportLoading from './ReportLoading';
afterEach(()=>{cleanup();vi.useRealTimers()});
test('elapsed time advances past 60 seconds and cancellation remains available',()=>{
 vi.useFakeTimers();
 Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:function(this:HTMLDialogElement){this.setAttribute('open','')}});
 Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:function(this:HTMLDialogElement){this.removeAttribute('open')}});
 const cancel=vi.fn();render(<ReportLoading onCancel={cancel} cancelling={false}/>);
 expect(screen.getByRole('timer').textContent).toContain('00:00');
 act(()=>vi.advanceTimersByTime(61000));
 expect(screen.getByRole('timer').textContent).toContain('01:01');
 expect(screen.getByRole('dialog')).toBeTruthy();
 expect(screen.getByText(/資料|자료를 계속 확인/)).toBeTruthy();
 fireEvent.click(screen.getByRole('button',{name:'결산 취소'}));expect(cancel).toHaveBeenCalledOnce();
});
