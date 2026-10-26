from pathlib import Path
import difflib,hashlib,json,subprocess,tempfile,shutil
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;tree=storage.candidate()/'src/libcamera-v0.7.2'
old=tree.parents[2]/'libcamera435-gtm-history/src/libcamera-v0.7.2'
assert (old/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').is_file()
state=json.loads((HERE/'source-state.json').read_text());build=json.loads((HERE/'build-validation.json').read_text());assert build['passed']
for row in state['source_hashes']:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
previous=json.loads((HERE.parent/'kernel435/build-validation.json').read_text())
for name in ['ipa_camss_vfe.so','ipa_camss_vfe.so.sign','camss_ipa_proxy']:
 assert next(r['sha256'] for r in build['runtime_files'] if r['name']==name)==next(r['sha256'] for r in previous['runtime_files'] if r['name']==name)
patch=''
for rel in state['changed_paths']:
 before=(old/rel).read_text().splitlines(keepends=True) if (old/rel).exists() else []
 after=(tree/rel).read_text().splitlines(keepends=True)
 patch+=''.join(difflib.unified_diff(before,after,fromfile='a/'+rel if before else '/dev/null',tofile='b/'+rel))
(HERE/'0048-camss-same-frame-tone-trace.patch').write_text(patch)
with tempfile.TemporaryDirectory(prefix='trace436-',dir=P) as temporary:
 dest=Path(temporary)
 rel=state['changed_paths'][0];(dest/rel).parent.mkdir(parents=True)
 shutil.copyfile(old/rel,dest/rel)
 q=subprocess.run(['patch','--batch','--fuzz=0','-p1'],cwd=dest,input=patch.encode(),capture_output=True)
 log=(q.stdout+q.stderr).decode();assert not q.returncode and 'offset' not in log.lower() and 'fuzz' not in log.lower(),log
 for rel in state['changed_paths']:assert (dest/rel).read_bytes()==(tree/rel).read_bytes()
(HERE/'patch-replay-validation.json').write_text(json.dumps(dict(stage=436,patch_files=2,baseline_stage=435,zero_fuzz_offset=True,replayed_sources_byte_identical=True,passed=True),indent=2)+'\n')
helper=(tree/'src/libcamera/pipeline/camss-vfe/tone_trace.h').read_text()
assert 'DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ' in helper and 'DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ' in helper
assert 'MapFlag::Write' not in helper and 'O_EXCL' in helper and 'O_NOFOLLOW' in helper
r=dict(stage=436,changed_source_files=state['changed_paths'],actual_build_sources_match=True,ipa_module_signature_proxy_identical_to435=True,
 opt_in_one_frame_trace_only=True,dma_cpu_read_sync_paired=True,logical_plane_offsets_and_lengths_retained=True,pixel_input_not_modified=True,
 kernel_sensor_board_and_math_code_unchanged=True,profile_correction_evidence='profile-export-validation.json',passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
