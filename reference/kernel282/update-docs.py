"""Advance entrypoints, preserving the previous checkpoint before the full-build wait."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
archive=ROOT/'archive/camera-before282-2026-10-19'
if archive.exists():
    manifest=json.loads((archive/'manifest.json').read_text())
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==item['sha256']
               for name,item in manifest.items()), 'Entrypoints already changed; inspect before replay'
else:
    archive.mkdir();manifest={}
    for name in ['NEXT-SESSION.md','DOCS-INDEX.md']:
        data=(ROOT/name).read_bytes();(archive/name).write_bytes(data)
        manifest[name]=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    (archive/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
path=ROOT/'NEXT-SESSION.md';text=path.read_text()
text=text.replace('2026-10-18：[281原厂HAL/VFE175 CAMIF](reference/kernel281/README.md)、[280型号纠正/CSID175 IPP候选](reference/kernel280/README.md)、[279现有方案/公共框架](reference/kernel279/README.md)、[278标准单次AF](reference/kernel278/README.md)。完整多摄及骁龙ISP目标active，',
    '2026-10-19：[282公共多流/FULL输出](reference/kernel282/README.md)、[281原厂HAL/CAMIF](reference/kernel281/README.md)、[280 IPP](reference/kernel280/README.md)、[278单次AF](reference/kernel278/README.md)。完整多摄及骁龙ISP目标active，直至适配完成，')
text=text.replace('运输用`reference/kernel281/host.py`','运输用`reference/kernel282/host.py`',1)
start=text.index('281候选在`camera279-isp-kernel`');end=text.index('\n\n',start)
text=text[:start]+'''282候选`camera279-isp-kernel`/`samurai-vfe175-output282`/`18b48939788bc7f95fb2999ea986846a67f0c62c`，父2985公共多流修复、281/21fac保留。复用作者v5修BUS-only DONE和最后流复位；新增175 FULL3/4双WM、0xe、byte地址/分组完成与标准捕获DMA边界，32组件W=1/-Werror和实际函数ASan/UBSan通过。仍3RDI，处理/统计/IPA未完成、未部署推送。首次完整构建因漏S5K3M5受控停止-15；只补该=m后r2已启动，原会话9620；私有kernel282/full-kernel-r2-build-state-private.json及build-r1/full282-r2-w1-private.log。续作核原句柄/进程，超时不另起；固定源码构建，结果另核。282现机载荷/模块/原服务/PM保持；[证据](reference/kernel282/README.md)，运输仍核276 guard。''' + text[end:]
text=text.replace('继续VFE175处理模块/使能、24-client输出/统计及pipeline/IPA，与280 IPP/281 CAMIF组合。',
    '核r2完整构建，再接VFE175处理/使能/统计及pipeline/IPA，组合280 IPP/281 CAMIF/282 FULL。')
assert len(text.encode())<=6500,len(text.encode());path.write_text(text)
path=ROOT/'DOCS-INDEX.md';text=path.read_text()
text=text.replace('最后整理：2026-10-18','最后整理：2026-10-19',1)
text=text.replace('[281原厂HAL/CAMIF](reference/kernel281/README.md)',
    '[282多流/FULL输出](reference/kernel282/README.md)、[281原厂HAL/CAMIF](reference/kernel281/README.md)',1)
assert len(text.encode())<=10000;path.write_text(text)
intro='''282（2026-10-19）：公共多流修复2985ef200及175 FULL双平面输出候选18b489397已通过32组件编译和实际函数ASan/UBSan；未部署，硬件成像/统计/IPA仍未完成。完整构建首次漏长焦配置受控终止，仅补S5K3M5=m后r2已启动、结果待核。现机boot276/Image183/r24/r19及50载荷/776模块/原服务/PM保持。目标按用户要求继续直至适配完成。[282证据](../../reference/kernel282/README.md)。

'''
for relative in ['linux-port/camera/README.md','linux-port/docs/HARDWARE-STATUS.md']:
    path=ROOT/relative;path.write_text(intro+path.read_text())
path=ROOT/'reference/kernel281/README.md';head,body=path.read_text().split('\n\n',1)
path.write_text(head+'\n\n后续[282](../kernel282/README.md)在本轮CAMIF之上复用公共多流修复并加入175 FULL传输候选，未部署；完整构建r2已发起，硬件成像/统计/IPA仍待完成。本文281证据按本阶段保留。\n\n'+body)
print(json.dumps(dict(checkpoint_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,index_bytes=(ROOT/'DOCS-INDEX.md').stat().st_size,previous_entrypoints_archived=True),indent=2))
