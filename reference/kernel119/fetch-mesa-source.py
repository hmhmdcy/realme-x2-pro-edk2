from pathlib import Path
import subprocess,tarfile,hashlib,json,shutil,runpy
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
mount=Path('/home/cy122/pmos-samurai-kernel118')
assert mount.is_mount()
dest=mount/'mesa-offline';dest.mkdir(exist_ok=True)
assert shutil.disk_usage(dest).free>4*1024**3
url='https://archive.mesa3d.org/mesa-26.2.4.tar.xz'
archive=dest/'mesa-26.2.4.tar.xz'
if not archive.exists():
    subprocess.run(['curl','--fail','--location','--retry','2','--connect-timeout','20','--max-time','180','--output',str(archive)+'.partial',url],check=True)
    Path(str(archive)+'.partial').rename(archive)
source=dest/'mesa-26.2.4'
if not source.exists():
    with tarfile.open(archive) as tf:
        members=tf.getmembers()
        assert all(Path(m.name).parts[0]=='mesa-26.2.4' and '..' not in Path(m.name).parts for m in members)
        tf.extractall(dest,filter='data')
assert (source/'VERSION').read_text().strip()=='26.2.4'
report=dict(official_source_url=url,version='26.2.4',archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),source_extracted_on_e_drive=True,no_phone_changes=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119/mesa-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
print((source/'src/freedreno/decode/meson.build').read_text())
