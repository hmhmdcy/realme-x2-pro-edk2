"""Locate current maintainer sources for the inline ISP proposal, pinning all responses."""
from pathlib import Path
import hashlib,json,subprocess,urllib.request
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
sources=[]
def fetch(url,name):
 request=urllib.request.Request(url,headers={'User-Agent':'Samurai-camera-source-audit','Accept':'application/vnd.github+json'})
 try:
  with urllib.request.urlopen(request,timeout=25) as response:data=response.read(8*1024*1024)
  (P/name).write_bytes(data);sources.append(dict(url=url,file=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()));return json.loads(data)
 except Exception as error:
  sources.append(dict(url=url,error=str(error)));return None
repo=fetch('https://api.github.com/repos/0xB0D/ife-tests','ife-tests-repo-private.json')
if repo:
 branch=repo['default_branch'];tree=fetch('https://api.github.com/repos/0xB0D/ife-tests/git/trees/'+branch+'?recursive=1','ife-tests-tree-private.json')
 print('ife-tests:',branch,repo['clone_url']);print('Files:',[p['path'] for p in (tree or {}).get('tree',[])])
repos=fetch('https://api.github.com/users/0xB0D/repos?per_page=100','maintainer-repos-private.json')
if repos:
 selected=[r for r in repos if any(t in r['name'].lower() for t in ['linux','cam','ife'])];print('Maintainer repositories:',[(r['name'],r['clone_url']) for r in selected])
 for repo in selected:
  if repo['name'].lower()!='linux':continue
  q=subprocess.run(['git','ls-remote','--heads',repo['clone_url']],capture_output=True,text=True,timeout=50)
  (P/'maintainer-linux-refs-private.txt').write_text(q.stdout+q.stderr);assert q.returncode==0
  rows=[l for l in q.stdout.splitlines() if any(t in l.lower() for t in ['isp','ife','7.2','7-2','8650','rfc'])]
  print('Candidate kernel refs:',rows)
(R/'public-source-discovery.json').write_text(json.dumps(dict(stage=279,sources=sources,no_hardware_changes=True),indent=2)+'\n')
