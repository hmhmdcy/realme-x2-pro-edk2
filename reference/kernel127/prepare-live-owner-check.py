from pathlib import Path
import runpy,json,stat,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel127';out=Path('/mnt/e/edk2-samurai-out/kernel127');runpy.run_path(str(r/'reference/kernel126/ensure-build-volume.py'))
root=Path('/home/cy122/pmos-samurai-build126/rootfs');target=Path('/home/cy122/pmos-samurai-build126/rootfs127');rows=[]
for path in root.rglob('*'):
 s=path.lstat();rel=path.relative_to(root).as_posix()
 if s.st_uid!=1000 or rel.startswith('home/'):continue
 assert s.st_gid==1000 and (rel.startswith('usr/lib/firmware/') or rel.startswith('etc/samurai-wifi'))
 assert not path.is_symlink() and (stat.S_ISDIR(s.st_mode) or stat.S_ISREG(s.st_mode))
 assert target.joinpath(rel).lstat().st_uid==0
 digest=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else '-'
 rows.append(f'{"f" if path.is_file() else "d"} {stat.S_IMODE(s.st_mode):o} {digest} /{rel}')
assert len(rows)==85
(out/'system-resource-owner-targets-private.txt').write_text('\n'.join(sorted(rows))+'\n')
(ref/'system-owner-target-validation.json').write_text(json.dumps(dict(target_count=85,only_system_wifi_and_own_firmware_metadata=True,no_home_targets=True,all_file_content_hashes_preserved=True,no_firmware_register_or_power_operations=True),indent=2)+'\n')
print('K127_LIVE_SYSTEM85_OWNER_TARGETS_HASH_GUARDED_READY')
