from pathlib import Path
import base64,hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
code=r'''from pathlib import Path
import base64,json,subprocess
root=Path('/var/lib/samurai/k394-ack-loss-r1');files={}
for p in list(Path('/sys/fs/pstore').iterdir())+list(root.iterdir()):
 if p.is_file() and (p.parent.name=='pstore' or p.suffix in ['.log','.out','.txt'] or p.name in ['state.json','launch.json','collector-ready.json','collector-result.json']):
  data=p.read_bytes();assert len(data)<=2097152;files[('pstore-' if p.parent.name=='pstore' else '')+p.name]=base64.b64encode(data).decode()
files['current-dmesg-private.log']=base64.b64encode(subprocess.check_output(['dmesg'])).decode()
print(json.dumps(dict(files=files,uptime=float(Path('/proc/uptime').read_text().split()[0]),test_parameter_absent=not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists(),worker_pid_from_launch_exists=Path('/proc/13432').exists())))
'''
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=30);d=json.loads(q.stdout);out=P/'recovery-collected';out.mkdir(exist_ok=True)
rows=[]
for n,v in d.pop('files').items():
 data=base64.b64decode(v);(out/n).write_bytes(data);rows.append(dict(file=n,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(P/'recovery-collection-private.json').write_text(json.dumps(dict(**d,files=rows),indent=2)+'\n')
print(json.dumps(dict(**d,files=[dict(file=r['file'],bytes=r['bytes']) for r in rows]),indent=2))
