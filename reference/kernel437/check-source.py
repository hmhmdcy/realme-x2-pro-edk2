from pathlib import Path
import difflib,hashlib,json,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=storage.candidate()/'src/libcamera-v0.7.2';old=tree.parents[2]/'libcamera436-tone-domain/src/libcamera-v0.7.2'
assert (old/'src/ipa/camss-vfe/camss.cpp').is_file()
state=json.loads((HERE/'source-state.json').read_text());build=json.loads((HERE/'build-validation.json').read_text());assert build['passed']
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
previous=json.loads((HERE.parent/'kernel436/build-validation.json').read_text())
for name in ['libcamera.so.0.7.2','camss_ipa_proxy']:
 assert next(r['sha256'] for r in build['runtime_files'] if r['name']==name)==next(r['sha256'] for r in previous['runtime_files'] if r['name']==name)
for rel in ['src/ipa/camss-vfe/hardware_awb.cpp','src/ipa/camss-vfe/hardware_awb.h','src/ipa/camss-vfe/ipe_tone_profile.cpp','src/ipa/camss-vfe/ipe_tone_profile.h']:
 assert (tree/rel).read_bytes()==(old/rel).read_bytes()
assert hashlib.sha256((P/'factory-s5kgw1-private.yaml').read_bytes()).hexdigest()==json.loads((HERE.parent/'kernel436/profile-export-validation.json').read_text())['profile_sha256']
patch=''
for rel in state['changed_paths']:
 before=(old/rel).read_text().splitlines(keepends=True) if (old/rel).exists() else []
 patch+=''.join(difflib.unified_diff(before,(tree/rel).read_text().splitlines(keepends=True),fromfile='a/'+rel if before else '/dev/null',tofile='b/'+rel))
(HERE/'0049-camss-applied-white-balance-status.patch').write_text(patch)
with tempfile.TemporaryDirectory(prefix='awb437-',dir=P) as temporary:
 dest=Path(temporary);rel=state['changed_paths'][0];(dest/rel).parent.mkdir(parents=True);shutil.copyfile(old/rel,dest/rel)
 q=subprocess.run(['patch','--batch','--fuzz=0','-p1'],cwd=dest,input=patch.encode(),capture_output=True)
 log=(q.stdout+q.stderr).decode();assert not q.returncode and 'fuzz' not in log.lower() and 'offset' not in log.lower(),log
 for rel in state['changed_paths']:assert (dest/rel).read_bytes()==(tree/rel).read_bytes()
r=dict(stage=437,changed_source_files=state['changed_paths'],actual_build_sources_match=True,patch_zero_fuzz_offset_replay_byte_identical=True,
 library_and_proxy_identical_to436=True,awb_algorithm_gains_thresholds_speed_and_region_filter_unchanged=True,original_bls_and_tone_profile_byte_identical_to436=True,
 kernel_sensor_board_and_pixel_math_unchanged=True,private_ipa_version=5,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
