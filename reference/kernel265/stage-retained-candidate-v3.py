"""Stage a verified candidate pair for isolated application tests, without installation."""
from pathlib import Path
import hashlib,io,json,shlex,subprocess,tarfile
import host
R=Path(__file__).parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
unit=json.loads((R/'retained-busy-v2-unit-validation.json').read_text());assert unit['real_pipewire_imported_map_without_default_map'] and unit['positive']['fd_growth']==0
core=host.PRIVATE/'libpipewire-map-lookup.so';plugin=host.PRIVATE/'libgstpipewire-retained-busy-v3.so'
def symbols(p):
 q=subprocess.run(['chroot',str(SDK),'nm','-D','--defined-only','/'+str(p.relative_to(SDK))],capture_output=True,check=True)
 return {line.split()[-1] for line in q.stdout.decode().splitlines() if line.split()}
old=SDK/'work/pipewire263-broadcast/build/src/pipewire/libpipewire-0.3.so.0.1609.0'
# The independent immutable stage264 binary is the ABI baseline.
baseline=SDK/'work/pipewire265-retained-busy/core-map-lookup/baseline-264-v3.so';assert not baseline.exists()
baseline.write_bytes((host.PRIVATE.parent/'kernel264/libpipewire-binding-reset.so').read_bytes())
new=SDK/'work/pipewire265-retained-busy/core-map-lookup/libpipewire-0.3.so.0.1609.0'
previous=symbols(baseline);current=symbols(new);assert previous<=current and 'pw_mempool_find_map' in current
helper=(SDK/'work/pipewire265-retained-busy/source/gstpipewirepool.c').read_text()
helper=helper[helper.index('gboolean\ngst_pipewire_pool_init_busy'):helper.index('\nvoid gst_pipewire_pool_wrap_buffer')]
assert hashlib.sha256(helper.encode()).hexdigest()==unit['actual_candidate_helpers_sha256']
assert 'pw_mempool_find_map' in helper
payload={'libpipewire-0.3.so.0.1609.0':core.read_bytes(),'libgstpipewire.so':plugin.read_bytes()}
checks={n:hashlib.sha256(v).hexdigest() for n,v in payload.items()}
assert checks['libpipewire-0.3.so.0.1609.0']==json.loads((R/'mapped-region-core-build-validation.json').read_text())['core_sha256']
assert checks['libgstpipewire.so']==json.loads((R/'retained-busy-v3-build-validation.json').read_text())['plugin_sha256']
b=io.BytesIO()
with tarfile.open(fileobj=b,mode='w') as t:
 for name,data in payload.items():
  info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;t.addfile(info,io.BytesIO(data))
code=r'''
from pathlib import Path
import hashlib,io,json,os,sys,tarfile
out=Path('/var/lib/samurai/k265-candidate-v3');assert not out.exists();out.mkdir(mode=0o755)
checks=json.loads(sys.argv[1])
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read())) as t:
 assert set(t.getnames())==set(checks)
 for name,digest in checks.items():
  data=t.extractfile(name).read();assert hashlib.sha256(data).hexdigest()==digest
  p=out/name;p.write_bytes(data);p.chmod(0o644)
(out/'libpipewire-0.3.so.0').symlink_to('libpipewire-0.3.so.0.1609.0')
print(json.dumps(dict(staged=True,sha256=checks,system_installation_changed=False)))
'''
q=host.ssh('python3 -c '+shlex.quote(code)+' '+shlex.quote(json.dumps(checks)),input=b.getvalue(),timeout=25)
report=json.loads(q.stdout);report.update(stage=265,abi_symbols_removed=sorted(previous-current),extra_exports=sorted(current-previous),real_imported_map_unit_passed=True)
(R/'candidate-stage-v3-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

