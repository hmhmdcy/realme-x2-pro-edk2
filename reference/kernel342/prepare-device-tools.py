"""Prepare the package transaction and a focused installed-feature capture."""
from pathlib import Path
import io,json,math,shutil,struct,tarfile
import host

HERE=Path(__file__).resolve().parent;P=host.PRIVATE
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')

def archive(target,files,repository=None):
 temporary=target.with_suffix(target.suffix+'.tmp')
 with tarfile.open(temporary,'w:gz') as tar:
  for name,source in files.items():tar.add(source,arcname=name)
  if repository:
   for source in repository.rglob('*'):tar.add(source,arcname='repository/'+source.relative_to(repository).as_posix(),recursive=False)
 temporary.replace(target)

# Reuse the proven package-only transaction; the kernel/module are unchanged.
s=(HERE.parent/'kernel321/native-install.py').read_text().replace("'stage':321","'stage':342").replace('stage=321','stage=342').replace('0.1.0-r21','0.1.0-r22')
a=s.index('def replace_module(');b=s.index('def sha(',a);s=s[:a]+s[b:]
(HERE/'native-install.py').write_text(s)
for name in ['launch-install.py','inspect-install.py']:
 s=(HERE.parent/'kernel321'/name).read_text().replace('k321-install-','k342-install-').replace('stage=321','stage=342')
 (HERE/name).write_text(s)

# Four installed unit-profile checks replace another full factory/unit campaign.
profiles=json.loads((P.parent/'kernel341/profiles-private.json').read_text());cases={}
directory=P/'profiles';directory.mkdir(exist_ok=True)
for variant in ['sunny_s5kgw1','sunny_imx471','sunny_imx319','qtech_s5k3m5sx']:
 name=variant+'-unit';row=profiles[name];item=row['item'];match=item['match']
 shutil.copyfile(P.parent/'kernel341/profiles'/(name+'.yaml'),directory/(name+'.yaml'))
 raw=bytearray();line_us=match['line_length']*1000000/match['pixel_rate']
 for target in [500,5000,12000 if item['model']=='imx471' else 25000]:
  lines=math.floor(target/line_us+.5);measured=math.floor(lines*line_us+.5)
  raw.extend(struct.pack('<9fi',1,0,0,0,1,0,0,0,1,measured))
 (directory/(name+'-phase-oracle-private.bin')).write_bytes(raw)
 cases[name]=dict(model=item['model'],profile=name,kind='unit',output=item['output'],sensor_size=item['sensor_size'],
  test_pattern=4 if item['model'] in ['imx471','imx319'] else item['test_pattern'],factory_ccm_enabled=item['factory_ccm_enabled'],planned_phases=4,
  supplier_basis='observed LC898219XI actuator, conditional on retained inventory' if item['model']=='s5kgw1' else 'explicit retained descriptor',
  exposure_mode_table_binding_verified=False)
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(HERE.parent/'kernel341/native-probe.py').read_text().replace('stage=341','stage=342')
s=s.replace('"""Temporarily run candidate core/IPA on installed CAMSS338, then restore consumers."""','"""Exercise installed r27 core/IPA with explicit private profiles."""')
s=s.replace("env['LIBCAMERA_IPA_MODULE_PATH']=str(root/'ipa');env['LD_LIBRARY_PATH']=str(root/'lib')", "env['LIBCAMERA_IPA_MODULE_PATH']='/usr/lib/libcamera/ipa';env.pop('LD_LIBRARY_PATH',None)")
s=s.replace('temporary_userspace_only=True,installed_camss338_reused=True,installed_files_unchanged=True',
 'installed_core_and_ipa=True,installed_camss338_reused=True,installed_files_unchanged=True,private_profiles_explicit=True')
(HERE/'native-probe.py').write_text(s)
for name in ['launch-probe.py','poll-probe.py','final-state.py']:
 s=(HERE.parent/'kernel341'/name).read_text().replace('k341-dynamic-lsc-','k342-installed-iq-').replace('stage=341','stage=342')
 (HERE/name).write_text(s)
archive(P/'probe.tar.gz',{'worker.py':HERE/'native-probe.py','cases.json':HERE/'cases.json','profiles':directory,
 'pipeline-fixture':P.parent/'kernel313/pipeline-fixture','bin/lsc-aec-smoke':SDK/'private/camss341-runtime/lsc-aec-smoke'})

if (HERE/'package-artifact-validation.json').exists():
 assert json.loads((HERE/'package-artifact-validation.json').read_text())['new_ipa_signature_verified_against_packaged_core']
 new={r['name']:r['version'] for r in json.loads((P/'runtime-records.json').read_text())}
 proof=dict(stage=342,packages=new,old_packages={name:('0.1.0-r21' if name.startswith('samurai-camera-') else '99990.7.2-r26') for name in new},
  module_note_sha256='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297',module_stage=338,module_unchanged=True)
 (P/'install-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 archive(P/'install.tar.gz',{'worker.py':HERE/'native-install.py','proof.json':P/'install-proof.json',
  'pipeline-fixture':P.parent/'kernel313/pipeline-fixture','bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe',
  'bin/pw-hardware-probe':SDK/'private/camss316-runtime/pw-hardware-probe'},P/'runtime-repository')
 print('Prepared r27/r22 install with r26/r21 rollback and installed four-camera IQ check.')
else:print('Prepared focused installed IQ check; install archive awaits signed package collection.')
