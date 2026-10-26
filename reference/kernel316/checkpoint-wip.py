"""Save the ongoing build handoff without promoting unverified capabilities."""
from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
prefix='''316进行中（2026-10-19）：普通应用所需StreamFormats、TRY缩放协商、自动硬件能力匹配和完整r25/r20配方已写。完整包尚未构建通过／上机／安装，最后实测仍315，设备仍309 CAMSS和r24/config-r19。当前第4次完整构建在运行，exec session49194，私有kernel316/package-build-state.json和framework-build-r4.log；不要在句柄活跃时重启或修改构建输入。读[316进行中交接](reference/kernel316/README.md)，构建终态后按其中步骤继续。315下文按最后已完成证据阅读。\n\n'''
for rel in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md']:
 p=ROOT/rel;s=p.read_text();assert not s.startswith('316进行中');p.write_text(prefix+s)
for rel,base in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/rel;d=json.loads(p.read_text());d.update(in_progress_stage=316,in_progress_evidence=base+'reference/kernel316/README.md',in_progress_installed=False)
 p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
changed=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
changed += [ROOT/p for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for p in changed:
 dest=mirror/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
print('Recorded ongoing316 build; last verified deployment stage remains315.')
