from pathlib import Path
import hashlib,html,json,urllib.request
from html.parser import HTMLParser

dest=Path('/mnt/e/edk2-samurai-out/kernel189/fastrpc-proposal');dest.mkdir(exist_ok=True)
url='https://lists.openwall.net/linux-kernel/2026/10/01/2547'
raw=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Samurai-Linux-bringup'}),timeout=30).read()
(dest/'v3-page.html').write_bytes(raw)
class Pre(HTMLParser):
 def __init__(self):super().__init__();self.active=False;self.parts=[]
 def handle_starttag(self,name,attrs):
  if name=='pre':self.active=True
 def handle_endtag(self,name):
  if name=='pre':self.active=False
 def handle_data(self,data):
  if self.active:self.parts.append(data)
p=Pre();p.feed(raw.decode());text=''.join(p.parts)
assert 'Subject: [PATCH v3] misc: fastrpc: fix context leak' in text
assert '20261002-anandu-fastrpc-interrupted-invoke-v3-v3-1-31e90439d2ba' in text
(dest/'v3-mail.txt').write_text(text)
patch=text[text.index('diff --git '):]
if '\nbase-commit:' in patch:patch=patch[:patch.index('\nbase-commit:')]
elif '\n-- \n' in patch:patch=patch[:patch.index('\n-- \n')]
(dest/'v3.patch').write_text(patch)
report=dict(source_url=url,message_id='20261002-anandu-fastrpc-interrupted-invoke-v3-v3-1-31e90439d2ba@oss.qualcomm.com',
 mail_sha256=hashlib.sha256(text.encode()).hexdigest(),patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
 proposal_not_assumed_merged=True,mail_lines=len(text.splitlines()),patch_lines=len(patch.splitlines()))
(Path(__file__).resolve().parent/'fastrpc-proposal-reference.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report));print(text[:text.index('diff --git ')])
