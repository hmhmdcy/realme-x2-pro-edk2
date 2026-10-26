from pathlib import Path
import hashlib,json,subprocess
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';out=Path('/mnt/e/edk2-samurai-out/kernel128')
rows=[]
for number,tag in [(110,'rescue'),(112,'startup'),(114,'ipa-disabled-zram')]:
 root=Path(f'/home/cy122/pmos-samurai-kernel{number}/kernel');v=root/'vmlinux';assert v.is_file() and not v.is_symlink() and v.resolve().parent==root and v.stat().st_nlink==1
 text=(root/'arch/arm64/boot/Makefile').read_text()
 assert 'OBJCOPYFLAGS_Image :=-O binary -R .note -R .note.gnu.build-id -R .comment -S' in text.replace(' := ',' :=')
 target=out/f'vmlinux{number}-objcopy-private.Image';assert not target.exists()
 subprocess.run(['aarch64-linux-gnu-objcopy','-O','binary','-R','.note','-R','.note.gnu.build-id','-R','.comment','-S',str(v),str(target)],check=True,timeout=60)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 expected=out.parent/f'kernel{number}'/('Image-'+tag)
 match=sha(target)==sha(expected)==sha(root/'arch/arm64/boot/Image')
 rows.append(dict(stage=number,vmlinux_bytes=v.stat().st_size,allocated_bytes=v.stat().st_blocks*512,canonical_objcopy_matches_retained_exported_and_local_image=match))
report=dict(redundant_debug_elf_inventory=rows,all_three_proven=all(x['canonical_objcopy_matches_retained_exported_and_local_image'] for x in rows),no_deletion_performed=True)
(ref/'redundant-vmlinux-inspection.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
