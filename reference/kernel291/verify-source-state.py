"""Check deployed source identity and exact tested probe sources before documentation sync."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent
tree=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *args:subprocess.check_output(['git','-C',str(tree),*args],text=True).strip()
assert git('rev-parse','HEAD')=='15c8639d8badf5d4146bfd1b2c2fcb2460a137e5' and not git('status','--porcelain')
checked=[]
for proof_file,source,binary in [('physical-tool-validation.json','samurai-physical-pix.c','physical-pix-aarch64-private'),('raw-tool-validation.json','samurai-physical-raw.c','physical-raw-aarch64-private')]:
 p=json.loads((ROOT/proof_file).read_text())
 assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest()==p['source_sha256']
 assert hashlib.sha256((host.PRIVATE/binary).read_bytes()).hexdigest()==p['binary_sha256'];checked.append(source)
for prefix in ['pattern','tele-pattern']:
 p=json.loads((ROOT/f'{prefix}-tool-validation.json').read_text())
 for kind in ['raw','pix']:
  source=f'samurai-{prefix}-{kind}.c';binary=f'{prefix}-{kind}-aarch64-private';entry=p['tools'][kind]
  assert hashlib.sha256((ROOT/source).read_bytes()).hexdigest()==entry['source_sha256']
  assert hashlib.sha256((host.PRIVATE/binary).read_bytes()).hexdigest()==entry['binary_sha256'];checked.append(source)
hardware=(tree/'drivers/media/platform/qcom/camss/camss-vfe-17x.c').read_text()
pixel=(tree/'drivers/media/platform/qcom/camss/camss-vfe-175-pixel.c').read_text()
assert 'pix->num_pads = MSM_VFE_PAD_NUM_RDI;' in hardware
assert 'No offset conversion is advertised: only zero offsets are accepted.' in pixel
report=dict(stage=291,source_branch=git('branch','--show-current'),source_commit=git('rev-parse','HEAD'),source_clean=True,
 checked_actual_probe_sources=checked,checked_sources_and_binary_hashes=True,
 no_product_kernel_dt_firmware_or_userspace_changes=True,
 parameter_registration_and_nonzero_black_offsets_still_incomplete=True,
 optical_validation_incomplete=True,goal_incomplete=True)
(ROOT/'source-state-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=ROOT/'documentation-validation.json';data=json.loads(p.read_text());data['next_bytes']=(ROOT.parents[1]/'NEXT-SESSION.md').stat().st_size;data['index_bytes']=(ROOT.parents[1]/'DOCS-INDEX.md').stat().st_size
assert data['next_bytes']<=6500 and data['index_bytes']<=10000;p.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(report,indent=2))
