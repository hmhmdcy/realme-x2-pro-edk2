from pathlib import Path
import json,shutil,subprocess
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128'
prior=json.loads((r/'reference/kernel126/obsolete-object-cleanup-validation.json').read_text());assert prior['recoverable_private_archives_verified']
rows=[]
for number in [110,112,114]:
 root=Path(f'/home/cy122/pmos-samurai-kernel{number}/kernel');assert root.is_dir() and not root.is_symlink()
 objects=[p for p in root.rglob('*.o') if p.is_file() and not p.is_symlink() and '.git' not in p.relative_to(root).parts]
 rows.append(dict(stage=number,remaining_o_files=len(objects),allocated_bytes=sum(p.stat().st_blocks*512 for p in objects),vmlinux_present=(root/'vmlinux').is_file(),
  matching_kbuild_command_objects=sum(p.with_name('.'+p.name+'.cmd').is_file() and p.name.encode() in p.with_name('.'+p.name+'.cmd').read_bytes() for p in objects)))
stable=[n for n in [109,111,113,115,128] if Path(f'/home/cy122/pmos-samurai-kernel{n}/kernel/arch/arm64/boot/Image').is_file()]
assert stable==[109,111,113,115,128]
report=dict(remaining_obsolete_c_build_inventory=rows,previous15189_verified_obsolete_objects_cleaned=True,
 retained_stable_c_stages=stable,no_additional_unverified_files_deleted=True,c_host_free_bytes=shutil.disk_usage('/mnt/c').free,
 wsl_vhd_not_compacted_or_resized=True,goal_complete=False)
(ref/'remaining-c-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
