"""Add real export-FD/VMA ownership checks and bounded delayed-fput gates."""
from pathlib import Path
import ast,json
HERE=Path(__file__).resolve().parent
helper='''
def wait_exports():
 deadline=time.monotonic()+5
 while True:
  current=read_m2m()
  if not current['owner_refs']:return current
  if time.monotonic()>deadline:raise RuntimeError('Export owner still pinned; retain platform and DMA domain')
  time.sleep(.02)
'''
lifetime='''
 (ROOT/'export-lifetime-client').chmod(0o700)
 with (ROOT/'export-client.log').open('xb') as output:
  client=subprocess.Popen([str(ROOT/'export-lifetime-client'),'/dev/'+nodes[0].name,str(ROOT)],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT)
  save('export-client-running',export_client_pid=client.pid)
  def held(marker):
   deadline=time.monotonic()+5
   while not (ROOT/marker).exists():
    assert client.poll() is None,'Export client exited before '+marker
    assert time.monotonic()<deadline,'Export client marker timeout: '+marker
    time.sleep(.01)
   current=read_m2m()
   assert not any(current[k] for k in ['users','running','jobs','pinned','orphans'])
   assert current['owner_refs']>0,'Export no longer pins real platform owner'
   assert int(Path('/sys/module',test,'refcnt').read_text())>=current['owner_refs']
   observation[marker.replace('-','_')]=current
   save(marker)
  held('export-held')
  (ROOT/'close-export-fd').touch()
  held('mmap-only-held')
  (ROOT/'release-export-mmap').touch()
  observation['export_client_exit']=client.wait(timeout=8)
 assert observation['export_client_exit']==0
 assert (ROOT/'export-released').exists()
 observation['export_after_release']=wait_exports()
 observation['export_fd_and_vma_lifetime_passed']=True
 save('export-lifetime-complete')
'''
for name in ['m2m-worker.py','pipeline-worker.py']:
 p=HERE/name;s=p.read_text()
 assert 'def wait_exports' not in s
 s=s.replace('\ndef read_result()',helper+'\ndef read_result()',1)
 s=s.replace('after=read_m2m()','after=wait_exports()').replace('final=read_m2m();result=read_result()','final=wait_exports();result=read_result()')
 s=s.replace("status=read_m2m();observation['m2m_before_removal']=status","status=wait_exports();observation['m2m_before_removal']=status")
 s=s.replace("['users','running','pinned','orphans']) and releasable", "['users','running','pinned','orphans','owner_refs']) and releasable")
 if name=='m2m-worker.py':
  needle=" (ROOT/'m2m-client').chmod(0o700)";assert needle in s;s=s.replace(needle,lifetime+needle)
 ast.parse(s);p.write_text(s)
print(json.dumps(dict(stage=388,native_export_lifetime_client_added=True,both_workers_wait_for_owner_refs_zero=True,passed=True)))
