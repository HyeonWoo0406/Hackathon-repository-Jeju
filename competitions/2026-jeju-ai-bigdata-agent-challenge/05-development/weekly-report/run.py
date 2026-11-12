import os
import subprocess
import threading
import webbrowser
import atexit
from backend.app.db import ROOT
from backend.app.main import app,PORT

if __name__=='__main__':
    import uvicorn
    model=ROOT/'models'/'qwen2.5-1.5b-instruct-q4_k_m.gguf'
    exe=ROOT/'llama-server.exe'
    process=None
    if model.exists() and exe.exists():
        process=subprocess.Popen([str(exe),'-m',str(model),'--host','127.0.0.1','--port','8766','--ctx-size','2048','--log-disable','--no-webui'],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        atexit.register(process.terminate)
    if os.getenv('WEEKLY_NO_BROWSER')!='1':threading.Timer(1.5,lambda:webbrowser.open(f'http://127.0.0.1:{PORT}')).start()
    try:uvicorn.run(app,host='127.0.0.1',port=PORT,access_log=False)
    finally:
        if process:process.terminate()
