"""Archive and update the current checkpoint after the verified 286 build."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'archive/camera-before286-2026-10-19';assert not archive.exists()
names=['NEXT-SESSION.md','DOCS-INDEX.md']
originals={n:(ROOT/n).read_bytes() for n in names}
s=originals['NEXT-SESSION.md'].decode();first=s.split('\n\n')[1]
new='''2026-10-19：[286 Gamma/输出位深](reference/kernel286/README.md)、[285 CST](reference/kernel285/README.md)、[278标准AF](reference/kernel278/README.md)。完整多摄及骁龙ISP目标active，优先现有方案，按SoC/板级/公共驱动/用户空间收敛。本机VFE175/CSID175，硬件成像仍未完成。'''
s=s.replace(first,new,1)
old=s.split('## 源码回退与下一步\n\n')[1].split('\n\n')[0]
new='''候选`camera279-isp-kernel`/`samurai-vfe175-depth-gamma286`/`209d1ea0f`干净；实现f2626cc3c，后续仅补屏障注释。[286](reference/kernel286/README.md)增加FULL8位round/clamp及Gamma64/65节点，DMI显式地址/恢复状态/切bank，停流失败回收；WB/CST/Demosaic保持。主机ASan/UBSan及37组件Werror、完整Image/778实际ko通过，73742已终态；Image SHA33e51409…、DTB保持。未部署仍3RDI，物理DMI/通道、Demux/MNDS/统计/IPA待验；sRGB64段模型误差约20个10位码值，非画质完成。release k279candidate+不能混现机k132+模块。285六项产物存私人kernel286/completed-cst285，282基础778ko归档保持。最新输出/mnt/samurai-full282/build，先用284/storage.py核backing/挂载。'''
s=s.replace(old,new)
s=s.replace('从285继续位深/Demux/Gamma、MNDS/round-clamp、统计及pipeline/IPA','从286继续Demux/输入归一化、MNDS/GTM/CC、统计及pipeline/IPA')
index=originals['DOCS-INDEX.md'].decode().replace('[285 CST12/完整构建]','[286 Gamma/输出位深](reference/kernel286/README.md)、[285 CST12/完整构建]',1)
assert len(s.encode())<=6500,len(s.encode())
assert len(index.encode())<=10000,len(index.encode())
archive.mkdir();manifest={}
for name,data in originals.items():
    (archive/name).write_bytes(data);manifest[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
(archive/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name,data in originals.items():assert (ROOT/name).read_bytes()==data
(ROOT/'NEXT-SESSION.md').write_text(s);(ROOT/'DOCS-INDEX.md').write_text(index)
headline='286（2026-10-19）：FULL输出位深/Gamma16候选209d1ea0f通过主机ASan/UBSan、37组件Werror及完整Image/778ko。DMI/物理颜色、Demux/MNDS/统计/IPA仍待硬件验证，未部署、仍3RDI；现机276/r24/r19载荷/模块/服务/PM保持。[286证据](../../reference/kernel286/README.md)。\n\n'
for name in ['linux-port/camera/README.md','linux-port/docs/HARDWARE-STATUS.md']:
    p=ROOT/name;old=p.read_text();assert not old.startswith('286');p.write_text(headline+old)
for name,notice in [
    ('reference/kernel285/README.md','后续[286](../kernel286/README.md)已新增Gamma16/FULL输出位深，候选209d1ea0f完整构建通过；仍未部署或开放PIX。本文Gamma/round-clamp未实现及285最新输出按当时阶段阅读。'),
    ('reference/kernel276/OEM-TUNING.md','最新[286](../kernel286/README.md)：原厂FULL/Gamma协议落实到SoC后端，标准曲线和输出位深候选完整构建通过；DMI/图像尚待实机验证，完整画质调校未完成。')]:
    p=ROOT/name;old=p.read_text();at=old.index('\n\n')+2;p.write_text(old[:at]+notice+'\n\n'+old[at:])
(ROOT/'sessions/286-vfe175-gamma-and-output-depth.md').write_text('# 286：VFE175 Gamma16与FULL输出位深\n\n2026-10-19。候选209d1ea0f实现FULL RoundClamp、标准Gamma65节点到64字及DMI bank上传，实际函数ASan/UBSan和完整Image/778ko构建通过；手机保持，硬件图像/全目标未完成。[来源、测试、限制和下一步](../reference/kernel286/README.md)。\n')
print('NEXT bytes',len(s.encode()),'INDEX bytes',len(index.encode()))
