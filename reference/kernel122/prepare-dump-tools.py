from pathlib import Path
import runpy,subprocess,json
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/ensure-rootfs-volume.py')
root=Path('/home/cy122/pmos-samurai-rootfs122/tools');root.mkdir(exist_ok=True)
source=root/'f2fs-tools';assert not source.exists()
out=Path('/mnt/e/edk2-samurai-out/kernel122')
with (out/'dump-tools-fetch-current-private.txt').open('w') as log:
    subprocess.run(['git','clone','--depth','1','https://kernel.googlesource.com/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools.git',str(source)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
assert 'dump out from the root inode' in (source/'fsck/main.c').read_text()
report=dict(primary_source='https://kernel.googlesource.com/pub/scm/linux/kernel/git/jaegeuk/f2fs-tools.git',commit=commit,nonexistent_v1170_tag_attempt_failed_and_preserved=True,fetch_pass=True,new_directory_dump_support_present=True,not_built_yet=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel122/dump-tools-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
