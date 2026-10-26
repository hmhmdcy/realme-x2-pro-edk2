from pathlib import Path
import json,shutil
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel211')
assert json.loads((here/'baseline-validation.json').read_text())['same210_boot_verified']
archive=repo/'archive/NEXT-SESSION-through210-2026-10-15.md';assert not archive.exists();shutil.copyfile(repo/'NEXT-SESSION.md',archive)
text=(repo/'NEXT-SESSION.md').read_text();start=text.index('2026-10-15，');end=text.index('\n\n',start)
text=text[:start]+'2026-10-15，阶段211进行中，完整外设goal active。210前摄常态启动/两轮6帧RAW已通过；211已备份源码和元数据，并在当前boot实测CROP查询EINVAL、SYSTEM/CMA heap安装但未加载且无设备节点。正在修复用户态接口及heap启动加载，尚无211产品变更或重启。[211进展](reference/kernel211/README.md)、[210完整快照](archive/NEXT-SESSION-through210-2026-10-15.md)、[边界](WORKING-BOUNDARIES.md)。'+text[end:]
text=text.replace('当前运输 `reference/kernel210/host.py`，新guard `/var/lib/samurai/k210-runtime/boot-id-private.txt`','当前运输 `reference/kernel211/host.py`，新guard `/var/lib/samurai/k211-baseline/boot-id-private.txt`（已核对仍为210新boot）')
(repo/'NEXT-SESSION.md').write_text(text)
(here/'README.md').write_text('''# 211：前摄 libcamera 接口与 DMA heap 接入（进行中）

上一轮210已完成静态前摄接入、一次启动和两轮6帧真实RAW。本轮沿同一boot继续；新基线再次确认三个DSP running、taint/五类fault0、GPS0和BT关闭。

实际V4L2 G_SELECTION查询CROP返回EINVAL，DEFAULT/BOUNDS/NATIVE_SIZE成功。SYSTEM/CMA heap模块均已安装但未加载，/dev/dma_heap无设备，OpenRC boot/modules支持modules-load.d，当前未配置相机heap。源码/配置/符号/order/模块已提前备份。[基线](baseline-validation.json)、[源备份](source-before-validation.json)。

正在核对模式寄存器与crop状态初始化，补齐正常接口返回、heap自动加载和普通用户访问。尚无211部署或重启；不将旧crop默认值伪装为正确模拟裁剪。前置与后置四摄、GNSS/蜂窝/蓝牙/传感器及完整打包目标继续保留。GNSS条件为用户确认的室内窗边，不重复相同收星对照。
''')
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='Fresh211 native baseline complete on210 boot. CROP errno22 confirmed; heap modules installed/unloaded and nodes absent. Source/metadata backed up.',guard='/var/lib/samurai/k211-baseline/boot-id-private.txt',next='Review crop initialization from real mode register tables, then correct driver and build. In parallel integrate standard modules-load.d and video-group/uaccess heap rules, validate native user allocations. No transition pending.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print('211 checkpoint written before product/source mutations.')
