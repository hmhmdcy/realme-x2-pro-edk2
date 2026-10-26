"""Read current Phosh files/services before preparing any package replacement."""
from pathlib import Path
import gzip
import importlib.util
import io
import json
import os
import tarfile

HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/e/edk2-samurai-out/charging-ui-audit-20261023/phosh-original-rollback-501')
OUT = BASE / 'live-preflight-02-private'
proof = json.loads((HERE / 'verified-result.json').read_bytes())
spec = importlib.util.spec_from_file_location('strict_original_key', HERE.parent.parent /
    'charging-session-20261023/icon-capture-image501-candidate/transport.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
import hashlib
sha = lambda raw: hashlib.sha256(raw).hexdigest()
expected = {}
for pkg in proof['packages']:
    path = BASE / pkg['filename']
    if sha(path.read_bytes()) != pkg['sha256']:
        raise RuntimeError('rollback input changed')
    raw = gzip.decompress(path.read_bytes())
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:', ignore_zeros=True) as archive:
        for member in archive:
            if member.isfile() and member.name.startswith('usr/'):
                expected['/' + member.name] = {'sha256': sha(archive.extractfile(member).read()),
                                              'mode': member.mode & 0o7777}
body = r'''
from pathlib import Path
import hashlib,json,os,subprocess
expected=EXPECTED
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
guard=Path('/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt').read_text().strip()
if boot!=guard or not os.uname().version.startswith('#501 '):
 raise RuntimeError('not the adopted Image501 boot')
files={}
for name,want in expected.items():
 p=Path(name)
 try:
  s=p.stat(); digest=hashlib.sha256(p.read_bytes()).hexdigest()
  files[name]={'sha256':digest,'mode':s.st_mode&0o7777,'original_bytes':digest==want['sha256'],'original_mode':s.st_mode&0o7777==want['mode']}
 except Exception as error:files[name]={'error':repr(error)}
db=Path('/lib/apk/db/installed').read_text()
packages=[b for b in db.split('\n\n') if '\no:phosh\n' in b]
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  comm=(p/'comm').read_text().strip()
  if comm not in ('phosh','phoc','greetd','gnome-session-b'):continue
  env={}
  for item in (p/'environ').read_bytes().split(b'\0'):
   k,sep,v=item.partition(b'=')
   if sep and k.decode(errors='replace') in ('HOME','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','WAYLAND_DISPLAY','XDG_CURRENT_DESKTOP'):
    env[k.decode()]=v.decode(errors='replace')
  processes.append({'pid':int(p.name),'comm':comm,'exe':os.readlink(p/'exe'),'environment':env})
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
def command(argv):
 q=subprocess.run(argv,capture_output=True,timeout=8)
 return {'rc':q.returncode,'stdout':q.stdout.decode(errors='replace'),'stderr':q.stderr.decode(errors='replace')}
result={'boot':boot,'uname':Path('/proc/version').read_text().strip(),'files':files,'packages':packages,
 'processes':processes,'greetd':command(['rc-service','greetd','status']),
 'upower':command(['upower','-d']),
 'greetd_config':Path('/etc/greetd/samurai-phosh.toml').read_text(),
 'desktop_config':Path('/etc/conf.d/greetd').read_text()}
result['all_original_files']=all(r.get('original_bytes') and r.get('original_mode') for r in files.values())
print(json.dumps(result))
'''.replace('EXPECTED', repr(expected))
os.umask(0o077)
OUT.mkdir(mode=0o700)
(OUT / 'executed-readonly-private.py').write_text(body)
q = transport.raw_ssh('python3 -', input=body.encode(), timeout=40, check=False)
(OUT / 'stdout-private.json').write_bytes(q.stdout)
(OUT / 'stderr-private.txt').write_bytes(q.stderr)
(OUT / 'terminal-private.json').write_text(json.dumps({'returncode': q.returncode}))
q.check_returncode()
data = json.loads(q.stdout)
summary = {'passed': data['all_original_files'] and data['greetd']['rc'] == 0,
           'original_package_file_count': len(expected), 'all_original_files': data['all_original_files'],
           'mismatches': [name for name, row in data['files'].items()
                          if not (row.get('original_bytes') and row.get('original_mode'))],
           'process_names': [row['comm'] for row in data['processes']],
           'upower_query_rc': data['upower']['rc'], 'phone_mutations': False,
           'executed_source_sha256': sha(body.encode()), 'raw_sha256': sha(q.stdout)}
(HERE / 'live-preflight-result.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
