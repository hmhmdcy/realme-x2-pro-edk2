# 当前检查点：385（多尺寸/格式及交替会话16帧实机通过，目标active）

先读WORKING-BOUNDARIES.md、reference/kernel385/README.md。384完整交接归档archive/NEXT-SESSION-through384-2026-10-20.md，383/382/381/380更早归档保留。现场关灯，按低照度解释，黑/噪点不单独判故障；光照校准后续做。

## 当前源和改动

维护源/mnt/samurai-full282/source354，branch samurai-a5-ipe-frames385，HEAD6fb4806e219998f5d06919a9b0266ff7b08867b0，父3845a0df37d3e9c8971d55186e468b38b424c8387dc，干净且等于已验证提案。

只改临时诊断：test_width/height/port/cores/frames/uv_swap只读参数，最多8帧/64MiB、资源前验证；逐帧变亮度/色度图案、request_id递增、RT/nonRT交替；记录输入/输出CRC、Y差异数、UV绝对误差和，末帧完整像素留内存导出。BL512KiB仍在1MiBparcel内。核心/条带/IQ/DMA回收不变：核心317008B SHAb429dc7b37fb22d9a5628a90eb3e27b780e4df3da568750f815ac7ae09a3b56d；test110008B SHAf0c9378d2736fe38269e3319b5017f5ef6421ae5f1af588c544f0d3321fa0953。实际k363 in-tree W1/-Werror无诊断，未永久安装。

原生bypass_size/encode_bypass_striping已接run，job已无外部stripe/IQ；仅1pass全帧1:1/IQ关闭/8bit线性NV12-NV21、匹配输入输出尺寸及UV顺序、port8/9、core1/2，偶宽高128..8192、有效偶stride/slice，实际每image≤64MiB。383分区ceil(W/328)向core倍数取整、右到左对齐2/halo4；LTMgridX=ceil(max(W,320)/12)，Y=ceil(max(H,240)/9)，inv65536/grid、径向x=first-W/2/y=-H/2。384有52组原FW整512KiB CDM/32Bjob对照和24组DMA故障注入，未改组件复用。

## 本轮实机证据

同一378-recovered启动guard /var/lib/samurai/k378-recovered/boot-id-private.txt。host385委托384→383→382→381→380→379→378，严格原USBkey/known_hosts。

- /var/lib/samurai/k385-boot-r1，worker15018：128×128/port8/core1/NV12/2帧，CMD196/MSG213words，19messages/20IRQs，UV MAE0.1953125。
- r2 worker15194：640×480/port9/core2/NV21/4帧，CMD272/MSG293、25/26，UV MAE0.203125。
- r3 worker15302：1920×1080/port8/core2/NV12/6帧，CMD348/MSG373、31/32，UV MAE0.2309027778。
- r4 worker15445：4608×3456/port9/core2/NV21/4帧，CMD272/MSG293、25/26，UV MAE0.2452256944。

共RT8/nonRT8，双handle/configscratch48/48，各帧MAP/FRAME40/ACK72/UNMAP，双destroy、PC/WFI/cooperative stop和全部BO/PM回收。四组worker/collector均terminal/exited，每次clks17归零、taint0、wd/protocol0、newfault0；无新失败事务/重启/永久安装，不用外部stripe/IQ。末次预检电100%、24.0°C。

16帧共77404160 Y字节由内核比较等于当帧输入；主机独立重建16输入CRC、组内输出CRC逐帧不同。每组末帧完整图/CRC/UV误差主机复核；前面帧全图未保存，不声称逐帧主机全图对比。UV仍滤波差，非全平面identity/完整IQ。最大末帧23887872B，SHA0c683aa2c6646982c011883d82cc48fff0171b518948f1c149ce26ebd0a83225，私存385/collected-rN/ipe-output-private.nv12。max_cores2是已通过配置，未分别测量两IPE负载/吞吐，也非持续满帧率/并发双流。

