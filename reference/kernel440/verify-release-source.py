from pathlib import Path
import hashlib,json,shutil,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;volume=storage.mount.mounted_build().parent;tree=storage.candidate()/'src/libcamera-v0.7.2';baseline=volume/'libcamera420-request-r31/src/libcamera-v0.7.2';old=volume/'libcamera439-front-colour/src/libcamera-v0.7.2'
for row in json.loads((HERE.parent/'kernel439/source-state.json').read_text())['source_hashes']:assert hashlib.sha256((old/row['path']).read_bytes()).hexdigest()==row['sha256']
patches=sorted(p for p in (HERE/'recipes/libcamera').glob('*.patch') if 42<=int(p.name[:4])<=51);assert len(patches)==10
paths=set()
for patch in patches:
 for line in patch.read_text().splitlines():
  if line.startswith(('--- a/','+++ b/')):paths.add(line[6:].split('\t')[0])
with tempfile.TemporaryDirectory(prefix='release440-r2-',dir=volume/'tmp') as temporary:
 dest=Path(temporary);logs=[]
 for rel in paths:
  assert not rel.startswith('/') and '..' not in Path(rel).parts
  if (baseline/rel).is_file():(dest/rel).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(baseline/rel,dest/rel)
 for patch in patches:
  q=subprocess.run(['patch','--batch','--fuzz=0','-p1'],cwd=dest,input=patch.read_bytes(),capture_output=True);log=(q.stdout+q.stderr).decode();assert not q.returncode and 'fuzz' not in log.lower() and 'offset' not in log.lower(),(patch.name,log);logs.append(log)
 for rel in paths:assert (dest/rel).read_bytes()==(tree/rel).read_bytes(),rel
 (P/'patch-chain-r2.log').write_text('\n'.join(logs))
report={'stage':440,'build_iteration':2,'passed':True,'baseline_formal_source_stage':420,'final_source_stage':440,'additional_patches':10,'compared_source_files':len(paths),'zero_fuzz_offset_replay_byte_identical':True,'original439_sources_preserved':True,'patches':[p.name for p in patches]};(HERE/'patch-chain-validation.json').write_text(json.dumps(report,indent=2)+'\n')
config=volume/'samurai-camera-config440-r32-r2';assert not config.exists();shutil.copytree(HERE/'recipes/samurai-camera-config',config)
print(json.dumps(report,indent=2))
