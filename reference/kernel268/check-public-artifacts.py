"""Validate public source syntax, recipe hashes, links and absence of private material."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parent;root=R.parents[1];syntax=0;files=[]
for directory in [R.parent/'kernel267',R]:
 for p in directory.rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts:continue
  assert p.suffix.lower() not in ['.jpg','.jpeg','.png','.raw','.key','.pem','.apk','.ko','.img']
  if p.suffix=='.py':compile(p.read_text(),str(p),'exec');syntax+=1
  b=p.read_bytes();assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',b)
  files.append(p)
for name in ['libcamera','samurai-camera-config']:
 p=root/'linux-port/packages'/name;lock=json.loads((p/'source-lock.json').read_text())
 for n,digest in lock['source_files_sha256'].items():assert hashlib.sha256((p/n).read_bytes()).hexdigest()==digest
for doc in [R/'README.md',root/'NEXT-SESSION.md']:
 for target in re.findall(r'\]\(([^)]+)\)',doc.read_text()):
  if '://' not in target and not target.startswith('#'):assert (doc.parent/target.split('#')[0]).exists(),target
native=[json.loads((R/('camera-'+str(i)+'-validation.json')).read_text()) for i in [16,17,18]]
assert all(d['diagnostic_completed'] and d['app_exit_code']==0 and not any(d['fault_delta'].values()) for d in native)
assert sum(d['probe_result']['buffers'] for d in native)==1097
assert sum(d['probe_result']['held_checked'] for d in native)==1081
assert sum(len(d['probe_result']['shots']) for d in native)==9
gui=json.loads((R/'snapshot-gui-r5-validation.json').read_text())
assert gui['diagnostic_completed'] and gui['gui_control']['camera_switch_action_accepted']
assert {p['camera'] for p in gui['gui_control']['new_jpegs']}=={'front','rear'}
source_files={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if R in p.parents and (p.suffix in ['.py','.cpp','.patch','.md'] or 'recipes' in p.parts)}
report=dict(stage=268,python_sources_compile=syntax,public_files_checked=len(files),recipe_sha256_records_match=True,
 relative_readme_checkpoint_links_exist=True,private_key_material_and_image_payloads_absent=True,
 gst_preview_frames=1097,held_prefix_checks=1081,gst_jpeg_count=9,gui_front_rear_switch_photo_verified=True,
 full_camera_goal_still_active=True)
(R/'public-artifact-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(R/'checkpoint-source-lock.json').write_text(json.dumps(source_files,indent=2)+'\n')
print(json.dumps(report))
