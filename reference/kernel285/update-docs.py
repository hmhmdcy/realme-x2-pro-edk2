"""Archive current entry points and atomically prepare the size-limited next checkpoint."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'archive/camera-before285-2026-10-19'
assert not archive.exists()
names=['NEXT-SESSION.md','DOCS-INDEX.md']
originals={n:(ROOT/n).read_bytes() for n in names}
s=originals['NEXT-SESSION.md'].decode()
first=s.split('\n\n')[1]
new='''2026-10-19：[285 CST12/完整构建](reference/kernel285/README.md)、[284 Demosaic](reference/kernel284/README.md)、[278标准AF](reference/kernel278/README.md)。完整多摄及骁龙ISP目标active，优先现有方案，按SoC/板级/公共驱动/用户空间收敛。原厂本机为VFE175/CSID175，完整硬件成像未完成。'''
s=s.replace(first,new,1)
old=s.split('## 源码回退与下一步\n\n')[1].split('\n\n')[0]
new='''候选`camera279-isp-kernel`/`samurai-vfe175-cst285`/`d1a5f8440`干净。CST12支持601/709 full/limited内部矩阵，读取实际输出声明、先验参再MMIO、停流/失败清使能；WB/Demosaic保持。[285](reference/kernel285/README.md)主机ASan/UBSan及35组件Werror、完整Image/778实际ko通过；未部署，仍3RDI，物理色序/画质待验。Image SHA5ff0a3d2…，DTB保持，release k279candidate+不能混现机k132+模块。构建34473已终态。284六项产物另存私人kernel285/completed-demosaic284，282基础778ko完整归档保持。最新输出/mnt/samurai-full282/build；用284/storage.py先核backing/挂载，勿向空挂载点写。CST内部完成不等于PIX/Gamma/统计/IPA已通。'''
s=s.replace(old,new)
s=s.replace('从284继续VFE175处理/统计及pipeline/IPA','从285继续位深/Demux/Gamma、MNDS/round-clamp、统计及pipeline/IPA')
s=s.replace('当前仍CSIPHY/CSID/VFE RDI→RAW→CPU ISP','本轮50载荷/776模块/服务/PM只读复核保持；当前仍RDI→RAW→CPU ISP')
index=originals['DOCS-INDEX.md'].decode().replace('[284 Demosaic/完整构建]','[285 CST12/完整构建](reference/kernel285/README.md)、[284 Demosaic/完整构建]',1)
assert len(s.encode())<=6500,len(s.encode())
assert len(index.encode())<=10000,len(index.encode())
archive.mkdir()
manifest={}
for name,data in originals.items():
    (archive/name).write_bytes(data)
    manifest[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
(archive/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name,data in originals.items():assert (ROOT/name).read_bytes()==data
(ROOT/'NEXT-SESSION.md').write_text(s)
(ROOT/'DOCS-INDEX.md').write_text(index)
headline='285（2026-10-19）：CST12/601-709 full-limited内部矩阵及生命周期候选d1a5f8440通过ASan/UBSan、35组件Werror及完整Image/778ko；未部署、仍3RDI，硬件色序/位深/Gamma/统计/IPA未验收。现机276/r24/r19的载荷/模块/服务/PM保持。[285证据](../../reference/kernel285/README.md)。\n\n'
for name in ['linux-port/camera/README.md','linux-port/docs/HARDWARE-STATUS.md']:
    p=ROOT/name;old=p.read_text();assert not old.startswith('285');p.write_text(headline+old)
p=ROOT/'reference/kernel284/README.md';old=p.read_text();at=old.index('\n\n')+2
p.write_text(old[:at]+'后续[285](../kernel285/README.md)已完成CST12内部后端、正式完整构建及本轮现机只读复核；当前候选d1a5f8440，仍未部署或开放PIX。本文CST待实现及af9最新输出按284阶段阅读。\n\n'+old[at:])
p=ROOT/'reference/kernel276/OEM-TUNING.md';old=p.read_text();at=old.index('\n\n')+2
p.write_text(old[:at]+'最新[285](../kernel285/README.md)：本机原厂CST12事实落实到公共SoC后端，标准色彩矩阵与设备画质调校分开；候选完整构建通过，物理色序和硬件ISP图像仍待验证。\n\n'+old[at:])
(ROOT/'sessions/285-vfe175-cst-colorimetry.md').write_text('# 285：VFE175 CST12与色彩范围\n\n2026-10-19。候选d1a5f8440落实原厂CST12布局及四种标准矩阵，通过实际函数主机边界/色彩公式/生命周期检查和完整Image/778ko构建；现机保持，完整多摄/硬件ISP目标继续。[源码、来源、测试和剩余工作](../reference/kernel285/README.md)。\n')
print('NEXT bytes',len(s.encode()),'INDEX bytes',len(index.encode()))
