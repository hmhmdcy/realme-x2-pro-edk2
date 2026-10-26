from pathlib import Path
import host,json

code=r'''
from pathlib import Path
import json,os,subprocess
root=Path('/var/lib/samurai');out=root/'k219-startup-inspection';out.mkdir(mode=0o700,exist_ok=True)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k219-runtime/boot-id-private.txt').read_bytes()
statuses={}
for name in ['samurai-ssc','samurai-radio','bluetooth','greetd','samurai-gnss-assist']:
    try:
        p=subprocess.run(['rc-service',name,'status'],capture_output=True,text=True,timeout=5);statuses[name]=dict(exit=p.returncode,text=p.stdout+p.stderr)
    except subprocess.TimeoutExpired:statuses[name]=dict(timeout=True)
(out/'service-status-private.json').write_text(json.dumps(statuses,indent=2)+'\n')
commands=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        text=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        if any(x in text for x in ['openrc','samurai-ssc','samurai-radio','samurai-gnss','hexagon','tqftp']):commands.append(dict(pid=int(p.name),comm=(p/'comm').read_text().strip(),args=text))
    except OSError:pass
(out/'startup-processes-private.json').write_text(json.dumps(commands,indent=2)+'\n')
logs={}
for base in ['/var/log','/run/samurai-ssc']:
    p=Path(base)
    if not p.exists():continue
    for f in p.rglob('*'):
        if f.is_file() and f.stat().st_size<4*1024*1024 and any(x in f.name.lower() for x in ['ssc','boot','rc.log','radio','error','log']):
            try:logs[str(f)]=f.read_text(errors='replace')[-30000:]
            except OSError:pass
(out/'startup-logs-private.json').write_text(json.dumps(logs,indent=2)+'\n')
print(json.dumps(dict(uptime=float(Path('/proc/uptime').read_text().split()[0]),statuses=statuses,process_names=[x['comm'] for x in commands],log_files=list(logs))))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=45)
(host.PRIVATE/'startup-inspection-host-private.json').write_bytes(p.stdout)
print(p.stdout.decode().strip())
