from pathlib import Path
from html.parser import HTMLParser
import urllib.request,json,hashlib,re
out=Path('/mnt/e/edk2-samurai-out/kernel121/pm8008-reference');out.mkdir(parents=True,exist_ok=True)
class MessageText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,data):self.parts.append(data)
records=[]
for name,url in [('mfd-no-irq','https://lkml.iu.edu/hypermail/linux/kernel/2609.1/01450.html'),('binding-optional-irq','https://lkml.iu.edu/2609.2/08693.html')]:
    with urllib.request.urlopen(url,timeout=30) as response:body=response.read()
    (out/(name+'.html')).write_bytes(body)
    message=body.decode().split('<!--X-Body-of-Message-->',1)[1].split('<!--X-Body-of-Message-End-->',1)[0]
    # MHonArc preserves line endings and appends <br>; adding newlines would
    # corrupt unified-diff hunk counts. HTMLParser decodes escaped C operators.
    parser=MessageText();parser.feed(message);text=''.join(parser.parts)
    assert 'diff --git ' in text
    patch=re.split(r'\n-- ?\n',text[text.index('diff --git '):],maxsplit=1)[0].rstrip()+'\n'
    assert '\n@@ ' in patch and not '<' in patch.splitlines()[0]
    (out/(name+'.patch')).write_text(patch)
    records.append(dict(name=name,url=url,patch_bytes=len(patch.encode()),sha256=hashlib.sha256(patch.encode()).hexdigest(),not_applied_yet=True))
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel121');ref.mkdir(parents=True,exist_ok=True)
(ref/'pm8008-reference-validation.json').write_text(json.dumps(dict(primary_mailing_list_sources=records),indent=2)+'\n')
print(json.dumps(records))
