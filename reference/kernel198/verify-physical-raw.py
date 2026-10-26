from pathlib import Path
import hashlib,json,struct,host
out=host.PRIVATE;remote='/var/lib/samurai/k198-front-capture-r1/';host.download(remote+'first-frame-private.raw',out/'first-front-frame-private.raw');host.download(remote+'summary.json',out/'front-summary-private.json');r=json.loads((out/'front-summary-private.json').read_text());data=(out/'first-front-frame-private.raw').read_bytes();assert len(data)==2628608 and r['physical_image_capture'] and r['capture_returncode']==0
hist=[0]*1024;minimum=1023;maximum=0;line_totals=[];different_adjacent=0;total=0
for y in range(1088):
 row=data[y*2416:y*2416+2410];pixels=[]
 for x in range(0,len(row),5):
  b0,b1,b2,b3,b4=row[x:x+5];pixels.extend([(b0<<2)|(b4&3),(b1<<2)|((b4>>2)&3),(b2<<2)|((b4>>4)&3),(b3<<2)|((b4>>6)&3)])
 assert len(pixels)==1928;line_totals.append(sum(pixels))
 for value in pixels:hist[value]+=1;minimum=min(minimum,value);maximum=max(maximum,value);total+=value
 different_adjacent+=sum(a!=b for a,b in zip(pixels,pixels[1:]))
occupied=sum(n>0 for n in hist);assert occupied>16 and maximum>minimum and different_adjacent>0 and len(set(line_totals))>1
private=dict(raw_sha256=hashlib.sha256(data).hexdigest(),min_pixel=minimum,max_pixel=maximum,occupied_bins=occupied,mean=total/(1928*1088),histogram=hist,different_adjacent=different_adjacent,line_totals=line_totals);(out/'raw-decode-private.json').write_text(json.dumps(private,indent=2)+'\n')
public=dict(stage=198,physical_frames=3,width=1928,height=1088,format='SRGGB10P',stride=2416,bytes_per_frame=len(data),test_patterns_disabled=True,packed_raw10_structure_decoded=True,pixel_values_vary=True,rows_vary=True,constant_or_unchanged_prefill_rejected=True,image_and_image_fingerprints_kept_private=True,first_frame_only_saved=True,exposure_color_optics_accuracy_not_yet_validated=True);(Path(__file__).resolve().parent/'physical-raw-validation.json').write_text(json.dumps(public,indent=2)+'\n');print(json.dumps(public))