close-current确认源干净、taint0、CAMSS/双CCI休眠、9rails disabled/users0、静态ICPdisabled、临时FW/模块无残留、四对进程均不存活。所有exec session已同handle终态。四摄普通采集仍381每摄12帧640，主摄IPA27帧5阶段/GammaACK1，未重复。Image363/7.3.0-rc6-rmx1931-samurai-k363+、boot366 DT365、五libcamera r29/config-stackr24、362四私有Preview保持。Image源码ba61a62293e0f6bc5838c06f2e85e033e3d702a8、DT源码e217016006e609333a715c10f2f3e442dc4da95f。SSC旧EPERM/daemon4/SLPIoffline/SensorProxystopped未修，desktop379恢复保持，不宣称全平台健康。

## 接续完整目标

重点转向V4L2 m2m/libcamera真实入口，处理队列/会话/取消错误与生命周期。core run为睡眠同步CPU-copy bring-up，不当最终零拷贝/吞吐路径。先复核已有352固定原型ebd1e440443121d18f730ab2aeea5586a754f36f（缺HFI/BPS文件及IPE会话定义、IPE未入Makefile、旧接口），复用可用框架，不盲拷X1E80100 MDT/PAS到SM8150 A5。

继续原厂Gamma/LTM/CCM等完整IQ；第五2MP身份未知（OV02A1B库名不是ID、front共享PHY2/MCLK2/reset12、GPIO29mux未解），更多模式、动态帧长/自动频闪、光学/几何/同步/连续AF等按363/REMAINING-CAMERA-SCOPE.md。bypass/合成图不是最终完成条件。目标active、无预算、未pause。

## 不可丢的资源/历史/来源

381DMAretain/quiescence：SID2222/0、2080/20、20a0/20、2100/20、2120/20、20c0/0、2140/0，mask不交CAMSS；images20000000+08000000仅IOVA名空间，每image64MiB；parcel07800000≤1MiB在既有shared内、config07600000/4KiB。未知完成留BO/PM；A5停机IRQjoin后两IPE CDMresetf/TOP3新ACK并清除成功才free，失败明确retry。

373先reset/wake后HFI参数program/readback；375正常PC/WFI/CPUoff不额外全局BCR；376双token/IRQjoin/错误锁存；379MAP/UNMAPACK44只header有效、尾12未初始化，CONFIGACK56scratch36/DESTROYACK48/FRAMEACK72。377/378失败自动重启审计保留，内部原因未测，不重复旧事务；372ABTSP+58修正/EUD377retired保持。完整细节见384归档。

Unicorn2.1.4全局MEM_READ破坏ThumbIT/SP，383最小复现保留；只用限定观察且整CDM/job与无观察一致后采信。384常规模型无读钩子。HAL CPUwrite mask不含provider uc.mem_write，不当全初始化mask；模型chip寄存器10705非本轮新实机读。

访问ext4前reference/kernel284/storage.py::mounted_build()，返回/mnt/samurai-full282/build和旁置source354，不格式化/重建镜像。libcamera源/mnt/samurai-full282/libcamera362-serialized-built/src/libcamera-v0.7.2，SDK/home/cy122/x2pro-linux/libcamera214-root，bind串行。HAL281/camera.qcom.so-private、350debugELF仅符号；FW352/CAMERA_ICP.elf-private、asm370-marmv7；Unicorn/home/cy122/x2pro-linux/private-k329-venv/bin/python。fixedGPL9668fcdc6ec15be7a10d66f7b93c347829e0fdb6、CamxChi9f17f1b568626b393e785b369c5dc94543774d7a，partialclone不全树gitgrep/lazyfetch；383stats/paramsRFC仍draft无目标条带算法。

rawFW/HAL/asm/CDM/图像/完整日志/校准/auth仅/mnt/e/edk2-samurai-out/kernelNNN；公共mirror/home/cy122/edk2-samurai/repo仅Platform/Realme/sm8150，本地commit不push/PR，保护无关staged/工作区。boot366 SHAc3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924、logdump365 SHAaca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da，旧rollback保留。
