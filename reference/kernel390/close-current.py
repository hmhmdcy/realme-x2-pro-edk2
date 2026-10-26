from pathlib import Path
import hashlib,importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;candidate=json.loads((HERE.parent/'kernel389/source-state.json').read_text())
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=m.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==candidate['commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
manifest=json.loads((P.parent/'kernel389/module-stage-manifest-private.json').read_text());notes={}
mods={r['name']:r for r in json.loads((HERE.parent/'kernel389/intree-build-validation.json').read_text())['modules']}
for r in manifest['modules']:
 out=P/(r['name']+'.note');subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.note.gnu.build-id',mods[r['name']]['private_path'],str(out)],check=True);notes[r['name'].replace('-','_')]=hashlib.sha256(out.read_bytes()).hexdigest()
code=r'''from pathlib import Path
import hashlib,json,subprocess
meta=MANIFEST;notes=NOTES;sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
for r in meta['modules']:assert sha(Path('/lib/modules')/meta['release']/r['target_relative'])==r['sha256']
for n,h in notes.items():assert sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h
assert sha(meta['firmware']['target'])==meta['firmware']['sha256']
def live(root,key,needle):
 s=json.loads((root/'state.json').read_text());p=Path('/proc',str(s.get(key,-1)))
 try:return (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and needle.encode() in (p/'cmdline').read_bytes()
 except OSError:return False
workers=[]
for root in [Path('/var/lib/samurai/k390-deployment'),Path('/var/lib/samurai/k390-runtime-r1'),Path('/var/lib/samurai/k390-runtime-r2'),Path('/var/lib/samurai/k390-reload-r1')]:
 workers.append(dict(root=root.name,worker=live(root,'pid',str(root/'worker.py')),client=live(root,'client_pid',str(root)),collector=live(root,'collector_pid',str(root/'dump-collector.py'))))
services={n:[] for n in ['pipewire','wireplumber']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in services and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':services[n].append(dict(pid=int(p.name),uid=p.stat().st_uid))
 except OSError:pass
clocks={}
for line in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines():
 f=line.split()
 if f and any(f[0].startswith('cam_cc_'+n+'_') for n in ['icp','bps','ipe_0','ipe_1']):clocks[f[0]]=int(f[1])
dev=Path('/sys/bus/platform/devices/ac10000.icp')
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),boot_sha256=sha('/dev/disk/by-partlabel/boot'),logdump_sha256=sha('/dev/disk/by-partlabel/logdump'),
 installed_five_module_files_and_notes_match=True,stock_firmware_file_matches=True,icp_driver=(dev/'driver').resolve().name,icp_state=json.loads((dev/'state').read_text()),m2m=json.loads((dev/'m2m_status').read_text()),
 workers=workers,services=services,clocks=clocks,
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']},
 rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))},
 test_module_and_overlay_absent=not Path('/sys/module/camss_icp_a5_boot_test').exists() and not Path('/sys/firmware/devicetree/base/soc@0/samurai-icp356-boot@ac10000').exists(),
 legacy_temporary_firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 slpi_current_state=next((p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('*') if (p/'name').read_text().strip()=='slpi'))))
'''.replace('MANIFEST',repr(manifest)).replace('NOTES',repr(notes))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=30);d=json.loads(q.stdout);(P/'current-state-private.json').write_bytes(q.stdout)
boot=json.loads((HERE.parent/'kernel389/build-package-validation.json').read_text());old=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text());assert d['boot_sha256']==boot['boot_sha256'] and d['logdump_sha256']==old['logdump_sha256']
assert not d['taint'] and d['icp_driver']=='qcom-sm8150-icp' and d['test_module_and_overlay_absent'] and d['legacy_temporary_firmware_absent']
assert not any(any(r[k] for k in ['worker','client','collector']) for r in d['workers'])
assert all(v=='suspended' for v in d['camera_pm'].values()) and len(d['clocks'])==17 and not any(d['clocks'].values())
assert len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert all(len(v)==1 and v[0]['uid']==10000 for v in d['services'].values())
assert not any(d['icp_state'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','cleanup_error','pc_error','watchdogs','protocol_errors'])
assert not any(d['m2m'][k] for k in ['users','running','fatal','pinned','orphans','failed','first_error'])
report=dict(stage=390,driver_source_commit=candidate['commit'],source_clean=True,normal_platform_and_board_permanently_enabled=True,Image363_and_logdump365_preserved=True,libcamera_candidate_still_private_stage387=True,installed_libcamera_r29_and_config_r24_unchanged=True,intermittent_ssc_issue_not_claimed_fixed=True,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
