"""Prepare scoped WB sequence analysis and retain both setup and hardware failures."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parents[1]
s=(ROOT.parent/'kernel293/analyze-frame-association.py').read_text().replace('stage=293','stage=295').replace('wb-params-capture','stats-capture').replace('wb-params-pixel','stats-pixel')
(ROOT/'analyze-frame-association.py').write_text(s);compile(s,'analyze-frame-association.py','exec')
for name in ['inspect-ssc-failure.py','restore-desktop.py']:
 s=(ROOT.parent/'kernel294'/name).read_text().replace('k294','k295').replace('stage=294','stage=295').replace('kernel_build=294','kernel_build=295')
 (ROOT/name).write_text(s);compile(s,name,'exec')
notes=dict(stages=[294,295],failures_preserved=[
 dict(operation='Initial BHIST register interpretation and k294 content test',failure='Missing independent port enumeration caused RS bit5 to be mistaken for BHIST bit4; all 90 statistics payloads contained zero bins.',resolution='Preserve original source, source-fact interpretation, physical failed counts and read-only readback; pin public port enumeration and original HAL packing; fix SoC driver and retest independently on k295.'),
 dict(operation='Early k294 SSC inspection',failure='state.json did not exist while default OpenRC startup was still in progress.',resolution='Retain private FileNotFoundError receipt; subsequent default SSC, SensorProxy and desktop became ready without service retry or nodeps restore.'),
 dict(operation='Corrected-bit host negative-control preparation',failure='Generated Python had a compound if after a semicolon, producing SyntaxError before tests or kernel changes.',resolution='Split the statement; the actual k294 code then failed the pinned bit4 contract, while the corrected driver passed ASan/UBSan and restart/unwind tests.'),
 dict(operation='Preserved build directory label',failure='k295 preparation initially labelled the verified k294 R2 backup as r1.',resolution='Verify all six artifact hashes against the actual R2 receipt and rename within the same private directory to completed-boot294-r2; no data discarded.')],
 transitions='One k293 to k294 normal transition completed; planned k294 to k295 is separately guarded. Only logdump is flashed.',private_raw_logs_retained=True)
(ROOT/'preparation-notes.json').write_text(json.dumps(notes,indent=2)+'\n')
p=BASE/'sessions/294-vfe175-metadata-lifetime-and-zero-histogram.md';assert not p.exists()
p.write_text('# 294：VFE175 metadata 生命周期与零直方图失败\n\n完整 R2 / 778 模块已部署读回。标准接口99图像/90统计包、WB颜色和三个缓冲回收通过；统计bin全零，ROI人口校验失败。只读回查与独立端口枚举定位使能位解读错误；候选295在驱动修正。默认SSC/桌面/SensorProxy随后成功启动，未重试。\n\n[完整证据](../reference/kernel294/README.md)。不将传输成功当作统计可用；多摄/ISP目标active。\n')
print('Prepared scoped sequence analysis and retained setup/hardware failures.')
