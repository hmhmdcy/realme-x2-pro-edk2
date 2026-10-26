"""Locate existing native geometry and the remaining fixed-size gates."""
from pathlib import Path
import json,re,subprocess
import storage,host
v=storage.mount.mounted_build().parent;t=storage.candidate()/'src/libcamera-v0.7.2';k=v/'source354/drivers/media/platform/qcom/camss'
assert subprocess.check_output(['git','-C','/home/cy122/edk2-samurai/repo','rev-parse','HEAD'],text=True).strip()=='5b3c59ebffaf0eef10ae149f94bcc59e4b887605'
pattern=re.compile(r'640|480|160|120|coarse|pd10|grid',re.I);rows=[]
paths=[t/'src/libcamera/pipeline/camss-vfe/camss_ipe.cpp',t/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp',t/'src/ipa/camss-vfe/ipe_tone_profile.cpp']
paths+=sorted(set(k.glob('*ipe*.c'))|set(k.glob('*strip*.c'))|set(k.glob('*strip*.h')))
for path in paths:
 if not path.exists():continue
 hits=[{'line':i,'text':line} for i,line in enumerate(path.read_text().splitlines(),1) if pattern.search(line)]
 if hits:rows.append({'path':str(path),'hits':hits})
(host.PRIVATE/'source-size-gates-private.json').write_text(json.dumps(rows,indent=2))
for row in rows:
 print('\n'+row['path'])
 for hit in row['hits'][:100]:print(str(hit['line'])+':'+hit['text'])
 print('TOTAL_HITS',len(row['hits']))
