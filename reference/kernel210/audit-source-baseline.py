from pathlib import Path
import hashlib,json,os,subprocess,tarfile
os.umask(0o077)
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel210/source-before');out.mkdir(mode=0o700)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
status=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=k,text=True)
(out/'git-status-private.txt').write_text(status)
(out/'git-diff-private.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=k))
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=k).strip()
tracked=subprocess.check_output(['git','diff','--name-only','-z'],cwd=k).split(b'\0')
untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=k).split(b'\0')
names=sorted({os.fsdecode(n) for n in tracked+untracked if n})
files={name:sha(k/name) for name in names if (k/name).is_file()}
with tarfile.open(out/'all-current-source-changes-private.tar.gz','w:gz') as archive:
    for name in names:archive.add(k/name,arcname=name,recursive=True)
(out/'source-file-hashes-private.json').write_text(json.dumps(files,indent=2)+'\n')
artifacts={}
for name in ['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','arch/arm64/boot/dts/qcom/sm8150-samurai.dts']:
    p=k/name;artifacts[name]=sha(p);(out/name.replace('/','__')).write_bytes(p.read_bytes())
assert artifacts['.config']=='55f1f0a35bd4f20ad70ebd383a8863e05d0b6d53a07c0f0f09fb47cee057913a'
assert artifacts['arch/arm64/boot/Image']=='bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469'
assert artifacts['arch/arm64/boot/dts/qcom/sm8150-samurai.dts']=='439db9439d065cc87f0d34ca35c02e6c8e25ed787957946ebc986096ef8fa9ff'
(out/'build-artifacts-private.json').write_text(json.dumps(artifacts,indent=2)+'\n')
paths=['arch/arm64/boot/dts/qcom/sm8150-samurai.dts','drivers/of/samurai-cci-bringup.c','drivers/mfd/qcom-pm8008.c','drivers/media/i2c/imx471.c','drivers/media/v4l2-core/Kconfig','drivers/media/v4l2-core/Makefile','drivers/media/i2c/Kconfig','drivers/media/v4l2-core/v4l2-cci.c']
source=out/'review';source.mkdir(mode=0o700)
for name in paths:
    if (k/name).is_file():(source/name.replace('/','__')).write_bytes((k/name).read_bytes())
report=dict(stage=210,current_source_and_build_artifacts_backed_up=True,tracked_changes=sum(not line.startswith('??') for line in status.splitlines()),untracked_entries=sum(line.startswith('??') for line in status.splitlines()),source_files_saved=len(files),source_before_sha256={name:files[name] for name in files if name in paths},config_image_board_match209=True,no_source_mutations=True)
(here/'source-baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
