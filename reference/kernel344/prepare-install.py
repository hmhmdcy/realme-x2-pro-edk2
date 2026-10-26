from pathlib import Path
import json,math,shutil,struct,tarfile,yaml
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
assert json.loads((HERE.parent/'kernel343/bound-profile-validation.json').read_text())['passed']
prefix=(HERE.parent/'kernel342/native-install.py').read_text().split('def versions():')[0].replace("'stage':342","'stage':344")
(HERE/'native-install.py').write_text(prefix+'\n'+(HERE/'transaction-body.py').read_text())
profiles=P/'profiles';profiles.mkdir(exist_ok=True);oracles=P/'oracles';oracles.mkdir(exist_ok=True)
bindings=json.loads((P.parent/'kernel343/profile-bindings-private.json').read_text());cases={}
for row in bindings:
 if row['usecase']!='Preview':continue
 model=row['model'];source=P.parent/'kernel343/profiles'/(row['profile']+'.yaml');shutil.copyfile(source,profiles/(model+'.yaml'))
 profile=yaml.safe_load(source.read_text())
 for item in row['modes']:
  size=item['sensor_size'];mode=next(m for m in profile['modes'] if [m['match']['width'],m['match']['height']]==size)
  match=mode['match'];label=row['variant']+'-mode'+str(item['sensor_mode_index'])
  line_us=match['line_length']*1000000/match['pixel_rate'];raw=bytearray()
  for target in [500,5000,12000 if model=='imx471' else 25000]:
   lines=math.floor(target/line_us+.5);measured=math.floor(lines*line_us+.5);raw.extend(struct.pack('<9fi',1,0,0,0,1,0,0,0,1,measured))
  (oracles/(label+'.bin')).write_bytes(raw)
  cases[label]=dict(model=model,profile=model,kind='unit',sensor_size='x'.join(map(str,size)),output='320x240',
   test_pattern=2 if model=='s5kgw1' else 4 if model in ['imx471','imx319'] else 3,planned_phases=4)
(HERE/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
files={'worker.py':HERE/'native-install.py','cases.json':HERE/'cases.json','configs':profiles,'oracles':oracles,
 'pipeline-fixture':P.parent/'kernel313/pipeline-fixture','bin/lsc-aec-smoke':SDK/'private/camss341-runtime/lsc-aec-smoke',
 'bin/gst-hardware-probe':SDK/'private/camss316-runtime/gst-hardware-probe','bin/pw-hardware-probe':SDK/'private/camss316-runtime/pw-hardware-probe'}
with tarfile.open(P/'install.tar.gz.tmp','w:gz') as tar:
 for name,path in files.items():tar.add(path,arcname=name)
(P/'install.tar.gz.tmp').replace(P/'install.tar.gz')
s=(HERE.parent/'kernel342/launch-install.py').read_text().replace('k342-install-','k344-calibration-');(HERE/'launch-install.py').write_text(s)
s=(HERE.parent/'kernel342/poll-probe.py').read_text().replace('k342-installed-iq-','k344-calibration-');(HERE/'poll.py').write_text(s)
s=(HERE.parent/'kernel342/analyze-installed-iq.py').read_text().replace('stage=342','stage=344').replace("summary['deployment_restored']","summary['consumers_restored']").replace("(name+'.yaml')","(item['profile']+'.yaml')").replace('len(rows)==4','len(rows)==5').replace('installed_package_compatibility=summary','default_configuration_compatibility=summary').replace("'installed-iq-validation.json'","'default-iq-validation.json'")
s=s.replace('profile=name,frames=',"case=name,profile=item['profile'],frames=").replace('mode_specific_exposure_table_binding_verified=False,','normal_preview_mode_root_binding_verified=True,all_scenarios_mode_binding_verified=False,').replace('default_profiles_changed=False,','device_private_defaults_changed=True,public_package_profiles_changed=False,default_ipa_lookup_used=True,explicit_profile_override_used=False,')
(HERE/'analyze-default-iq.py').write_text(s)
print('Prepared four private default profiles, five mode captures, and consumer checks; no frame-count quota.')
