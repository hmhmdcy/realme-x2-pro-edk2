from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel210')
health=json.loads((here/'final-health-validation.json').read_text());archive=json.loads((here/'evidence-export-validation.json').read_text());assert health['taint']==0 and archive['all_regular_member_hashes_verified']
lib=json.loads((private/'read-libcamera-result-host-private.log').read_text())
report=dict(stage=210,root_cli_only=True,enumerated_front_cameras=len(lib['camera_entries']),sensor_stayed_suspended=lib['sensor_still_suspended'],crop_rectangle_query_returned_einval=True,static_properties_and_sensor_delay_metadata_missing=True,dma_buf_provider_open_failed=True,software_debayer_disabled=True,full_userspace_camera_not_accepted=True)
(here/'libcamera-inspection-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(here/'README.md').write_text('''# 210：前摄接入正常设备树并自动绑定，真实 RAW 取流通过

前摄不再依赖临时 overlay、VIO phandle 或性能辅助模块。已安装 IMX471、V4L2 CCI 库及支持地址迁移的 PM8008 模块，只更新 boot 中的设备树。新启动自动绑定 `imx471 7-0010` 和 `pm8008 1-0004`，media0 从22个内部实体变为23个实体，前摄正常进入 runtime suspend。[启动读回](runtime-validation.json)

## 源码与部署

修改前备份全部36份已有源改动、配置和产物。源码基线与实际204部署设备树均有910节点；以DTC YAML明确标记的引用归一化phandle后，语义完全相同，普通整数未被改写。新树925节点，仅新增15个前摄相关节点，并改变原CCI1状态和VIO phandle。[基线](baseline-semantic-validation.json)、[候选比较](camera-dtb-validation.json)

静态配置采用200实体取流证明的CCI1 master1/地址0x10、MCLK2 19.2MHz、四lane/200MHz及CSIPHY2。PM8008 Q复位是PM8150L GPIO4，未使用的P由GPIO1保持低电平复位；Q的NLDO输入引用S8C，前摄LDO2为1.050—1.056V、LDO5为2.8V，VIO静态引用PM8150L LDO1 1.8V。四路PLDO输入仍未知，没有虚构父电源。

首次候选被路径断言拦截：运行系统的i2c-1对应0x890000，源码标签实际为`&i2c4`，`&i2c1`对应0x884000。已修正后重新编译，错误候选从未部署。[板级补丁](persistent-front-camera.patch)、[配置片段](front-camera.config)、[源码记录](camera-source-validation.json)

常规配置已启用VIDEO_IMX471/V4L2_CCI/V4L2_CCI_I2C=m，五个开发helper均disabled。目标构建不再临时恢复配置；部分构建产生的符号表/删除的modules.order与原基线合并，保留16793个原符号并增加5个CCI导出，order为772。Image183及旧canonical DTB22c1保持；旧canonical不是当前部署树。[构建](camera-module-build-validation.json)、[最终源码](source-final-validation.json)

手机原模块树是770个ko/784份文件；部署后为772个ko/786份文件，仅三条模块路径变化，其余769模块逐文件保持，CAMSS与BT185保持。旧MFD及元数据在安装前已经导出私人回退归档；原生modprobe/卸载通过。[安装](module-install-validation.json)

新boot镜像89242ade…，内嵌DTB7ff712b1…，只改变UEFI中的FDT内容；其它固件、shim、header、ramdisk和分区尾保留。完整停用外设、归档并核对当前fastboot身份后，只刷boot一次，logdump/Image183未刷写。新boot读回boot/logdump/persist/NV与模块树均通过；回退boot为204 cdd16e29…。早期MM对象及BlueZ未就绪造成的两次观察失败已保留，未重复重启。[封装](build-package-validation.json)、[刷写](flash-validation.json)、[停用与归档](pre-reboot-validation.json)

## 真实取流与资源释放

WirePlumber自动发现新前摄并持有7个相机FD，传感器和CAMSS仍休眠。测试时确认唯一持有者是UID10000的空闲WirePlumber，短暂SIGSTOP，在finally中核对PID身份并SIGCONT恢复；未修改其持久配置。

首次硬件取流实际取得3帧且工具清理成功，但验收把VFE实际847000048Hz与请求847000000Hz做精确比较而停止。保留原记录后将检查限于100Hz取整差；另做两轮、每轮3帧，全部1928×1088 RAW10，每帧2628608字节，sensor/CSID测试图案均0，DMA缓冲区被图像数据覆盖、序号和时间戳递增。正式两轮共6帧，另有前次3帧，不能把前次失败的整轮验收算通过。

两轮都观察到VFE847000048Hz、CSID600MHz、MCLK19.2MHz，自身MMCX请求384；结束后自身请求0、MCLK关闭，传感器/CAMSS/CCI休眠，VDIG/VANA/VIO全部disabled/users0，原媒体图恢复。其它媒体FD为0的统计已排除暂时暂停的空闲WirePlumber；它最后已恢复。[两轮取流](static-front-capture-validation.json)

469秒独立健康再次确认前摄绑定和全部空闲资源状态；三个DSP running、taint及五类fault0，GPS0/Signals=false/rate30、BT关闭无连接，NV与产品程序保持。GNSS自动UTC准备在本次启动第8次尝试后完成，chrony Normal；没有手动时钟/轨道注入，也没有新开GPS收星会话。[最终健康](final-health-validation.json)

167份原生文件以一致快照导出，压缩包和每个常规成员均核对。原始场景RAW、私人标识和归档指纹不公开。[私人证据核对](evidence-export-validation.json)

## 用户态与下一步

root运行`cam --list`已枚举1个Internal front camera。仍有裁剪矩形EINVAL、静态属性/延迟/rotation提示，DMA buffer provider打开失败使软件debayer关闭，因此尚未验收完整拍照用户态。[检查](libcamera-inspection-validation.json)、[libcamera传感器接口要求](https://docs.libcamera.org/master/sensor_driver_requirements.html)、[内核DMA heap接口](https://docs.kernel.org/userspace-api/dma-buf-heaps.html)

源码已定位CROP分支赋值后break，最终落入-EINVAL；同时SYSTEM/CMA heap已配置为模块，需要下一阶段核对实际安装、加载、设备节点和权限，再修正启动接入。后续还要验证同一镜像第二次启动、完整冷启/未知PLDO输入、其它镜头和曝光色彩方向。

GNSS条件已由用户明确为室内窗边，不能排除弱天空信号，尚无无遮挡户外验收。209 UTC误差输入对照没有改善fix/CNR，候选未部署；不重复相同实验。[相关realme/OPPO/一加研究](../kernel205/GNSS-RELATED-DEVICES.md)。蜂窝真实业务、传感器精度/SSR、BT phase5、Wi-Fi/USB PM、完整充电和APK/rootfs整合仍属于完整goal。[当前检查点](../../NEXT-SESSION.md)
''')
checkpoint='''# Realme X2 Pro 当前检查点

2026-10-15，阶段210完成有限相机接入，完整外设goal active。前摄已在正常DTS启动中自动绑定，两轮6帧真实RAW及PM释放通过；libcamera枚举前摄，用户态仍有裁剪接口与DMA allocator缺口。下一步211继续修复。210已完成一次boot刷写及启动读回，无待确认切换。[210报告](reference/kernel210/README.md)、[209快照](archive/NEXT-SESSION-through209-2026-10-15.md)、[边界](WORKING-BOUNDARIES.md)。

## 当前部署与已验证状态

- 当前运输 `reference/kernel210/host.py`，新guard `/var/lib/samurai/k210-runtime/boot-id-private.txt`。新USB端点已发现并严格认证，旧端点另存私人210。reboot-request/boot-flash-request/fastboot-reboot-request三个marker均已闭环，禁止重放。k210-baseline及旧207/208/209 guard都是旧boot。
- 当前boot210 89242ade…/DTB7ff712b1…；Image183 bfa72dd9…/logdump e73754c7…/CAMSS82cbc052…/BT185保持。新imx471 c49dca63…/CCI库f9c9272a…/PM8008 d1ff82c0…，安装树772个ko/786份文件，其余769模块保持。TFTP207 b3bb82b9…/wifi854c9a8c…/MCFG helperd4c62be6…/MM191/helper421/init54/SSC9a1均保持。
- 静态IMX471 7-0010、PM8008 1-0004及CCI正常自动绑定，media0为23实体，无临时overlay/VIO/性能helper。前摄CCI1 master1/0x10、MCLK2 19.2MHz、4lane/200MHz、CSIPHY2。PMIC所在源码标签是&i2c4（0x890000），不可把运行i2c-1误作&i2c1（0x884000）。
- 正式两轮各3帧1928×1088 RAW10、2628608B，图案0/0、DMA覆盖/序号时间戳有效。自身MMCX384→0，VFE847000048Hz/CSID600MHz，结束后三路电源users0/disabled、MCLK0、sensor/CAMSS/CCI休眠，原媒体图恢复。首次另取3帧后被过严频率断言拦截，原失败保留，不算整轮验收通过。WirePlumber只在采集时短暂停止并finally恢复，没有持久禁用。
- 469秒最终健康：三个DSP running、taint/五类fault0；GPS0/Signalsfalse/rate30，BT关闭无连接，NV/产品程序保持。自动UTC准备第8次尝试后成功、chrony Normal；没有手动NTP/UTC/XTRA或新收星会话。167份本轮原生文件一致快照私人归档、逐成员核对，RAW场景/端点/私人标识及归档指纹不公开。

## 源码、产物与回退依据

- 内核 `/home/cy122/pmos-samurai-kernel136/kernel`，本轮仅改变36份已有改动中的板级DTS：68738cb9…；25 tracked/11 untracked仍未暂存。配置fbde3690…持久启IMX471/CCI，五个开发helper disabled。原16793符号保留+5CCI导出=16798，order772。Image183及旧canonical DTB22c1…保持；旧canonical不能刷作当前树。源与产物完整前备份在私人210/source-before。
- 私人210/modules为三模块，camera-dtb-r2为候选DTB，boot-partition-k210-front.img为当前镜像。回退boot在私人204/boot-partition-k204-bt-wake.img（cdd16e29…）；模块旧MFD/元数据在手机k210-install-before-r2及私人modules-before归档。正常回退需新核对当前设备，不使用旧marker。板级补丁及配置片段见reference/kernel210，完整kernel APK/rootfs尚未重建。
- 用户态root cam枚举1个Internal front camera，但CROP查询EINVAL、缺静态sensor属性/延迟/rotation，DMA provider失败禁用软件debayer。源码CROP分支赋值后break最终返回-EINVAL；SYSTEM/CMA heap在.config中为m，下一步核对安装/加载/节点/权限。不要将枚举或RAW成功写成完整拍照可用。
- 207已修TFTP回绕，原厂MCFG173文件8,807,671B自动RAM复制/mdtime可读，但mcfg.tmp仍0B；PDC1平台/25软件活动无pending是207实测。本轮没有PDC选择/激活或NV修改。radio新TFTP/wifi/MCFG仍未APK化，旧rootfs132和Mesa149打包债未完成。

## 续作与已知风险

211优先修IMX471 CROP返回值并做实际V4L2/libcamera验收，核对heap模块及访问权限/启动接入，推进普通用户态取流。当前已有WirePlumber自动持有7个闲置相机FD，做独占测试应核对真正持有者/休眠状态并恢复会话，不盲目卸载。之后验同镜像第二次启动与持续运行；完整断电冷启、四路PLDO输入、其它镜头/模式/曝光色彩方向均未验收。

GNSS真实fix/正CNR仍未解决。用户已明确手机在室内窗边，弱天空信号不能排除，尚无户外验收。209同会话1000→418ms UTC误差输入没有改变约6秒内部报告/收星，候选未部署；208原厂PQWM/PQWP已采，RF/天线不能由ADC变化推定正常。不重复同一时钟/收星对照。NTP启动延迟/GeoClue晚到Signals、原厂初始化/RF/LNA、精度冷启/SSR继续开放。[相关机型](reference/kernel205/GNSS-RELATED-DEVICES.md)。

保留完整目标：蜂窝真实SIM注册/数据/通话/SMS、传感器精度/FastRPC共享池与SSR/SSC首次204退出、BT phase5、Wi-Fi/USB PM、完整充电及其它外设、radio/Mesa可复现APK和新rootfs均未完成。[完整硬件清单](linux-port/docs/HARDWARE-STATUS.md)。
'''
assert len(checkpoint.encode())<8000
(repo/'NEXT-SESSION.md').write_text(checkpoint)
status=repo/'linux-port/docs/HARDWARE-STATUS.md';text=status.read_text();start=text.index('用途：');end=text.index('\n\n',start)
text=text[:start]+'用途：当前硬件验收清单。最后核对2026-10-15，阶段210。前摄静态启动自动绑定、两轮6帧RAW及PM释放通过；libcamera可枚举但裁剪接口/DMA allocator尚待修复。三个DSP running、taint/fault0，完整goal active。[210报告](../../reference/kernel210/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+text[end:]
lines=text.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| 摄像头 |'):
        lines[i]='| 摄像头 | 210正常DTS+三模块持久部署，新boot自动绑定IMX471/PM8008；两轮6帧1928×1088 RAW10、VFE847MHz/CSID600MHz，自身MMCX384→0，三路电源/时钟/CCI/CAMSS休眠和图恢复通过。libcamera枚举1个前摄，无临时overlay/性能helper | CROP返回EINVAL、缺sensor属性/延迟/rotation，DMA provider未能打开使软件debayer关闭；普通用户拍照未验收。第二boot/完整冷启/未知四路PLDO输入/其它镜头模式/曝光色彩方向/长稳仍开放；首次频率断言失败保留 |'
    if line.startswith('| GNSS定位 |'):
        lines[i]='| GNSS定位 | 208原厂时钟/ADC/XTRA诊断已取；209 UTC误差输入对照完成并恢复，候选未部署。210新boot自动UTC准备第8次后成功、chrony Normal，GPS0/Signalsfalse/rate30 | 真实fix/正CNR仍未解决，用户确认室内窗边、无无遮挡户外验收；较小UTC输入未改善约6秒内部报告。RF/天线/初始化、精度冷启/SSR、NTP延迟/晚到Signals、完整radio APK/rootfs开放 |'
status.write_text('\n'.join(lines)+'\n')
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='210 static front integration closed: one guarded boot-only flash/readback, auto binding,6 accepted RAW frames+3 earlier frames with validation failure retained, PM/graph restored, monitor resumed, final health clean,167 native files archived/member-verified.',next='211 fix CROP fall-through return; verify configured SYSTEM/CMA heap modules are installed/loaded, device naming/permissions and startup, then actual libcamera ordinary-user capture and second warm boot. Full goal active; GNSS indoor-window authoritative; no unchanged UTC/CNR repeats.',transition_pending=False,guard='/var/lib/samurai/k210-runtime/boot-id-private.txt')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(dict(stage=210,checkpoint_bytes=len(checkpoint.encode()),hardware_status_updated=True,finite_camera_milestone_complete=True,full_goal_still_active=True)))
