"""Run the existing generic 303 control/AGC backend with a measured telephoto profile."""
from pathlib import Path
import hashlib,io,json,shutil,subprocess,tarfile
import host
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'kernel303';P=host.PRIVATE
timing=json.loads((HERE/'delay-analysis-r1-validation.json').read_text())
useful=[r for r in timing['steps'] if r['useful_response']]
assert len(useful)>=7 and {r['control'] for r in useful}=={'exposure','analogue_gain'}
assert all(r['first_observed_changed_offset']==r['first_three_frame_plateau_offset']==2 for r in useful)
assert json.loads((HERE/'delay-capture-r1-validation.json').read_text())['passed']
profile='''%YAML 1.1
---
# Experimental OEM IFE BLS reference, not per-unit calibration.
version: 1
sensor_model: s5k3m5
residual_black_subtraction: 3840
range_normalization: 1.06201171875
sensor_controls:
  width: 2104
  height: 1560
  pixel_rate: 481930000
  line_length: 9648
  frame_length: 1663
  exposure_delay: 2
  gain_delay: 2
'''
(HERE/'s5k3m5-manual.yaml').write_text(profile+'...\n')
agc='''agc:
  relativeLuminanceTarget: 0.16
  AeConstraintMode:
    ConstraintNormal:
      lower:
        qLo: 0.98
        qHi: 1.0
        yTarget: 0.16
      upper:
        qLo: 0.98
        qHi: 1.0
        yTarget: 0.85
  AeExposureMode:
    ExposureNormal:
      exposureTime: [100, 30000, 33200]
      gain: [1.0, 1.0, 16.0]
...
'''
(HERE/'s5k3m5-ae.yaml').write_text(profile+agc)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');stage=SDK/'private/camss306-runtime'
apps={}
for kind in ['joint','ae']:
 source=(OLD/f'{kind}-smoke.cpp').read_text().replace('2.22f','1.0f').replace('1.90f','1.0f')
 if kind=='joint':
  source=source.replace('sequence / 24 % 2 ? 4.0f : 2.0f','sequence / 24 % 2 ? 16.0f : 8.0f')
  source=source.replace('controls.set(controls::AnalogueGain, 2.0f)','controls.set(controls::AnalogueGain, 8.0f)')
 (HERE/f'{kind}-smoke.cpp').write_text(source);(stage/f'{kind}.cpp').write_text(source)
 q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
  '-I/candidate278-r24/usr/include/libcamera','/private/camss306-runtime/'+kind+'.cpp',
  '-L/candidate278-r24/usr/lib','-Wl,-rpath-link,/candidate278-r24/usr/lib','-lcamera','-lcamera-base','-pthread',
  '-o','/private/camss306-runtime/'+kind],capture_output=True,timeout=100)
 (P/f'{kind}-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
 shutil.copyfile(stage/kind,P/f'{kind}-smoke-aarch64-private')
 apps[kind]=dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),
  binary_sha256=hashlib.sha256((P/f'{kind}-smoke-aarch64-private').read_bytes()).hexdigest(),werror=True)
for kind,version in [('joint','r1'),('ae','r2')]:
 previous=json.loads((OLD/f'{kind}-{version}-bundle-validation.json').read_text())
 archive=P.parent/'kernel303'/previous['archive_file']
 assert hashlib.sha256(archive.read_bytes()).hexdigest()==previous['archive_sha256']
 files={}
 with tarfile.open(archive,'r:gz') as tar:
  assert set(tar.getnames())==set(previous['files'])
  for name in tar.getnames():
   data=tar.extractfile(name).read();assert hashlib.sha256(data).hexdigest()==previous['files'][name]['sha256'];files[name]=data
 fixture=P.parent/'kernel305/pipeline-fixture305-aarch64-private'
 assert hashlib.sha256(fixture.read_bytes()).hexdigest()=='32500d1bc563569e59df63e2e1972299fbe06a625b326ba56cd2ec06826700fa'
 files['bin/pipeline-smoke']=(P/f'{kind}-smoke-aarch64-private').read_bytes()
 files['bin/pipeline-fixture']=fixture.read_bytes()
 files['profile/manual.yaml']=(HERE/('s5k3m5-manual.yaml' if kind=='joint' else 's5k3m5-ae.yaml')).read_bytes()
 target=P/f'tele-{kind}-r1-private.tar.gz';assert not target.exists()
 with tarfile.open(target,'w:gz') as tar:
  for name,data in files.items():
   entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o700 if name.startswith(('bin/','proxy/')) else 0o600
   tar.addfile(entry,io.BytesIO(data))
 report=dict(stage=306,kind=kind,archive_file=target.name,archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
  files={n:dict(bytes=len(d),sha256=hashlib.sha256(d).hexdigest()) for n,d in files.items()},
  existing303_generic_ipa_pipeline_reused_byte_exact=True,only_application_fixture_profile_replaced=True,
  not_installed=True,unity_wb_not_awb=True,sensor_delay_measured_useful_steps=len(useful),
  sensor_delay_scope=timing['sensor_mode'])
 (HERE/f'bundle-{kind}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(kind=kind,sha256=report['archive_sha256'],generic_backend_unchanged=True)))
(HERE/'control-applications-validation.json').write_text(json.dumps(dict(stage=306,applications=apps),indent=2)+'\n')
