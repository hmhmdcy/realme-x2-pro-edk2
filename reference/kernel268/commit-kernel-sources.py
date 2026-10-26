"""Commit only the reviewed camera source integration and record its identity."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;U=Path('/home/cy122/x2pro-linux/upstream');P=Path('/mnt/e/edk2-samurai-out/kernel268')
G=['git','-c','safe.directory='+str(U),'-C',str(U)]
def git(*args):return subprocess.check_output(G+list(args),text=True).rstrip()
d=json.loads((R/'maintained-source-validation.json').read_text());b=json.loads((R/'maintained-build-validation.json').read_text())
assert git('rev-parse','HEAD')==d['before_head'] and b['dtb_matches_deployed267'] and b['w1_camera_diagnostics']==0
names=list(d['source_files_sha256'])
for n,digest in d['source_files_sha256'].items():assert hashlib.sha256((U/n).read_bytes()).hexdigest()==digest
changed={l[3:] for l in git('status','--porcelain').splitlines()};assert changed<=set(names),changed-set(names)
subprocess.run(G+['add','--',*names],check=True)
assert set(git('diff','--cached','--name-only').splitlines())<=set(names)
style=subprocess.run(G+['diff','--cached','--check'],capture_output=True,text=True)
expected='drivers/media/i2c/imx319-222mhz-tables.h:315: new blank line at EOF.'
assert style.returncode==0 or (style.returncode==2 and style.stdout.strip()==expected and not style.stderr)
# Preserve the exact on-device register-table input, including its old EOF blank.
body=P/'kernel-commit-message.txt';body.write_text('media: describe RMX1931 camera supplies through common drivers and DT\n\nUse the common PM8008 MFD/regulator path for both camera PMICs, with reset GPIOs, address dependencies and voltage constraints supplied by DT. Remove the need for the separate laboratory supply and board reset modules. Bind IMX319 through sony,imx319 and endpoint frequencies, and report its crop and orientation through standard V4L2 properties.\n\nSynchronize IMX471 timing and common CAMSS stream failure cleanup with the tested on-device sources. Compile all five camera targets with W=1 in a fresh output directory; the resulting DTB exactly matches the deployed boot267 DTB. The deployed modules were built separately against Image183. A clean full Image/modules build remains pending.\n\nOn RMX1931: native cam front/rear cycles, cam-to-PipeWire alternation, and unchanged Snapshot front/rear preview, UI switching and JPEG capture passed. Common libcamera stale-link recovery is carried in its separate package patch. Local bindings and driver extensions have not been accepted upstream.\n')
subprocess.run(G+['commit','--file',str(body)],check=True)
assert not git('status','--porcelain')
report=dict(stage=268,repository='https://github.com/hmhmdcy/linux',branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),
 files_committed=len(git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines()),clean_worktree=True,
 mainline_base=d['mainline_base'],camera_inputs_exact=True,upstream_acceptance_not_claimed=True,remote_push_pending=True,
 known_style_diagnostic=style.stdout.strip() or None)
(R/'kernel-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
