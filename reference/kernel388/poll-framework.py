from pathlib import Path
import base64,json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent;run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run)
root='/var/lib/samurai/k388-framework-'+run
code=r'''from pathlib import Path
import base64,json
root=Path(ROOT);proof=json.loads((root/'proof.json').read_text())
def alive(pid,needle):
 try:
  p=Path('/proc',str(pid));return needle.encode() in (p/'cmdline').read_bytes() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
 except OSError:return False
states={};live={};files={}
for key,folder in [('framework',root),('native',root/'native'),('pipeline',root/'pipeline')]:
 if not (folder/'state.json').exists():continue
 s=json.loads((folder/'state.json').read_text());states[key]=s;live[key]=alive(s['pid'],str(folder/'worker.py'))
 for path in folder.iterdir():
  if path.is_file() and path.stat().st_size<=2097152 and (path.suffix in ['.log','.txt'] or path.name in ['state.json','client-private.json','camera-state.json','collector-result.json','collector-ready.json']):files[str(path.relative_to(root))]=base64.b64encode(path.read_bytes()).decode()
print(json.dumps(dict(states=states,live=live,same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(proof['boot_guard']).read_bytes(),files=files)))
'''.replace('ROOT',repr(root))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=40);d=json.loads(q.stdout);out=host.PRIVATE/('framework-collected-'+run);out.mkdir(exist_ok=True)
(host.PRIVATE/('framework-observation-'+run+'-private.json')).write_bytes(q.stdout)
for name,value in d['files'].items():
 p=out/name;p.parent.mkdir(exist_ok=True);p.write_bytes(base64.b64decode(value))
report=dict(stage=388,run=run,same_boot=d['same_boot'],worker_live=d['live'],states={})
for name,s in d['states'].items():
 keys=['phase','terminal','passed','failure','restore_error','service_restore_error','error','cleanup_error','requires_cleanup_attention','original_framework_restored','new_sg_loaded','taint','taint_after','export_fd_and_vma_lifetime_passed','export_client_exit','client_exit','core_absent','adapter_absent','test_absent','helper_absent','m2m_after_client','installed_captures','camera_pm']
 report['states'][name]={k:s[k] for k in keys if k in s}
 if 'services' in s:report['states'][name]['service_counts']={k:len(v) for k,v in s['services'].items()}
 if 'new_relevant_faults' in s:report['states'][name]['new_fault_count']=len(s['new_relevant_faults'])
 for key in ['export_held','mmap_only_held','export_after_release']:
  if key in s:report['states'][name][key]={k:s[key][k] for k in ['users','running','jobs','owner_refs']}
if d['states'].get('framework',{}).get('terminal'):
 report['passed']=d['states']['framework']['passed'] and d['same_boot'] and not any(d['live'].values())
 (HERE/('framework-runtime-'+run+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
 (HERE/'framework-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
