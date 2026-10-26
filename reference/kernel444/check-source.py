from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;storage.mount.mounted_build()
tree=storage.candidate()/'src/libcamera-v0.7.2';old=tree.parents[1].parent/'libcamera442-bounded-dispatch/src/libcamera-v0.7.2'
state=json.loads((HERE/'source-state.json').read_text());baseline=json.loads((HERE.parent/'kernel442/source-state.json').read_text())
changed=set(state['changed_this_stage']);assert len(changed)==3
for row in baseline['source_hashes']:
 if row['path'] not in changed:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
def function(text,name):
 a=text.index('int IPACamss::'+name+'(');z=text.index('\n}\n',a)+3;return text[a:z]
ipa='src/ipa/camss-vfe/camss.cpp'
for name in ['processFocus','prepareIpeParameters']:
 assert function((old/ipa).read_text(),name)==function((tree/ipa).read_text(),name)
with tempfile.TemporaryDirectory(prefix='source-replay-',dir=P) as work:
 root=Path(work)
 for name in changed:
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/name,p)
 q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(HERE/'0056-camss-focused-ipe-dispatch.patch')],cwd=root,capture_output=True)
 (P/'patch-replay.log').write_bytes(q.stdout+q.stderr)
 assert not q.returncode and not re.search(rb'offset|fuzz',q.stdout+q.stderr,re.I)
 assert all((root/name).read_bytes()==(tree/name).read_bytes() for name in changed)
pipeline=(tree/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_text()
assert 'IPAProxyCamss>(6, 6)' in pipeline
assert pipeline.count('if (!ownsFrame()) return;')==3
r=dict(stage=444,only_three_production_files_changed=True,existing_focus_and_tone_function_bodies_byte_identical=True,
 other_recorded_numeric_profile_and_driver_sources_unchanged=True,patch_zero_fuzz_offset_and_source_equal=True,
 protocol6_core_module_proxy_must_match=True,three_stop_reentry_guards_retained=True,phone_accessed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
