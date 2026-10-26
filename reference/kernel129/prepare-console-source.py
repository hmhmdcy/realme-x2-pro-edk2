from pathlib import Path
import subprocess,hashlib,json,os,stat,shutil,sys
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel129')
sys.path.insert(0,str(ref));from cpio_contract import members,console_ok
base=Path('/home/cy122/pmos-samurai-kernel128');stage=Path('/home/cy122/pmos-samurai-kernel129')
assert os.geteuid()==0 and not stage.exists() and shutil.disk_usage('/mnt/c').free>9*1024**3
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base/'kernel/arch/arm64/boot/Image')=='11e754d507eb445b67423f62519ced39644d0fb7b78fb89152f7978b51cd4fb9'
old=members(base/'kernel/usr/initramfs_data.cpio');assert 'dev' in old and 'dev/console' not in old
assert list((base/'initramfs/dev').iterdir())==[]
diff=subprocess.check_output(['git','-C',str(base/'kernel'),'diff','--binary'])
stage.mkdir(mode=0o700)
for name in ['kernel','initramfs']:
 subprocess.run(['cp','-a',str(base/name),str(stage/name)],check=True,timeout=300)
 print('K129_ISOLATED_SOURCE_COPY_COMPLETED',name,flush=True)
assert subprocess.check_output(['git','-C',str(stage/'kernel'),'diff','--binary'])==diff
config=stage/'kernel/.config';text=config.read_text();assert text.count('CONFIG_LOCALVERSION="-rmx1931-samurai-k128"')==1 and text.count(str(base/'initramfs'))==1
config.write_text(text.replace('CONFIG_LOCALVERSION="-rmx1931-samurai-k128"','CONFIG_LOCALVERSION="-rmx1931-samurai-k129"').replace(str(base/'initramfs'),str(stage/'initramfs')))
node=stage/'initramfs/dev/console';assert not node.exists();os.mknod(node,stat.S_IFCHR|0o600,os.makedev(5,1));os.chown(node,0,0);os.chmod(node,0o600)
assert (node.stat().st_uid,node.stat().st_gid,stat.S_IMODE(node.stat().st_mode),os.major(node.stat().st_rdev),os.minor(node.stat().st_rdev))==(0,0,0o600,5,1)
archive=out/'console-candidate-before-build-private.cpio';assert not archive.exists()
subprocess.run(['bash','usr/gen_initramfs.sh','-o',str(archive),'-u','1000','-g','1000',str(stage/'initramfs')],cwd=stage/'kernel',check=True,timeout=60)
candidate=members(archive);assert console_ok(candidate) and set(candidate)==set(old)|{'dev/console'}
assert all(candidate[name]==old[name] for name in old)
assert subprocess.check_output(['git','-C',str(base/'kernel'),'diff','--binary'])==diff and sha(base/'kernel/arch/arm64/boot/Image')=='11e754d507eb445b67423f62519ced39644d0fb7b78fb89152f7978b51cd4fb9'
report=dict(candidate_kernel=129,base128_image_and_source_preserved=True,source_driver_diff_identical128=True,initramfs_original_members=len(old),candidate_members=len(candidate),only_added_member='dev/console',encoded_console_char_5_1_uid_gid_zero_mode0600=True,all_existing_cpio_content_mode_uid_gid_links_rdev_exact128=True,localversion_and_source_path_only_config_changes=True,actual_deployment_pending=True,goal_complete=False)
(ref/'console-static-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
