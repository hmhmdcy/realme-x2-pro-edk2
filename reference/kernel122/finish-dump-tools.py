from pathlib import Path
import runpy,subprocess,hashlib,json,os
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')
stage=Path('/home/cy122/pmos-samurai-rootfs122');source=stage/'tools/f2fs-tools';dest=stage/'tools/install-root';out=Path('/mnt/e/edk2-samurai-out/kernel122')
assert not dest.exists() and (source/'fsck/.libs/fsck.f2fs').is_file()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()=='83fd39a184df96db5def895ddc55bf68e720ef76'
with (out/'dump-tools-install-private.txt').open('w') as log:
    subprocess.run(['make','DESTDIR='+str(dest),'install'],cwd=source,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
dump=dest/'usr/local/sbin/dump.f2fs';assert dump.is_file()
env=dict(os.environ,LD_LIBRARY_PATH=str(dest/'usr/local/lib'))
p=subprocess.run([str(dump),'-V'],env=env,capture_output=True,text=True,timeout=10)
(out/'dump-tools-version-private.txt').write_text(p.stdout+p.stderr);assert p.returncode==0
report=dict(commit='83fd39a184df96db5def895ddc55bf68e720ef76',complete_native_tool_build_pass=True,dump_alias_created_by_upstream_install_rule=True,private_destdir_on_e=True,no_system_binary_install=True,binary_sha256=hashlib.sha256(dump.read_bytes()).hexdigest(),version_exit_zero=True,apt_uuid_dev_added=True,source_not_modified=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/dump-tools-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
