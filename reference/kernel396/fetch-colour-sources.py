"""Retain a bounded pinned source set and target HAL instruction windows."""
from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;out=P/'sources';out.mkdir(exist_ok=True)
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';commit='9f17f1b568626b393e785b369c5dc94543774d7a'
paths=['camx/src/hwl/iqsetting/cc13setting.cpp','camx/src/hwl/iqsetting/cc13setting.h','camx/src/hwl/isphwsetting/titan17x/camxipecc13titan17x.cpp','camx/src/hwl/isphwsetting/titan17x/camxipecc13titan17x.h']
rows=[]
for path in paths:
 p=out/Path(path).name
 if not p.exists():p.write_bytes(subprocess.check_output(['git','-C',repo,'show',commit+':'+path],timeout=40))
 rows.append(dict(path=path,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/'+commit+'/'+path))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=396,commit=commit,files=rows),indent=2)+'\n')
symbols=(P.parent/'kernel350/hal-symbols-private.txt').read_text().splitlines()
selected=[l for l in symbols if re.search(r'IPECC13|CC13Setting|IPECC.*13|CC13Interpolation|IPEColorCorrection13|CC13CalculateSetting',l)]
(P/'hal-colour-symbols-private.txt').write_text('\n'.join(selected)+'\n');print('\n'.join(selected))
hal=P.parent/'kernel281/camera.qcom.so-private';assert hashlib.sha256(hal.read_bytes()).hexdigest()=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
addresses=sorted(set(int(l.split()[0],16) for l in selected if len(l.split())>2 and l.split()[1].lower()=='t'))
all_addresses=sorted(set(int(l.split()[0],16) for l in symbols if len(l.split())>2 and l.split()[1].lower()=='t'))
for a in addresses:
 b=next((x for x in all_addresses if x>a),a+0x1000)
 if b-a>0x10000:continue
 q=subprocess.run(['aarch64-linux-gnu-objdump','-d','-C','--start-address='+hex(a),'--stop-address='+hex(b),str(hal)],check=True,capture_output=True)
 (P/('hal-colour-'+hex(a)+'-private.asm')).write_bytes(q.stdout)
print(json.dumps(dict(source_files=len(rows),hal_instruction_windows=len(addresses))))
