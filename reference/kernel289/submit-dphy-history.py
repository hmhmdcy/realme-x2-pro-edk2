"""Use standard link setup to isolate retained PHY history from DMI readback behavior."""
from pathlib import Path
import base64,json
import host

ROOT=Path(__file__).resolve().parent
s=(ROOT/'native-dmi-sequential.py').read_text().replace('k289-dmi-r2','k289-dmi-r3')
needle="log=root/'capture-private.log'"
assert s.count(needle)==1
s=s.replace(needle,'''section=graph_before.decode().split(': msm_csid0 (',1)[1].split('pad1: SOURCE',1)[0]
 history_links=[(name, bool(enabled)) for name,enabled in re.findall(r'<- "(msm_csiphy[0-3])":1 \\[(ENABLED)?\\]',section)]
 assert len(history_links)==4 and any(name=='msm_csiphy1' for name,_ in history_links)
 def set_link(name,enabled):
  subprocess.run(['media-ctl','-d','/dev/media0','-l',f'"{name}":1->"msm_csid0":0[{int(enabled)}]'],check=True,capture_output=True)
 for name,enabled in history_links:
  if enabled:set_link(name,False)
 set_link('msm_csiphy1',True);set_link('msm_csiphy1',False)
 log=root/'capture-private.log' '''.rstrip())
needle="graph_after=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'])"
s=s.replace(needle,"for name,enabled in history_links:\n  if enabled:set_link(name,True)\n "+needle)
s=s.replace('except BaseException:\n if child','except BaseException:\n if child')
# Restore the outer graph even if the worker fails before its regular restore point.
needle="(root/'failure-private.txt').write_text(traceback.format_exc())"
s=s.replace(needle,"failure=traceback.format_exc()\n if 'history_links' in globals():\n  for name,enabled in history_links:\n   try:set_link(name,enabled)\n   except Exception:pass\n "+needle.replace('traceback.format_exc()','failure'))
compile(s,'native-dphy-history','exec');(ROOT/'native-dphy-history.py').write_text(s)
code=r'''
from pathlib import Path
import base64,json,subprocess
r=Path('/var/lib/samurai');assert not (r/'k289-dmi-r3').exists()
script=r/'k289-tools/native-dphy-history.py';assert not script.exists();script.write_bytes(base64.b64decode(WORKER))
with (r/'k289-tools/dphy-worker-private.log').open('xb') as log:
 p=subprocess.Popen(['python3',str(script)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
print(json.dumps(dict(pid=p.pid,start_ticks=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()[19])))
'''.replace('WORKER',repr(base64.b64encode(s.encode()).decode()))
assert not (host.PRIVATE/'dphy-launch-private.json').exists()
q=host.ssh('python3 -',input=code.encode(),timeout=20)
(host.PRIVATE/'dphy-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
poll=(ROOT/'poll-dmi-sequential.py').read_text().replace('dmi-sequential-launch-private','dphy-launch-private').replace('k289-dmi-r2','k289-dmi-r3').replace('dmi-sequential-poll-private','dphy-poll-private').replace('dmi-sequential-capture-validation','dphy-capture-validation').replace('gamma-lut-sequential-validation','gamma-lut-dphy-validation')
(ROOT/'poll-dphy-history.py').write_text(poll)
