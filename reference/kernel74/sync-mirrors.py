from pathlib import Path
import shutil
import subprocess

w = Path('/mnt/e/RealmeX2Pro edk2')
p = Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
for name in ('README.md','HANDOVER-NEXT.md','DOCS-INDEX.md','RX-CONSOLE.md','FLYWHEEL.md',
             'NEXT-SESSION.md','NEXT-SESSION-PROMPT.md'):
    shutil.copyfile(w/name,p/name)
shutil.copytree(w/'reference/kernel74',p/'reference/kernel74',dirs_exist_ok=True,copy_function=shutil.copyfile)
shutil.copyfile(w/'sessions/74-sm8150-display-boot-handoff.md',p/'sessions/74-sm8150-display-boot-handoff.md')
shutil.copytree(w/'linux-port',p/'linux-port',dirs_exist_ok=True,
    ignore=shutil.ignore_patterns('artifacts'),copy_function=shutil.copyfile)
repo = p.parents[2]
tracked = subprocess.check_output(['git','-C',str(repo),'ls-files','-s'],text=True)
for line in tracked.splitlines():
    meta,name = line.split('\t',1)
    mode = meta.split()[0]
    target = repo/name
    if target.is_file() and mode in ('100644','100755'):
        target.chmod(0o755 if mode=='100755' else 0o644)
print('Synchronized source/evidence/living docs; preserved historical mirrors and tracked modes.')
