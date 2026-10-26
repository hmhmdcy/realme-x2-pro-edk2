from pathlib import Path

here=Path(__file__).resolve().parent;repo=here.parents[1]
path=repo/'NEXT-SESSION.md';text=path.read_text()
first=text.splitlines()[2]
text=text.replace(first,'2026-10-16，阶段218：原生尺寸Quad Bayer CPU候选完成构建、50组实机合成测试及当前模式暗场/白帧回归；候选未部署。手机保持216驱动与214完整r5栈、同一启动。全外设goal active。[218报告](reference/kernel218/README.md)、[217模式候选](reference/kernel217/README.md)、[边界](WORKING-BOUNDARIES.md)。',1)
text=text.replace('reference/kernel217/host.py','reference/kernel218/host.py').replace('k217-baseline/boot-id-private.txt','k218-baseline/boot-id-private.txt')
text=text.replace('217没有安装或切换','217/218候选未安装或切换')
text=text.replace('分别227/167/99/86/22成员','分别227/167/99/86/22成员；218另59成员')
old='217原厂模式：'
start=text.index(old);end=text.index('\n\n217旧模式120帧',start)
text=text[:start]+'''217独立双解码核对原厂3模式/174寄存器：完整4608×3456需SWRemosaic，另2304×1728 bin30/60；均19.2MHz。候选module bc4649fb…/DTB a214fd6b…仍未安装。218发现其COMPOSE数字裁剪不能被当前libcamera消费，COMPOSE_DEFAULT也不适用于subdev；先按[接口审计](reference/kernel218/geometry-interface-audit.md)修订，不盲改CROP意义。

218独立源码在 /home/cy122/x2pro-linux/libcamera214-root/work/libcamera218；原214源码/产物保留。实验补丁 linux-port/camera/isp/experimental/0001-libcamera-imx471-native-quad-cpu.patch，a7913401…，未加入配方。按IMX471完整尺寸和experimental_imx471_native_quad显式开启，默认关；保留各原始采样点、不折半。宿主400组/sanitizer、4项Meson及手机CPU类50组/780337408像素通过；system heap四RAW+四RGBA容量通过，不等于完整CAMSS/传感器通过。当前1928暗场std0.44–0.47/变化33%–36%，数字白首帧起254，taint/fault0。隔离构建默认/usr/local，回归需XDG选择逐字产品CPU配置；初次预检失败留档。先补CFA/几何/完整RAW/时序与画质，再完整包整合；不可将合成测试当16MP实拍验收。''' +text[end:]
# Details stay in217, retain the clock discrepancy without repeating all fields.
text=text.replace('217旧模式120帧buffer时间戳约57.8168fps，5次流中仍pixel_rate160M、LLP2328/FLL1308（控件算52.5447fps）；差异未归因，不盲改PLL。','217旧模式120帧时间戳57.8168fps与控件算52.5447fps不符，流中控制保持；未归因，不盲改PLL。')
assert len(text.encode())<=6500,len(text.encode())
path.write_text(text)
path=repo/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text();first=text.splitlines()[2]
text=text.replace(first,'用途：当前硬件验收清单。最后核对2026-10-16，阶段218。手机保持216驱动/214完整r5栈；218原生尺寸Quad Bayer CPU候选已通过50组合成及当前模式暗场/白帧回归，完整传感器模式未部署或验收，全外设goal仍开放。[218报告](../../reference/kernel218/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。',1)
text=text.replace('217原厂16MP/4MP候选已构建但未安装，完整尺寸重马赛克/缓冲区/COMPOSE/时序待验','217原厂16MP/4MP候选未安装；218原生尺寸CPU候选50组合成/780337408像素及当前模式回归通过，system heap容量通过；完整传感器/CAMSS导入/CFA/COMPOSE/时序与画质仍待验')
path.write_text(text)
path=repo/'DOCS-INDEX.md';text=path.read_text();old='| Camera实体前摄、静态启动与内部TPG | ';assert text.count(old)==1
text=text.replace(old,old+'[218原生尺寸CPU候选与实测边界](reference/kernel218/README.md)、');path.write_text(text)
print('Updated218 checkpoints; NEXT-SESSION bytes='+str((repo/'NEXT-SESSION.md').stat().st_size))
