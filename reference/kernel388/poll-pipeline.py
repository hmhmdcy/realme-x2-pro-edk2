from pathlib import Path
import base64,json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r\d+',run)
root='/var/lib/samurai/k388-pipeline-'+run
code=r'''
from pathlib import Path
import base64,json
root=Path(ROOT);meta=json.loads((root/'manifest.json').read_text());state=json.loads((root/'state.json').read_text())
assert b'realme,samurai\0' in Path('/sys/firmware/devicetree/base/compatible').read_bytes()
def live(pid,name):
 p=Path('/proc')/str(pid)
 try:return str(root/name).encode() in (p/'cmdline').read_bytes() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
 except OSError:return False
same=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path(meta['boot_guard']).read_bytes()
files={}
for path in root.iterdir():
 if path.is_file() and (path.name in ['ipe-output-private.nv12','collector-ready.json','collector-result.json','a5-dump-decoded-private.json','sfr-private.txt','worker.log','collector.log','failure.log','kernel-log-private.txt'] or path.name.startswith('a5-devcd') and path.suffix=='.bin' or path.name.startswith('firmware-') or path.name=='snapshot-result-private.json' or path.name.startswith('case-') or path.name.startswith('client-private.') or path.suffix=='.log' or path.name.startswith('camera-')):
  assert path.stat().st_size<=(64*1024*1024 if path.name=='ipe-output-private.nv12' else 2*1024*1024);files[path.name]=base64.b64encode(path.read_bytes()).decode()
print(json.dumps(dict(state=state,same_boot=same,client_process_live=live(state.get('client_pid',-1),'camera-client.py'),worker_live=live(state['pid'],'worker.py'),collector_live=live(state.get('collector_pid',-1),'snapshot-collector.py'),files_b64=files)))
'''.replace('ROOT',repr(root))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=90);(P/('observation-'+run+'-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout)
out=P/('collected-'+run);out.mkdir(exist_ok=True)
for name,value in d['files_b64'].items():(out/name).write_bytes(base64.b64decode(value))
s=d['state'];keys=['ready_result','libcamera_pipeline_client_passed','m2m_before','m2m_after_client','m2m_final','m2m_before_removal','m2m_cleanup_retry_result','client_exit','client_live','client_report','video_node','media_node','adapter_absent','helper_absent','m2m_video_absent','image_control_completion_passed','ipe_io_config_passed','ipe_session_lifecycle_passed','binding_returned_before_cpu_release','held_window_returned','snapshot_saved','code_page_match','cleanup_attempted','terminal','phase','passed','firmware_handshake_passed','diagnostic_completed','firmware_failure_observed','sfr_recovered','collector_armed_before_boot_module','device_result','taint_before','taint_after','core_absent','test_absent','temporary_dt_nodes_absent','temporary_firmware_removed','clocks_before','clocks_after','camss_before','camss_after','error','cleanup_error','requires_cleanup_attention']
report=dict(stage=388,run=run,client_process_live=d['client_process_live'],same_boot=d['same_boot'],worker_live=d['worker_live'],collector_live=d['collector_live'],**{k:s[k] for k in keys if k in s})
if 'collector_result' in s:report['collector_result']={k:v for k,v in s['collector_result'].items() if k not in ['raw_private_path','pid']}
report['new_relevant_fault_count']=len(s.get('new_relevant_faults',[]))
if s['terminal']:
 for name in ['pipeline-runtime-'+run+'-validation.json','pipeline-runtime-validation.json']:(HERE/name).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
