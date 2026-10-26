from pathlib import Path
import json,re,subprocess
root=Path('/var/lib/samurai');out=root/'k197-media-tools';out.mkdir(mode=0o700);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k197-baseline/boot-id-private.txt').read_bytes()
reports=[]
for device in sorted(Path('/dev').glob('media*')):
 p=subprocess.run(['media-ctl','-d',str(device),'-p'],capture_output=True,text=True,timeout=15);(out/(device.name+'-topology-private.txt')).write_text(p.stdout+p.stderr);assert p.returncode==0;reports.append(dict(device=device.name,entities=re.findall(r'- entity (\d+): ([^\n]+)',p.stdout)))
print(json.dumps(dict(stage=197,media=reports)))
