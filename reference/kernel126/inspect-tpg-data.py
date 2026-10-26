from pathlib import Path
import tarfile,json,collections,re,hashlib
out=Path('/mnt/e/edk2-samurai-out/kernel126')
with tarfile.open(out/'tpg-once-private.tar') as tf:data={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for line in data['SHA256SUMS'].decode().splitlines():
 h,n=line.split('  ',1);assert hashlib.sha256(data[n.removeprefix('./')]).hexdigest()==h
raw=data['first-frame-private.raw'];assert len(raw)==96000
pixels=[]
for offset in range(0,len(raw),5):
 chunk=raw[offset:offset+5];pixels.extend([(chunk[i]<<2)|((chunk[4]>>(2*i))&3) for i in range(4)])
assert len(pixels)==320*240
histogram=collections.Counter(pixels)
rows=[pixels[y*320:(y+1)*320] for y in range(240)]
summary=dict(unique_bytes=len(set(raw)),pixel_histogram=sorted(histogram.items()),row_unique_counts=sorted(set(map(lambda row:len(set(row)),rows))),row0_even=rows[0][::2],row0_odd=rows[0][1::2],row1_even=rows[1][::2],row1_odd=rows[1][1::2],pairs_repeat=all(rows[y]==rows[y%2] for y in range(240)),capture=data['capture.txt'].decode(),new_log=data['dmesg-after.txt'].decode()[len(data['dmesg-before.txt'].decode()):])
(out/'tpg-pixel-analysis-private.json').write_text(json.dumps(summary,indent=2)+'\n')
for key in ['unique_bytes','pixel_histogram','row_unique_counts','pairs_repeat','new_log']:print(key,summary[key])
for key in ['row0_even','row0_odd','row1_even','row1_odd']:print(key,[(v,len(list(items))) for v,items in __import__('itertools').groupby(summary[key])])
for name in ['interrupts-before.txt','interrupts-after.txt','power-before.txt','power-after.txt']:
 print(name,'\n'.join(l for l in data[name].decode().splitlines() if any(word in l.lower() for word in ['csid','vfe','camss','camnoc','ife','vfe0','camss_top'])))
