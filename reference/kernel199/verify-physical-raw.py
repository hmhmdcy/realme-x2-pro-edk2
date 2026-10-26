from pathlib import Path
import hashlib,json,tarfile
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel199');records=[];previous=None
with tarfile.open(out/'native-evidence-private.tar.gz') as tar:
 for label in ['first','second']:
  name='k199-front-capture-r1/'+label+'-first-frame-private.raw';raw=tar.extractfile(name).read();assert len(raw)==2628608;p=out/(label+'-front-frame-private.raw');assert not p.exists();p.write_bytes(raw);hist=[0]*1024;row_sums=[]
  for y in range(1088):
   row=raw[y*2416:y*2416+2410];s=0
   for x in range(0,2410,5):
    a,b,c,d,e=row[x:x+5]
    for v in [(a<<2)|(e&3),(b<<2)|((e>>2)&3),(c<<2)|((e>>4)&3),(d<<2)|((e>>6)&3)]:hist[v]+=1;s+=v
   row_sums.append(s)
  assert sum(hist)==1928*1088 and sum(n>0 for n in hist)>16 and len(set(row_sums))>1
  if previous is not None:assert raw!=previous
  previous=raw;records.append(dict(label=label,raw_sha256=hashlib.sha256(raw).hexdigest(),histogram=hist,row_sums=row_sums))
(out/'physical-raw-decode-private.json').write_text(json.dumps(records,indent=2)+'\n');r=dict(stage=199,saved_physical_frames=2,packed_raw10_decoded=True,pixels_vary_in_both_frames=True,rows_vary_in_both_frames=True,frames_from_separate_runtime_cycles_differ=True,width=1928,height=1088,stride=2416,raw_and_image_fingerprints_kept_private=True,full_image_quality_not_yet_validated=True);(ref/'physical-raw-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
