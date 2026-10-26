"""Commit only the tested camera DMA/DT cleanup before the full build."""
from pathlib import Path
import hashlib,json,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269');U=Path('/home/cy122/x2pro-linux/upstream')
G=['git','-c','safe.directory='+str(U),'-C',str(U)]
def git(*args):return subprocess.check_output(G+list(args),text=True).rstrip()
source=json.loads((R/'dma-source-validation.json').read_text());tests=json.loads((R/'dma-test-validation.json').read_text());dt=json.loads((R/'prepare-build-validation.json').read_text())
assert tests['results']['actual']['cases']==40024 and not dt['semantic_delta']['remaining_changed_properties']
names=list(source['files_sha256']);changed={l[3:] for l in git('status','--porcelain').splitlines()};assert changed==set(names)
for n,digest in source['files_sha256'].items():assert hashlib.sha256((U/n).read_bytes()).hexdigest()==digest
patch=subprocess.check_output(G+['diff','--',*names]);(R/'camera-dma-policy.patch').write_bytes(patch)
subprocess.run(G+['add','--',*names],check=True);subprocess.run(G+['diff','--cached','--check'],check=True)
body=P/'dma-commit-message.txt';body.write_text('media: camss: describe handset IOVA exclusions in the board tree\n\nMove RMX1931 firmware IFE IOVA reservation values and their memory-region reference from the SM8150 common tree into its board description. The compiled DT has the same 937 nodes and property values, including both reserved windows. Standard of_iommu_get_resv_regions and the DMA IOVA allocator continue to enforce the policy.\n\nKeep the CAMSS requirement for a translated DMA/FQ domain and the full-plane DMA-mask, SG continuity and length checks. Remove duplicated handset window constants from CPAS/video code and replace the bring-up dma_trace parameter with normal dynamic debug.\n\nThe actual guard/domain functions pass 40024 ASan/UBSan model cases, including 10000 scatterlists and an old-source negative control. Camera object compilation, CAMSS/PM8008/IMX319/reserved-memory schema validation and DT semantic comparison passed. Full kernel build and on-device reservation/capture regression are still required.\n')
subprocess.run(G+['commit','--file',str(body)],check=True);assert not git('status','--porcelain')
report=dict(stage=269,branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),source_files_sha256=source['files_sha256'],
 source_clean=True,original_bringup_branch_preserved=git('rev-parse','samurai-bringup')=='db301b64c0c591f63423d278643d452294654324',
 full_build_pending=True,phone_not_modified=True)
(R/'kernel-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
