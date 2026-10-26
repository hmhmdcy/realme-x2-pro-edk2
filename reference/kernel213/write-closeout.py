from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel213')
path=repo/'NEXT-SESSION.md';text=path.read_text();paragraph=text.split('\n\n')[1]
assert '阶段213进行中' in paragraph
text=text.replace(paragraph,'2026-10-15，阶段213：关灯后RAW暗噪声与CPU ISP首帧bug已分开验证，helper/属性及一行查找表修复的隔离候选通过固定输入对照。当前仍为212启动，系统libcamera/包数据库未替换，未刷写/重启；下一步保留原包功能完成构建、打包和部署。完整外设goal active。[213证据](reference/kernel213/README.md)、[212验收](reference/kernel212/README.md)、[边界](WORKING-BOUNDARIES.md)。')
old='只有独立SDK/候选构建文件，系统相机库和包数据库未替换，无新切换。'
assert old in text;text=text.replace(old,'独立SDK与两候选已编译，RAW暗噪声及CSID固定白输入通过，系统相机库和包数据库未替换，无新切换。')
marker='## 源码、产物与回退依据'
assert text.count(marker)==1
text=text.replace(marker,'213暗场RAW10经DMA同步、排除行填充后，均值63.949～63.983、标准差0.442～0.476、相邻帧34.6%～36.3%像素变化，非全零/冻结。CSID全1正对照6帧每像素1023；旧候选首帧RGB0、后5帧254，一行修复后6帧均254。所有图案/链路/控制已恢复，最终3DSP running、相机电源/时钟释放、taint/五fault0，NV/产品保持。隔离候选未安装，RGB暗场全零不直接判bug。\n\n'+marker)
marker='前摄下一步处理首帧黑、真实增益helper/控制延迟/静态属性和tuning，验曝光色彩方向及拍照应用；'
assert marker in text;text=text.replace(marker,'前摄下一步整合libcamera0.7.2原六补丁与linux-port/camera/libcamera/的三补丁，保留原auto/virtual pipeline、其它IPA/代理、工具、tuning和签名依赖，完成可复现包/部署后验默认客户端。当前三pipeline隔离构建不能直接充当完整系统包。helper增益范围1～4.57143，像元修正1µm，延迟仍空；传感器TPG的0x0600/0601位宽疑点未修。再验控制延迟、tuning、曝光色彩方向及拍照应用；')
text=text.replace('必须用去除stride填充的RAW10直方图/噪声方差','必须先对DMA buffer执行READ START/END同步，再用去除stride填充的RAW10直方图/噪声方差')
path.write_text(text)
path=repo/'linux-port/docs/HARDWARE-STATUS.md';text=path.read_text();old=text.split('\n\n')[1]
text=text.replace(old,'用途：当前硬件验收清单。最后核对2026-10-15，阶段213。关灯后的RAW暗噪声与CPU ISP首帧bug已区分；一行查找表修复在隔离候选通过固定输入对照，系统库尚未替换。完整五摄、图像质量和完整外设goal仍开放。[213报告](../../reference/kernel213/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。')
rows=text.splitlines();indices=[i for i,line in enumerate(rows) if line.startswith('| 摄像头 |')];assert len(indices)==1
rows[indices[0]]='| 摄像头 | 210静态前摄两轮6帧RAW10，211 CROP与独立供电修复；212默认CPU跨启动取流。213同步后的暗场RAW有噪声和帧间变化；回移IMX471 helper/属性并修复CPU ISP首帧LUT，一行差异的隔离候选以固定白RAW/RGB对照通过；最终相机休眠/电源时钟释放、taint/fault0 | 修复尚未安装系统包；需保留原pipeline/IPA/工具/签名的可复现构建与部署。传感器TPG寄存器位宽疑点、控制延迟/方向/tuning、图像质量/应用和完整16MP未完成。后置四路未接入；GPU ISP的CMA不足/全黑/IOMMU unmap、未知PLDO输入/冷启/长稳开放 |'
path.write_text('\n'.join(rows)+'\n')
path=repo/'linux-port/camera/README.md';text=path.read_text();text+='\n213已在关灯环境验证同步RAW的暗噪声，并以CSID固定白输入验证首帧LUT的一行修复；IMX471增益helper/1µm静态属性也进入隔离候选。当前系统库尚未替换，完整打包/部署和默认客户端回归待做。后续按[补丁与源码锁](libcamera/README.md)保留原包功能，不能把暗场RGB全零直接当作故障。[213实机证据](../../reference/kernel213/README.md)。\n';path.write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='213 complete evidence: DMA-synchronized active RAW10 dark noise, CSID exact white RAW, A/B proves single-line CPU LUT first-frame fix. Helper/properties compiled and verified. Installed camera libraries/database unchanged; no transition. Native SDK/build and candidates retained private.',guard='/var/lib/samurai/k213-baseline/boot-id-private.txt',transition_pending=False,next='Preserve baseline auto,virtual pipelines, all IPA/proxy/tuning/tools/dependencies while integrating 3 patches into complete reproducible signed camera packages; deploy and validate default UID10000 client. Native SDK at k213-libcamera-sdk, source/build at k213-libcamera-build. Limited 3-pipeline A/B binaries must not overwrite full system package. Sensor TPG byte-width/address doubt remains. All peripheral goal active.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('213 checkpoint updated with verified dark/first-frame distinction and concrete packaging continuation; goal remains active.')
