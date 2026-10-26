"""Render a read-only trace capability query; live requires a fresh camera handoff."""
from pathlib import Path
import argparse,ast,datetime,hashlib,importlib.util,json,shlex
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('guard449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mount.mounted_build()
parser=argparse.ArgumentParser()
parser.add_argument('--handoff',type=Path)
parser.add_argument('--baseline',type=Path)
parser.add_argument('--live',action='store_true')
args=parser.parse_args()
assert bool(args.handoff)==bool(args.baseline)
assert not args.live or args.handoff
private=Path('/mnt/e/edk2-samurai-out/kernel457');private.mkdir(mode=0o700,exist_ok=True)
handoff=None;baseline=None
if args.handoff:
 handoff=json.loads(args.handoff.read_text());baseline=json.loads(args.baseline.read_text())
 assert handoff['schema']=='samurai-camera-handoff-v1' and handoff['window_owner']=='camera' and handoff['fresh_preflight_verified'] is True
 assert hashlib.sha256(args.baseline.read_bytes()).hexdigest()==handoff['formal_baseline_sha256']
 issued=datetime.datetime.fromisoformat(handoff['issued_at_utc'].replace('Z','+00:00'))
 assert issued.tzinfo and 0<=(datetime.datetime.now(datetime.timezone.utc)-issued).total_seconds()<600
helper=HERE.parent/'kernel451/capture-body-comparison.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='a65f6326fc2366e8bd0b225c1399c386d0aa86f83260d28e57e02ed04e279fff'
tree=ast.parse(helper.read_text())
definitions='\n\n'.join(ast.get_source_segment(helper.read_text(),n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['sha','charging'])
source='from pathlib import Path\nimport hashlib,json,os,re,runpy\n'+definitions+'\n'
source+='handoff='+repr(handoff)+'\nbaseline='+repr(baseline)+'\n'
source+='''
assert handoff is not None and baseline is not None, 'FRESH_HANDOFF_REQUIRED'
assert Path(handoff['boot_guard_path']).read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert sha('/usr/lib/libcamera.so.0.7.2')==handoff['formal_library_sha256']
assert charging()==handoff['charging']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for name,digest in baseline['notes'].items():assert sha(Path('/sys/module',name,'notes/.note.gnu.build-id'))==digest
roots=[path for path in [Path('/sys/kernel/tracing'),Path('/sys/kernel/debug/tracing')] if (path/'available_events').is_file()]
assert roots, 'Tracefs capability not exposed; do not mount or change global tracing here'
root=roots[0];available=set((root/'available_events').read_text().split())
wanted=['vb2:vb2_qbuf','vb2:vb2_buf_queue','vb2:vb2_buf_done','vb2:vb2_dqbuf','v4l2:v4l2_qbuf','v4l2:v4l2_dqbuf','irq:irq_handler_entry','irq:irq_handler_exit']
formats={name:(root/'events'/name.replace(':','/')/'format').read_text() for name in wanted if name in available}
videos={path.name:dict(name=(path/'name').read_text().strip(),dev=(path/'dev').read_text().strip()) for path in Path('/sys/class/video4linux').glob('video*')}
print(json.dumps(dict(tracefs=str(root),tracing_on=(root/'tracing_on').read_text().strip(),trace_clock=(root/'trace_clock').read_text().strip(),instances_supported=(root/'instances').is_dir(),existing_instances=sorted(p.name for p in (root/'instances').iterdir()) if (root/'instances').is_dir() else [],wanted_events={name:name in available for name in wanted},formats=formats,video_nodes=videos,interrupts=Path('/proc/interrupts').read_text(),online_cpus=Path('/sys/devices/system/cpu/online').read_text().strip(),charging_before=handoff['charging'],charging_after=charging(),phone_changed=False)))
'''
ast.parse(source)
for node in ast.walk(ast.parse(source)):
 assert not (isinstance(node,ast.Attribute) and node.attr in ['write_text','write_bytes','mkdir','unlink','chmod','chown','symlink_to','Popen','kill','killpg'])
(private/'trace-capability-query-private.py').write_text(source)
if args.live:
 output=private/'trace-capabilities-private.json';assert not output.exists(),'Keep prior probe and use a newly named collection'
 spec=importlib.util.spec_from_file_location('transport451',HERE.parent/'kernel451/host.py')
 host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
 result=host.raw_ssh('python3 -B -c '+shlex.quote(source),timeout=25);result.check_returncode()
 data=json.loads(result.stdout);assert data['charging_before']==data['charging_after']
 output.write_bytes(result.stdout)
 print(json.dumps(dict(probed=True,phone_changed=False,events=data['wanted_events'],instances_supported=data['instances_supported'],passed=True)))
else:
 print(json.dumps(dict(rendered=True,phone_accessed=False,phone_writes_absent=True,fresh_handoff_required_for_live=True,passed=True)))
