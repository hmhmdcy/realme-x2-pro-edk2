"""Resume the size-guarded 284 entry-point update from its archived originals."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'archive/camera-before284-2026-10-19'
manifest=json.loads((archive/'manifest.json').read_text())
for name,meta in manifest.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==meta['sha256']
s=(ROOT/'NEXT-SESSION.md').read_text()
old=s.split('## 源码回退与下一步\n\n')[1].split('\n\n')[0]
new='''候选`camera279-isp-kernel`/`samurai-vfe175-demosaic284`/`af9e2a023`干净。mask2确认Demosaic36；参数校验、使能/停流回收通过实际函数ASan/UBSan，34组件Werror及完整Image/778实际ko通过，DTB保持。候选release为k279candidate+，不能混装现机k132+模块。[284证据](reference/kernel284/README.md)。282 r3、WB及Demosaic构建全部终态；18b基础产物/778ko归档在私有kernel284/completed-base282，最新输出/mnt/samurai-full282/build。续作用284/storage.py核backing/挂载，勿向空挂载点写；旧PID不再代表活任务。npm缓存5.25GB已迁E保留。仍3RDI，CST/位深/缩放/统计/IPA未完成，未部署推送。'''
s=s.replace(old,new).replace('2026-10-19：[283 WB参数]','2026-10-19：[284 Demosaic/完整构建](reference/kernel284/README.md)、[283 WB参数]',1)
s=s.replace('除r3完整构建外均终态，不重放。','本轮构建、迁移及采集均终态，不重放。').replace('核原r3完整构建，再接VFE175处理/使能/统计及pipeline/IPA','从284继续VFE175处理/统计及pipeline/IPA')
index=(ROOT/'DOCS-INDEX.md').read_text().replace('[283 WB/首帧参数]','[284 Demosaic/完整构建](reference/kernel284/README.md)、[283 WB/首帧参数]',1)
assert len(s.encode())<=6500,len(s.encode())
assert len(index.encode())<=10000,len(index.encode())
(ROOT/'NEXT-SESSION.md').write_text(s)
(ROOT/'DOCS-INDEX.md').write_text(index)
headline='284（2026-10-19）：原厂mask2确认Demosaic36，新候选af9e2a023通过34组件Werror/ASan/UBSan及完整Image/778实际ko；全部构建终态，未部署，仍3RDI。CST/位深/缩放/统计/IPA及完整硬件成像未完成；现机boot276/Image183/r24/r19保持。[284证据](../../reference/kernel284/README.md)。\n\n'
for name in ['linux-port/camera/README.md','linux-port/docs/HARDWARE-STATUS.md']:
    f=ROOT/name;old=f.read_text();assert not old.startswith('284');f.write_text(headline+old)
for name in ['reference/kernel282/README.md','reference/kernel283/README.md']:
    f=ROOT/name;old=f.read_text();at=old.index('\n\n')+2
    f.write_text(old[:at]+'后续[284](../kernel284/README.md)已核282 r3完整构建终态、验证归档实际778ko，并checkout WB完成正式Kbuild及Demosaic36候选完整链接；本文构建运行/未checkout等描述按当时阶段阅读。\n\n'+old[at:])
(ROOT/'sessions/284-vfe175-demosaic-and-coherent-kernel.md').write_text('# 284：VFE175 Demosaic36与完整内核模块\n\n2026-10-19。确认原厂实际选择Demosaic36，候选af9e2a023通过主机边界/生命周期与正式完整构建；未部署，完整硬件ISP目标继续。[来源、分层和完整证据](../reference/kernel284/README.md)。\n')
failure=ROOT/'reference/kernel284/initial-failures-validation.json'
report=json.loads(failure.read_text());report['initial_docs_size_guard']='NEXT calculated6580 then6504 bytes; refused before entry-point writes. Archived originals matched before the shorter resumed update.'
failure.write_text(json.dumps(report,indent=2)+'\n')
print('NEXT bytes',len(s.encode()),'INDEX bytes',len(index.encode()))
