from pathlib import Path
import hashlib,json,shutil,subprocess
import host
ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='4757a0f15c1e0439eef2fdddf6043d65635f1c90'
path='drivers/media/platform/qcom/camss/camss-vfe.c';assert git('diff','--name-only')==path
assert json.loads((ROOT/'fixed-restart-metadata-validation.json').read_text())['partial_output_start_unwind_verified']
patch=subprocess.check_output(['git','-C',str(TREE),'diff']);q=subprocess.run([str(TREE/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True)
(host.PRIVATE/'metadata-restart-checkpatch-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stdout.decode()
for original,target in [('candidate-commit-validation.json','candidate-r1-commit-validation.json'),('boot-candidate-build-validation.json','boot-r1-build-validation.json')]:
 p=ROOT/target;assert not p.exists();shutil.copyfile(ROOT/original,p)
for name in ['installed-module-inventory-private.json','boot-initramfs-manifest-private.json']:
 p=host.PRIVATE/name;target=p.with_name(name.replace('-private','-r1-private'));assert not target.exists();shutil.copyfile(p,target)
message=host.PRIVATE/'metadata-restart-commit-message-private.txt';message.write_text('media: qcom: camss: retain metadata buffers across image restarts\n\nWhen only an image stream stops, its auxiliary metadata queue can remain streaming. Stop the DMA and put its active buffers back at the front of the pending queue rather than overwriting them on the next image start. Clear stopped output state under output_lock. Unwind outputs already enabled if a later output fails preparation, preserving their queued buffers for the callers failure cleanup and retry.\n')
subprocess.run(['git','-C',str(TREE),'add','--',path],check=True);subprocess.run(['git','-C',str(TREE),'commit','-F',str(message)],check=True,capture_output=True);assert not git('status','--porcelain');commit=git('rev-parse','HEAD')
report=json.loads((ROOT/'candidate-commit-validation.json').read_text());report['commits'].append(dict(label='metadata-restart',parent=report['commit'],commit=commit,checkpatch_errors=0,checkpatch_warnings=0));report['commit']=commit
combined=subprocess.check_output(['git','-C',str(TREE),'diff','1aa1955077c977b611c722eca0bc467c3bf052ed..HEAD']);(ROOT/'vfe175-stats-candidate.patch').write_bytes(combined);report['combined_patch_sha256']=hashlib.sha256(combined).hexdigest()
(ROOT/'candidate-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
s=(ROOT/'build-boot-kernel.py').read_text().replace('4757a0f15c1e0439eef2fdddf6043d65635f1c90',commit)
s=s.replace('d0f794c784b3587002ba18f503ed899541a3c45f80e762673bd2bfbb2ce2f7dc','668a1b37ce96c9cf0e7bc591d3e5f7c418340245ae4156a49512c005a7bc2c97')
s=s.replace("ROOT.parent/'kernel293/boot-candidate-build-validation.json'","ROOT/'boot-r1-build-validation.json'").replace('completed-boot293','completed-boot294-r1')
s=s.replace('boot-build-state-private','boot-build-r2-state-private').replace("('boot-'+name+'-private.log')","('boot-r2-'+name+'-private.log')")
s=s.replace('input-initramfs294','input-initramfs294-r2').replace("'modules294'","'modules294-r2'").replace('modules-k294-private','modules-k294-r2-private')
s=s.replace("{'CONFIG_LOCALVERSION','CONFIG_INITRAMFS_SOURCE'}","{'CONFIG_INITRAMFS_SOURCE'}")
p=ROOT/'build-boot-r2.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print(json.dumps(report,indent=2))
