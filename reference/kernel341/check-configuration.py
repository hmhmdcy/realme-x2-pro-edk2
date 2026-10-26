from pathlib import Path
import copy,json,subprocess,yaml
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;TREE='/work/libcamera/src/libcamera-v0.7.2';relative=Path('/private/camss341-contract');stage=storage.SDK/str(relative).lstrip('/');cases=json.loads((P/'profiles-private.json').read_text());rows=[]
base=yaml.safe_load((P/'profiles/sunny_imx471-unit.yaml').read_text());item=cases['sunny_imx471-unit']['item'];m=item['match']
with storage.sdk_candidate():
 for name,change in [('empty-lsc-core',lambda mode:mode['lens_shading'].update(core=[])),('missing-unit-pair',lambda mode:mode['lens_shading'].pop('golden')),('dynamic-lsc-without-lux',lambda mode:mode.pop('aec_lux'))]:
  profile=copy.deepcopy(base)
  for mode in profile['modes']:change(mode)
  (stage/(name+'.yaml')).write_text(yaml.safe_dump(profile,sort_keys=False))
  args=[str(relative/(name+'.yaml')),item['model'],*[str(m[k]) for k in ['width','height','pixel_rate','line_length','frame_length']],'-22']
  q=subprocess.run(['chroot',str(storage.SDK),'env','LD_LIBRARY_PATH='+TREE+'/output/src/libcamera:'+TREE+'/output/src/libcamera/base',str(relative/'contract'),TREE+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so',*args],capture_output=True)
  (P/(name+'-contract.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode and b'DYNAMIC_LSC_REJECT_PASS' in q.stdout,(name,q.stderr.decode()[-1200:]);rows.append(dict(case=name,expected_error=-22,passed=True))
(HERE/'configuration-validation.json').write_text(json.dumps(dict(stage=341,cases=rows,front_ccm_disabled_not_a_lux_prerequisite=True,passed=True),indent=2)+'\n');print(json.dumps(rows))
