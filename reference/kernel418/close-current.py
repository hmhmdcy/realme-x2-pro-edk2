"""Close the temporary test and verify the restored normal driver ownership."""
from pathlib import Path
import importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
runtime=json.loads((HERE/'runtime-validation.json').read_text());assert runtime['state']['passed'] and json.loads((HERE/'hardware-validation.json').read_text())['passed']
assert not any(runtime[k] for k in ['worker_live','client_live','collector_live'])
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';expected=json.loads((HERE.parent/'kernel417/source-state.json').read_text());assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==expected['commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
meta=json.loads((P/'manifest-private.json').read_text())
code=r'''from pathlib import Path
import hashlib,json
meta=META;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
assert all(sha(n)==h for n,h in meta['normal_files'].items())
assert all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
for module,kind in [('qcom_camss_icp_a5_core','normal_core'),('camss_icp_a5_m2m','normal_adapter')]:assert sha('/sys/module/'+module+'/notes/.note.gnu.build-id')==meta[kind+'_note_sha256']
assert sha('/sys/module/qcom_camss/notes/.note.gnu.build-id')==meta['camss_note_sha256']
assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_cc_mode').exists()
assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_gamma_mode').exists()
assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_ltm_mode').exists()
assert not Path('/sys/module/camss_icp_a5_m2m/parameters/test_chain_mode').exists() and not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
root=Path('/var/lib/samurai/k418-libcamera-r2');state=json.loads((root/'state.json').read_text());live=[]
for key,names in [('pid',['worker.py']),('client_pid',['ipe-smoke','pipeline-fixture']),('collector_pid',['dump-collector.py'])]:
 p=Path('/proc',str(state.get(key,-1)))
 try:active=(p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and any(str(root/n).encode() in (p/'cmdline').read_bytes() for n in names)
 except OSError:active=False
 if active:live.append(key)
services={n:[] for n in ['pipewire','wireplumber']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in services and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':services[n].append(dict(pid=int(p.name),uid=p.stat().st_uid))
 except OSError:pass
clocks={}
for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
 fields=line.split()
 if fields and any(fields[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):clocks[fields[0]]=int(fields[1])
dev=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(same_guard394=True,normal395_files_and_loaded_notes_match=True,private_profiles_unchanged=True,test_parameters_absent=True,transaction_terminal=state['terminal'],transaction_live=live,services=services,clocks=clocks,m2m=json.loads((dev/'m2m_status').read_text()),core=json.loads((dev/'state').read_text()),taint=int(Path('/proc/sys/kernel/tainted').read_text()),camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']},rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))})))
'''.replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);(P/'current-state-private.json').write_bytes(q.stdout)
assert d['m2m']['jobs']==d['m2m']['completed']==d['m2m']['direct_completed']==48 and d['m2m']['starts']==d['m2m']['stops']==4
assert d['taint']==512 and not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert not any(d['core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','cleanup_error','pc_error','watchdogs','protocol_errors'])
assert len(d['clocks'])==17 and not any(d['clocks'].values()) and len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert all(v=='suspended' for v in d['camera_pm'].values()) and all(len(v)==1 and v[0]['uid']==10000 for v in d['services'].values()) and d['transaction_terminal'] and not d['transaction_live']
report=dict(stage=418,candidate_source_commit=expected['commit'],candidate_source_clean=True,candidate_permanently_installed=False,installed_core_stage=395,installed_adapter_stage=393,generic20_conversion_pair_verified=True,media_request_iq_verified=True,known417_r2_warning_taint_retained=True,hardware_scope="Actual candidate CamssIpe16 nonzero frames equal reference,4 wrapper cancels;camera pipeline81 request frames inclfour48/dual6/isolated27 andRAW-only6 noIPE;formal395/393 restored48.Numerical IPA payloads remain bypass.",factory_rgb_matrices_ready_for_default=False,full_goal_active=True,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['m2m','core','clocks','rails','camera_pm']},indent=2))
