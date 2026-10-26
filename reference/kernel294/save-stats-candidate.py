"""Keep generic lifecycle and SoC statistics in separate reviewable local commits."""
from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel');base='drivers/media/platform/qcom/camss/'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='1aa1955077c977b611c722eca0bc467c3bf052ed'
assert json.loads((ROOT/'stats-host-validation.json').read_text())['asan_ubsan'] and json.loads((ROOT/'registration-host-validation.json').read_text())['asan_ubsan']
assert not git('diff','--cached','--name-only')
groups=[('metadata-lifecycle',['camss-video.h','camss-video.c','camss-vfe.h','camss-vfe.c'],
 'media: qcom: camss: manage metadata DMA lifetime\n\nAllow a backend to validate an output immediately before starting it under output_lock. Metadata callbacks can start and stop their own statistics DMA while an image continues. Return queued buffers on a failed metadata start and stop the DMA before flushing buffers. Allocate a declared statistics target during registration and unwind metadata nodes already published for the current line on failure.\n'),
 ('vfe175-bhist',['Makefile','camss-vfe-175-stats.c','camss-vfe-175-stats.h','camss-vfe-175-output.c','camss-vfe-175-pixel.c','camss-vfe-175-pixel.h','camss-vfe-17x.c'],
 'media: qcom: camss: add VFE175 Bayer histogram statistics\n\nRegister the optional linear 1024-bin Y Bayer histogram through the existing typed metadata ABI. Use the VFE175 packet writer client and independent completion group with bounded coherent DMA, preserve other register fields, validate and clip its region in input pixel coordinates, and dispatch WB and histogram parameter blocks independently. Keep board description, firmware and product userspace unchanged.\n')]
reports=[]
for label,names,message in groups:
 subprocess.run(['git','-C',str(TREE),'add','--',*[base+n for n in names]],check=True)
 patch=subprocess.check_output(['git','-C',str(TREE),'diff','--cached']);(ROOT/(label+'.patch')).write_bytes(patch)
 q=subprocess.run([str(TREE/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True);(host.PRIVATE/(label+'-checkpatch-private.log')).write_bytes(q.stdout+q.stderr)
 assert q.returncode==0,q.stdout.decode()
 msg=host.PRIVATE/(label+'-commit-message-private.txt');msg.write_text(message);parent=git('rev-parse','HEAD')
 subprocess.run(['git','-C',str(TREE),'commit','-F',str(msg)],check=True,capture_output=True)
 reports.append(dict(label=label,parent=parent,commit=git('rev-parse','HEAD'),files=names,patch_sha256=hashlib.sha256(patch).hexdigest(),checkpatch_errors=0,checkpatch_warnings=0))
assert not git('status','--porcelain')
combined=subprocess.check_output(['git','-C',str(TREE),'diff',reports[0]['parent']+'..HEAD']);(ROOT/'vfe175-stats-candidate.patch').write_bytes(combined)
report=dict(stage=294,branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),commits=reports,source_clean=True,pushed=False,not_deployed=True)
(ROOT/'candidate-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
