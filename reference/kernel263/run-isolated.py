from pathlib import Path
import json,shlex,sys
import host
R=Path(__file__).parent;mode=int(sys.argv[1]);assert mode in [6000002,6000003,6000004,6000005,6000006,6000008]
if mode==6000005:
 setup="from pathlib import Path;import sys;base=Path('/usr/lib/spa-0.2');out=Path('/var/lib/samurai/k263-spa');assert not out.exists();out.mkdir(mode=0o755);[(out/p.name).symlink_to(p,target_is_directory=p.is_dir()) for p in base.iterdir() if p.name!='libcamera'];d=out/'libcamera';d.mkdir(mode=0o755);f=d/'libspa-libcamera.so';f.write_bytes(sys.stdin.buffer.read());f.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(setup),input=(host.PRIVATE/'libspa-libcamera-busy-candidate.so').read_bytes())
if mode==6000008:
 setup="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k263-spa/libcamera/libspa-libcamera.so');assert p.exists();p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(setup),input=(host.PRIVATE/'libspa-libcamera-automatic-candidate.so').read_bytes())
for name in ['isolated-runner.py','pipewire263.conf','wireplumber263-off.conf','wireplumber263-on.conf']:
 setup="from pathlib import Path;import sys;p=Path('/var/lib/samurai/k263-tools')/"+repr(name)+";p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"
 host.ssh('python3 -c '+shlex.quote(setup),input=(R/name).read_bytes())
# Add the remote node's advertised policy to the private probe metadata.
probe=(R/'immutability-probe.py').read_text()
probe=probe.replace("held=[]", "props=devices[0].get_properties();data['remote_node_reliable']=str(props.get_value('node.reliable')) if props.has_field('node.reliable') else None\nheld=[]")
host.ssh('python3 -c '+shlex.quote("from pathlib import Path;import sys;p=Path('/var/lib/samurai/k263-tools/pipewire-probe.py');p.write_bytes(sys.stdin.buffer.read());p.chmod(0o644)"),input=probe.encode())
r=host.ssh('python3 - '+str(mode),input=(R/'native-isolated.py').read_bytes(),timeout=65,check=False)
(host.PRIVATE/('isolated-'+str(mode)+'-private.log')).write_bytes(r.stdout+r.stderr)
d=json.loads(r.stdout);(R/('isolated-'+str(mode)+'-validation.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
