"""Verify current four-camera idle state, deployed payloads, and normal desktop maps."""
from pathlib import Path
import ast,json
import host
R=Path(__file__).resolve().parent
t=ast.parse((R.parent/'kernel270/final-health.py').read_text());n=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets));code=ast.literal_eval(n.value)
code=code[:code.index('manifest=')]+code[code.index('report=dict'):]
for a,b in [("['7-0010','8-002d','9-0010']","['6-0010','7-0010','8-002d','9-0010']"),
 ("('cam-front-','cam-rear-','cam-tele-')","('cam-front-','cam-rear-','cam-tele-','cam-main-')"),
 ("['cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']","['cam_cc_mclk0_clk','cam_cc_mclk1_clk','cam_cc_mclk2_clk','cam_cc_mclk3_clk']"),
 ('k270-work','k273-work'),('stage=270','stage=273')]:assert a in code,a;code=code.replace(a,b)
code=code[:code.rindex('print(json.dumps(report))')]+r'''
out=Path('/var/lib/samurai/k273-main-transaction');manifest=json.loads((out/'new-manifest-private.json').read_text());checked=0
for pkg in manifest['packages']:
 for name,item in pkg['files'].items():
  p=Path('/')/name
  if item['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==item['target']
  else:assert not p.is_symlink() and sha(p)==item['sha256'] and (p.stat().st_mode&0o777)==item['mode']
  checked+=1
tree=Path('/usr/lib/modules')/os.uname().release;old=json.loads((out/'module-inventory-before-private.json').read_text());now={str(p.relative_to(tree)):sha(p) for p in tree.rglob('*.ko')}
assert len(now)==775 and all(now[n]==v for n,v in old.items()) and set(now)-set(old)=={'kernel/drivers/media/i2c/s5kgw1.ko'}
maps={}
for item in report['services']:
 if item['comm'] in ['pipewire','wireplumber']:
  text=Path('/proc',str(item['pid']),'maps').read_text();assert not any('/var/lib/samurai/k' in line and '.so' in line for line in text.splitlines())
  assert not any('libcamera' in line and '(deleted)' in line for line in text.splitlines())
  maps[item['comm']]=dict(normal_library_paths=True,camera_core_mapped='/usr/lib/libcamera.so.' in text,spa_mapped='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so' in text)
assert set(maps)=={'pipewire','wireplumber'} and maps['wireplumber']['spa_mapped']
ssc=json.loads(Path('/run/samurai-ssc/state.json').read_text())
report.update(current49_payload_records_verified=checked,existing774_modules_unchanged=True,package_versions={p['name']:p['version'] for p in manifest['packages']},
 desktop_library_maps=maps,ssc_started=ssc.get('started'),ssc_failed_attempt_retained=ssc.get('attempted') and not ssc.get('started'),
 rotation_and_normal_desktop_dependency_start_pending=True)
print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=35);(host.PRIVATE/'final-health-private.json').write_bytes(q.stdout)
d=json.loads(q.stdout);d.pop('dmesg');d.pop('package_database_sha256')
d['camera_idle_passed']=d['taint']==0 and not any(d['faults'].values()) and not d['camera_clients'] and all(v=='suspended' for v in d['runtime'].values()) and len(d['rails'])==9 and all(v['state']=='disabled' and v['num_users']=='0' for v in d['rails'].values()) and not any(d['mclk_enable_counts'].values())
assert d['camera_idle_passed'] and d['package_count']==961 and d['module_count']==775
(R/'final-health-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
