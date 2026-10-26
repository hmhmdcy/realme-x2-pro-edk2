from pathlib import Path
import json,subprocess,shutil
out=Path('/mnt/e/edk2-samurai-out/kernel118')
target=Path('/home/cy122/pmos-samurai-kernel118')
assert target.resolve()==target and target.is_dir() and not target.is_symlink()
assert not (out/'candidate-preparation.json').exists(),'do not remove completed preparation'
assert not (target/'initramfs').exists(),'unexpected completed clone'
assert (Path('/home/cy122/pmos-samurai-kernel115/kernel')/'arch/arm64/boot/Image').is_file()
commands=[['findmnt','-n','-o','SOURCE,OPTIONS','/'],['df','-h','/','/mnt/c','/mnt/e'],['dmesg']]
for n,cmd in enumerate(commands):
    (out/f'host-before-{n}-private.txt').write_bytes(subprocess.check_output(cmd))
shutil.rmtree(target)
trim=subprocess.run(['fstrim','-v','/'],capture_output=True,text=True)
(out/'host-trim-private.txt').write_text(trim.stdout+trim.stderr)
(out/'host-after-private.txt').write_bytes(subprocess.check_output(['df','-h','/','/mnt/c','/mnt/e']))
report=dict(incomplete_owned_118_clone_removed=True,baseline_115_not_removed=True,trim_exit=trim.returncode,new_candidate_not_prepared=True,no_phone_flash=True,goal_complete=False)
(out/'host-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
