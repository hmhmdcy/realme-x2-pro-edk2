from pathlib import Path
import subprocess,json
out=Path('/mnt/e/edk2-samurai-out/kernel126')
report=[]
for number in [110,112,114]:
 root=Path(f'/home/cy122/pmos-samurai-kernel{number}/kernel');assert root.is_dir() and not root.is_symlink()
 git=subprocess.run(['git','-C',str(root),'rev-parse','--is-inside-work-tree'],capture_output=True,text=True)
 objects=list(root.rglob('*.o'));objects=[p for p in objects if '.git' not in p.relative_to(root).parts and not p.is_symlink()]
 report.append(dict(stage=number,git_rc=git.returncode,git_output=git.stdout.strip(),object_count=len(objects),object_allocated_bytes=sum(p.stat().st_blocks*512 for p in objects),vmlinux_bytes=(root/'vmlinux').stat().st_size if (root/'vmlinux').is_file() else 0))
(out/'obsolete-build-inventory-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
