"""Install pinned official local-model artifacts, verifying their SHA-256."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
MODEL='qwen2.5-1.5b-instruct-q4_k_m.gguf'
MODEL_HASH='6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e'
ARCHIVE_HASH='96e5008bde3367ef049a0f327e0674b149a4e3385af90b3f046cc7fe0301d322'

def download(url,destination,expected):
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        with destination.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=expected:raise ValueError('Existing file hash differs; preserved')
        return
    temporary=destination.with_suffix(destination.suffix+'.part')
    digest=hashlib.sha256();size=0;last=0
    with httpx.Client(timeout=120,follow_redirects=True,trust_env=False) as c:
        with c.stream('GET',url) as response:
            response.raise_for_status()
            with temporary.open('wb') as f:
                for chunk in response.iter_bytes(1024*1024):
                    f.write(chunk);digest.update(chunk);size+=len(chunk)
                    if size-last>=200_000_000:print(f'{destination.name}: {size//1_000_000} MB',flush=True);last=size
    if digest.hexdigest()!=expected:raise ValueError('Downloaded file hash differs')
    temporary.replace(destination)

def main():
    target=ROOT/'dist'
    download('https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/'+MODEL,target/'models'/MODEL,MODEL_HASH)
    archive=ROOT/'runtime'/'llama-b12317-bin-win-cpu-x64.zip'
    download('https://github.com/ggml-org/llama.cpp/releases/download/b12317/llama-b12317-bin-win-cpu-x64.zip',archive,ARCHIVE_HASH)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name=Path(info.filename).name
            if name=='llama-server.exe' or name.endswith('.dll'):
                destination=target/name;content=z.read(info)
                if destination.exists() and destination.read_bytes()!=content:raise ValueError('Existing runtime differs; preserved')
                destination.write_bytes(content)
    (target/'models'/'manifest.json').write_text(json.dumps({'model':MODEL,'model_sha256':MODEL_HASH,'runtime_release':'b12317','runtime_archive_sha256':ARCHIVE_HASH},indent=2),encoding='utf-8')
    print('Verified local model and CPU runtime installed',flush=True)
if __name__=='__main__':main()
