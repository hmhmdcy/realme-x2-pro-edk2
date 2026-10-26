"""Check closeout consistency, local links, recipe mirrors and public file types."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
R=Path(__file__).resolve().parent;root=R.parents[1]
files=[p for p in R.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
py=0;js=0
for p in files:
 if p.suffix=='.py':ast.parse(p.read_text());py+=1
 if p.suffix=='.json':json.loads(p.read_text());js+=1
 assert p.suffix not in ['.bin','.img','.dtb','.apk','.pem','.key','.png','.jpg','.pyc']
 assert not p.name.endswith('-private.json') and not re.search(r'(?m)^-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----\s*$',p.read_text(errors='replace'))
links=0
for p in [R/'README.md',root/'NEXT-SESSION.md',root/'linux-port/packages/samurai-platform/README.md',root/'linux-port/packages/samurai-desktop/README.md']:
 for a,b in re.findall(r'(?<!!)\[[^\]]+\]\((?:<([^>]+)>|([^\s)]+))\)',p.read_text()):
  target=a or b
  if re.match(r'\w+:',target) or target.startswith('#'):continue
  path=target.split('#',1)[0];assert (p.parent/path).resolve().exists(),(p,target);links+=1
candidate=Path('/home/cy122/x2pro-linux/pmaports-camera-common269');recipefiles=0
for name in ['samurai-platform','samurai-desktop']:
 source=candidate/'device/testing'/name;mirror=root/'linux-port/packages'/name
 for p in source.iterdir():
  if p.is_file():assert (mirror/p.name).read_bytes()==p.read_bytes();recipefiles+=1
health=json.loads((R/'final-health-validation.json').read_text());lock=json.loads((root/'linux-port/camera/deployment-lock.json').read_text())
assert lock['current_boot_guard_stage']==269 and lock['guard_path']==health['current_guard']
assert all(row['sha256']==health['modules'][name]['sha256'] for name,row in lock['kernel_modules'].items())
assert lock['candidate_kernel_deployed'] is False and lock['full_image_and_all_modules_candidate_built']
assert lock['snapshot_reboot_cause_unresolved'] and lock['current_boot_actual_capture_validation_pending']
assert json.loads((R/'snapshot-startup-validation.json').read_text())['capture_done_events']==0
assert json.loads((R/'full-build-validation.json').read_text())['configured_modules_built_and_installed']==773
for name,digest in json.loads((R/'documentation-update-validation.json').read_text())['previous_checkpoint_and_lock_archive_sha256'].items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
report=dict(stage=269,python_syntax_checked=py,json_receipts_parsed=js,local_document_links_verified=links,
 recipe_mirror_files_exact=recipefiles,archives_exact=True,current_lock_matches_final_health=True,
 no_private_binary_or_scene_files_in_stage=True,new_kernel_candidate_distinguished_from_running_kernel=True,
 zero_frame_probe_not_counted_as_capture_pass=True,whole_adaptation_not_marked_complete=True)
(R/'closeout-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
