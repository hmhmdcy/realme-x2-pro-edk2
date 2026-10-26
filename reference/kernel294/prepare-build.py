from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent;prior=ROOT.parent/'kernel293'
commit=json.loads((ROOT/'candidate-commit-validation.json').read_text())['commit']
s=(prior/'build-boot-kernel.py').read_text()
s=s.replace("COMMIT='1aa1955077c977b611c722eca0bc467c3bf052ed'",f'COMMIT={commit!r}')
s=s.replace('92aabf9ab5add22974567188f217fe711812b730ece1b46d6f3ca1731b16b6d5','d0f794c784b3587002ba18f503ed899541a3c45f80e762673bd2bfbb2ce2f7dc')
s=s.replace("ROOT.parent/'kernel292/boot-candidate-build-validation.json'","ROOT.parent/'kernel293/boot-candidate-build-validation.json'")
s=s.replace("backup=PRIVATE/'completed-boot292-r2';assert backup.is_dir()","backup=PRIVATE/'completed-boot293';assert not backup.exists();backup.mkdir()")
s=s.replace("assert sha(BUILD/name)==row['sha256'] and sha(backup/Path(name).name)==row['sha256']","assert sha(BUILD/name)==row['sha256'];shutil.copyfile(BUILD/name,backup/Path(name).name)")
s=s.replace("original=BUILD.parent/'input-initramfs290';payload=BUILD.parent/'input-initramfs293'","original=BUILD.parent/'input-initramfs293';payload=BUILD.parent/'input-initramfs294'")
s=s.replace('samurai-k293','samurai-k294').replace("KBUILD_BUILD_VERSION='293'","KBUILD_BUILD_VERSION='294'").replace("'modules293'","'modules294'").replace('modules-k293-private','modules-k294-private').replace('stage=293','stage=294')
s=s.replace('old_initramfs290_preserved=True','old_initramfs293_preserved=True').replace("report['camss_component_count']==39","report['camss_component_count']==40")
p=ROOT/'build-boot-kernel.py';assert not p.exists();compile(s,str(p),'exec');p.write_text(s)
print('Prepared independent k294 build; current k293 input and all six artifacts will be preserved.')
