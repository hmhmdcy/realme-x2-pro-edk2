"""Update current entrypoints while preserving the previous checkpoint verbatim."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
archive = ROOT / 'archive/camera-before281-2026-10-18'
assert not archive.exists()
archive.mkdir()
manifest = {}
for name in ['NEXT-SESSION.md', 'DOCS-INDEX.md']:
    data = (ROOT / name).read_bytes()
    (archive / name).write_bytes(data)
    manifest[name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
(archive / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

path = ROOT / 'NEXT-SESSION.md'
text = path.read_text()
text = text.replace('2026-10-18：[280型号纠正/CSID175 IPP候选]',
    '2026-10-18：[281原厂HAL/VFE175 CAMIF](reference/kernel281/README.md)、[280型号纠正/CSID175 IPP候选]', 1)
text = text.replace('运输用`reference/kernel278/host.py`', '运输用`reference/kernel281/host.py`', 1)
start = text.index('280候选仍在`camera279-isp-kernel`')
end = text.index('\n\n', start)
text = text[:start] + '''281候选在`camera279-isp-kernel`新分支`samurai-vfe175-281`/`21facb9a7941ecd0a624a9e4fccd9ae544dde7b5`，父280/7f81和279/30b0分支保留，未部署/推送。匹配175 ops/CAMIF及PIX更新/IRQ，公共prepare错误返回；31组件W=1/-Werror和实际函数ASan/UBSan通过，DTB不变，仍3个RDI，处理/输出/统计/IPA及完整链接/实机PIX缺。原厂HAL只读提取/卸载、静态恢复符号并核对CAMIF/WB/去马赛克/CST等范围；二进制私存不执行。281最终50载荷/776模块/原服务/PM保持；[证据](reference/kernel281/README.md)，运输仍核276 guard。280只读版本/记录失败见其README。''' + text[end:]
text = text.replace('同步推进匹配VFE175的CAMIF/PIX、24-client输出/统计及pipeline/IPA。',
                    '继续VFE175处理模块/使能、24-client输出/统计及pipeline/IPA，与280 IPP/281 CAMIF组合。')
assert len(text.encode()) <= 6500, len(text.encode())
path.write_text(text)

path = ROOT / 'DOCS-INDEX.md'
text = path.read_text().replace('[280型号纠正/CSID175 IPP](reference/kernel280/README.md)',
    '[281原厂HAL/CAMIF](reference/kernel281/README.md)、[280型号纠正/CSID175 IPP](reference/kernel280/README.md)', 1)
assert len(text.encode()) <= 10000
path.write_text(text)

intro = '''281：只读原厂HAL静态符号/寄存器交叉依据，新增VFE175 CAMIF/PIX更新IRQ及prepare错误返回候选21facb9a7；31组件W=1/-Werror与实际函数ASan/UBSan通过，未部署，PIX/硬件成像仍未开放。现机保持boot276/Image183/r24/r19，50载荷/776模块、原服务/PM及vendor卸载复核通过；处理/输出/统计/IPA、画质与GUI录像仍待完成。[281证据]({link})。

'''
for relative in ['linux-port/camera/README.md', 'linux-port/docs/HARDWARE-STATUS.md']:
    path = ROOT / relative
    path.write_text(intro.format(link='../../reference/kernel281/README.md') + path.read_text())

path = ROOT / 'reference/kernel276/OEM-TUNING.md'
text = path.read_text()
insert = '''后续281已只读提取本机原厂HAL并静态恢复CamX调试符号，交叉核CAMIF及多个成像模块范围，新增未部署的VFE175 CAMIF候选；完整硬件ISP仍缺。后续278已实现标准单次AF，本文276时的“尚未完成AF”按当时阶段阅读。[281原厂依据与源码](../kernel281/README.md)、[278单次AF](../kernel278/README.md)

'''
head, body = text.split('\n\n', 1)
path.write_text(head + '\n\n' + insert + body)

path = ROOT / 'reference/kernel280/README.md'
text = path.read_text()
head, body = text.split('\n\n', 1)
path.write_text(head + '\n\n后续[281](../kernel281/README.md)在本轮候选之上增加VFE175 CAMIF源码及原厂HAL静态依据，未部署；本文280结果与失败均按本阶段保留。\n\n' + body)
print(json.dumps(dict(checkpoint_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,
                     index_bytes=(ROOT/'DOCS-INDEX.md').stat().st_size,
                     previous_entrypoints_archived=True), indent=2))
