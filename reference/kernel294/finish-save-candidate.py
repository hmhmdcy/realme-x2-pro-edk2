from pathlib import Path
import hashlib,json,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
generic=git('rev-parse','HEAD');assert generic.startswith('519a70abd')
assert git('show','--format=%s','--no-patch','HEAD')=='media: qcom: camss: manage metadata DMA lifetime'
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--cached']);assert patch==(ROOT/'vfe175-bhist.patch').read_bytes()
assert 'F:\tdrivers/media/platform/qcom/camss/' in (TREE/'MAINTAINERS').read_text()
q=subprocess.run([str(TREE/'scripts/checkpatch.pl'),'--no-tree','--strict','--ignore','FILE_PATH_CHANGES','-'],input=patch,capture_output=True)
(host.PRIVATE/'vfe175-bhist-checkpatch-reviewed-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stdout.decode()
message=host.PRIVATE/'vfe175-bhist-commit-message-private.txt';assert not message.exists()
message.write_text('media: qcom: camss: add VFE175 Bayer histogram statistics\n\nRegister the optional linear 1024-bin Y Bayer histogram through the existing typed metadata ABI. Use the VFE175 packet writer client and independent completion group with bounded coherent DMA, preserve other register fields, validate and clip its region in input pixel coordinates, and dispatch WB and histogram parameter blocks independently. Keep board description, firmware and product userspace unchanged.\n')
subprocess.run(['git','-C',str(TREE),'commit','-F',str(message)],check=True,capture_output=True);assert not git('status','--porcelain')
combined=subprocess.check_output(['git','-C',str(TREE),'diff','1aa1955077c977b611c722eca0bc467c3bf052ed..HEAD']);(ROOT/'vfe175-stats-candidate.patch').write_bytes(combined)
report=dict(stage=294,branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),source_clean=True,pushed=False,not_deployed=True,
 commits=[dict(label='metadata-lifecycle',commit=generic,parent='1aa1955077c977b611c722eca0bc467c3bf052ed',checkpatch_errors=0,checkpatch_warnings=0),dict(label='vfe175-bhist',commit=git('rev-parse','HEAD'),parent=generic,checkpatch_errors=0,checkpatch_default_warnings=1,warning_type='FILE_PATH_CHANGES',warning_review='Existing MAINTAINERS entry already covers the complete CAMSS directory',checkpatch_after_review_errors=0,checkpatch_after_review_warnings=0)],
 combined_patch_sha256=hashlib.sha256(combined).hexdigest())
(ROOT/'candidate-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
