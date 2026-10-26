from pathlib import Path
import hashlib,json,re,urllib.request
P=Path('/mnt/e/edk2-samurai-out/kernel244/protocol-source');url='https://raw.githubusercontent.com/bcyj/android_tools_leeco_msm8996/master/diag/include/log_codes.h'
b=urllib.request.urlopen(url,timeout=25).read();assert len(b)>10000;(P/'log_codes.h').write_bytes(b);s=b.decode(errors='replace');lines=s.splitlines();hits=[]
for i,line in enumerate(lines):
 if re.search(r'#define.*(?:GNSS|GPS).*(?:CLOCK|RF_|HARDWARE|HW_|MEASUREMENT|SEARCH|STATUS|STATE)',line):hits.append(dict(line=i+1,text=line))
v=dict(url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),matches=hits);(P/'log-code-hits-private.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
