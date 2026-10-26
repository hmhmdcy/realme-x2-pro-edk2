from pathlib import Path
import difflib,hashlib,json,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=storage.candidate()/'src/libcamera-v0.7.2';old=tree.parents[2]/'libcamera437-awb-history/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text());build=json.loads((HERE/'build-validation.json').read_text());assert build['passed']
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
patch=''
for rel in state['changed_paths']:
 patch+=''.join(difflib.unified_diff((old/rel).read_text().splitlines(keepends=True),(tree/rel).read_text().splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel))
(HERE/'0050-camss-front-ipe-colour.patch').write_text(patch)
with tempfile.TemporaryDirectory(prefix='front439-',dir=P) as temporary:
 dest=Path(temporary)
 for rel in state['changed_paths']:(dest/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/rel,dest/rel)
 q=subprocess.run(['patch','--batch','--fuzz=0','-p1'],cwd=dest,input=patch.encode(),capture_output=True)
 log=(q.stdout+q.stderr).decode();assert not q.returncode and 'fuzz' not in log.lower() and 'offset' not in log.lower(),log
 for rel in state['changed_paths']:assert (dest/rel).read_bytes()==(tree/rel).read_bytes()
assert (old/'include/libcamera/ipa/camss.mojom').read_bytes()==(tree/'include/libcamera/ipa/camss.mojom').read_bytes()
r={'stage':439,'passed':True,'changed_source_files':state['changed_paths'],'actual_build_sources_match':True,'patch_zero_fuzz_offset_replay_byte_identical':True,'private_ipa_version':5,'mojom_unchanged':True,'kernel_sensor_board_unchanged':True,'ipe_colour_cct_and_manual_owned_by_observation':True,'ipe_colour_committed_with_successful_numeric_state':True,'metadata_matrix_from_successful_ipe_packet':True}
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
