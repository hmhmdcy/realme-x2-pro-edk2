from pathlib import Path
import runpy,json,os,stat
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel126/ensure-build-volume.py')
stage=Path('/home/cy122/pmos-samurai-build126');base=stage/'rootfs';root=stage/'rootfs127';out=Path('/mnt/e/edk2-samurai-out/kernel127')
home=base/'home/cy122';old=[p.relative_to(base).as_posix() for p in [home,*home.rglob('*')] if p.lstat().st_uid==1000]
outside=[p.relative_to(base).as_posix() for p in base.rglob('*') if p.lstat().st_uid==1000 and not p.is_relative_to(home)]
new=[p.relative_to(root).as_posix() for p in [root/'home/cy122',*(root/'home/cy122').rglob('*')] if p.lstat().st_uid==10000]
report=dict(original_home_stale_owner_count=len(old),new_home_correct_owner_count=len(new),outside_home_uid1000=outside,source_root_mode=oct(stat.S_IMODE(base.stat().st_mode)),new_root_mode=oct(stat.S_IMODE(root.stat().st_mode)))
(out/'owner-fix-failure-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
