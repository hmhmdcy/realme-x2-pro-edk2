from pathlib import Path
import base64,hashlib,json,shlex,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;action=sys.argv[1] if len(sys.argv)>1 else 'probe';assert action in ['probe','adopt']
manifest=json.loads((P.parent/'kernel389/module-stage-manifest-private.json').read_text());build=json.loads((HERE.parent/'kernel389/intree-build-validation.json').read_text());mods={r['name']:r for r in build['modules']}
notes={}
for n in ['qcom-camss','qcom-camss-icp-a5-core','camss-icp-a5-m2m','v4l2-mem2mem','videobuf2-dma-sg']:
 path=P/(n+'.note');subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','--only-section=.note.gnu.build-id',mods[n]['private_path'],str(path)],check=True);notes[n.replace('-','_')]=hashlib.sha256(path.read_bytes()).hexdigest()
ns={};exec((HERE.parent/'kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns);nodes=ns['fdt_nodes']((P.parent/'kernel389/samurai389-private.dtb').read_bytes())
expected={p:{k:base64.b64encode(v).decode() for k,v in props.items()} for p,props in nodes.items() if p=='/soc@0/icp@ac10000' or p.startswith('/reserved-memory/reservation-icp-')}
code=r'''from pathlib import Path
import base64,hashlib,json,os
root=Path('/var/lib/samurai/k390-deployment');marker=Path('/etc/samurai-rootfs-release')
def sha(p):return hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
dt=Path('/sys/firmware/devicetree/base');dev=Path('/sys/bus/platform/devices/ac10000.icp')
meta=MANIFEST;expected=EXPECTED
d=dict(rootfs_marker=marker.exists(),old_deployment_root_present=root.exists(),kernel=os.uname().release,version=os.uname().version,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),taint=int(Path('/proc/sys/kernel/tainted').read_text()),icp_device=dev.exists(),icp_driver=(dev/'driver').resolve().name if (dev/'driver').exists() else None)
if marker.exists() and root.exists():
 d['same_as_old_boot']=Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'boot-id-private.txt').read_bytes()
 d['boot_sha256']=sha('/dev/disk/by-partlabel/boot');d['logdump_sha256']=sha('/dev/disk/by-partlabel/logdump')
 d['dt_matches']=all((dt/p.lstrip('/')/k).exists() and (dt/p.lstrip('/')/k).read_bytes()==base64.b64decode(v) for p,props in expected.items() for k,v in props.items())
 d['module_files_match']=all(sha(Path('/lib/modules')/meta['release']/r['target_relative'])==r['sha256'] for r in meta['modules'])
 d['firmware_file_match']=sha(meta['firmware']['target'])==meta['firmware']['sha256']
 d['module_notes']={n:sha(Path('/sys/module',n,'notes/.note.gnu.build-id')) if Path('/sys/module',n).exists() else None for n in NOTES}
 d['state']=json.loads((dev/'state').read_text()) if (dev/'state').exists() else None
 d['m2m']=json.loads((dev/'m2m_status').read_text()) if (dev/'m2m_status').exists() else None
 d['pm']={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci'] if Path('/sys/bus/platform/devices',n).exists()}
 d['temporary_test_absent']=not Path('/sys/module/camss_icp_a5_boot_test').exists() and not (dt/'soc@0/samurai-icp356-boot@ac10000').exists()
 d['services']={n:[] for n in ['pipewire','wireplumber','greetd','ModemManager']}
 for p in Path('/proc').glob('[0-9]*'):
  try:
   n=(p/'comm').read_text().strip()
   if n in d['services'] and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':d['services'][n].append(int(p.name))
  except OSError:pass
print(json.dumps(d))
'''.replace('MANIFEST',repr(manifest)).replace('EXPECTED',repr(expected)).replace('NOTES',repr(notes))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=25,check=False)
attempt=1
while (P/('postboot-probe-'+str(attempt)+'-private.json')).exists():attempt+=1
if q.returncode:
 (P/('postboot-ssh-'+str(attempt)+'-private.log')).write_bytes(q.stdout+q.stderr);print(json.dumps(dict(stage=390,connected=False,ssh_exit=q.returncode,no_transition_repeated=True)));sys.exit(0)
d=json.loads(q.stdout);(P/('postboot-probe-'+str(attempt)+'-private.json')).write_bytes(q.stdout)
if action=='adopt':
 boot=json.loads((HERE.parent/'kernel389/build-package-validation.json').read_text());old=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text())
 assert d['rootfs_marker'] and d['old_deployment_root_present'] and not d['same_as_old_boot'] and d['kernel']==manifest['release'] and d['version'].startswith('#363 ')
 assert d['boot_sha256']==boot['boot_sha256'] and d['logdump_sha256']==old['logdump_sha256']
 assert d['dt_matches'] and d['module_files_match'] and d['firmware_file_match'] and d['module_notes']==notes and not d['taint']
 assert d['icp_driver']=='qcom-sm8150-icp' and d['temporary_test_absent'] and d['state']['engine_dma_capable']
 assert not d['state']['cpu_release_attempted'] and d['m2m']['registered'] and not d['m2m']['jobs']
 guard='/var/lib/samurai/k390-active/boot-id-private.txt'
 adopt="""from pathlib import Path
import os
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOTID
root=Path('/var/lib/samurai/k390-active');assert not root.exists();root.mkdir(mode=0o700)
p=root/'boot-id-private.txt'
with p.open('xb') as f:f.write(Path('/proc/sys/kernel/random/boot_id').read_bytes());f.flush();os.fsync(f.fileno())
print('New390 boot identity recorded.')
""".replace('BOOTID',repr(d['boot_id']))
 print(host.raw_ssh('python3 -c '+shlex.quote(adopt),timeout=20).stdout.decode())
 (P/'postboot-adoption-private.json').write_text(json.dumps(dict(guard_path=guard,boot_id=d['boot_id'],kernel=d['kernel']),indent=2)+'\n')
 report=dict(stage=390,boot389_readback_exact=True,logdump365_and_Image363_preserved=True,actual_dt_and_five_modules_match=True,formal_icp_driver_bound=True,test_module_and_temporary_overlay_absent=True,firmware_not_started_in_probe=True,normal_m2m_registered=True,pm=d['pm'],taint=d['taint'],passed=True)
 (HERE/'postboot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
else:
 public={k:v for k,v in d.items() if k not in ['boot_id','module_notes','version']}
 if 'services' in public:public['services']={k:len(v) for k,v in public['services'].items()}
 print(json.dumps(dict(stage=390,connected=True,**public),indent=2))
