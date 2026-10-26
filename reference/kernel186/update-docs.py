from pathlib import Path
import hashlib
import json

root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel186'
runtime=json.loads((ref/'restored-runtime-r2-validation.json').read_text())
failure=json.loads((ref/'candidate-runtime-failure-validation.json').read_text())
a11=json.loads((ref/'a11-reference-validation.json').read_text())
assert runtime['failed_candidate_not_loaded'] and runtime['original_fastrpc_loaded_and_verified']
assert failure['permanent_fix_accepted'] is False and a11['linux_deployed'] is False
old=root/'NEXT-SESSION.md'
snapshot=root/'archive/NEXT-SESSION-through185-2026-10-15.md'
assert not snapshot.exists()
snapshot.write_bytes(old.read_bytes())
readme='''# 186：SLPI停启、FastRPC共享池故障与本机A.11固件

2026-10-15。完整外设适配goal继续active，范围仍为GPS、实体摄像头、蓝牙、传感器、蜂窝等。本阶段不宣称传感器已经修复。当前仍kernel183/logdump183、boot/DTB172、runtime/modules132且仅hci_uart185覆盖，Mesa149/UCM173。边界见[WORKING-BOUNDARIES](../../WORKING-BOUNDARIES.md)。

## 原固件停启试验

重新核对185新boot，SLPI offline/供电0且本boot未启动，原hci_uart185保持。[准备](lifecycle-preparation.json)使用本机00121、原厂配置与校准的私有RAM副本、既有hexagonrpcd-v5；仅查询SSC属性，未请求测量流。文件服务保持运行直到DSP停止，再关闭服务、供电停5秒后仅尝试一次重新启动。

首次start、属性查询、DSP-first stop、第二次start均退出0，第二次状态running；第一轮完整属性只见wise_light/proximity等，accel/gyro实例仍为空。源码及NV核对保持。**第二次rproc启动成功不等于完整FastRPC/SSC重启成功**：随后FastRPC反复报SCM权限分配−22，末尾日志至少2259条SCM失败/2260条probe失败，kernel ring被覆盖。早期phase快照保留0秒日志与第二start之前的九项错误0，不能据此声称整个试验故障0。[实际范围](lifecycle-validation.json)

初始导出器错误地要求最终日志严格保留旧前缀，被真实ring覆盖拒绝；保留失败后改为分phase证据并显式标注缺口，不拼成不存在的连续全窗。属性data_type是数组，初次set转换失败也修正；查询类型有键不代表有SUID，必须检查非空实例。原始属性/日志均在私人包。

## FastRPC候选与实机失败

当前fastrpc.c在SDSP probe中把reserved pool从HLOS授权给DT VMIDs，但原remove及后续probe失败路径没有反向操作。原源码SHAa15e99ea…。[候选补丁](fastrpc-reserved-pool-lifecycle.patch)记录成功SCM调用返回的owner mask，在remove/失败unwind中申请归还HLOS；错误仍报告、失败时不清空元数据。现场DT VMIDs为3/5/6。当前[qcom_scm_assign_mem实现](https://github.com/torvalds/linux/blob/master/drivers/firmware/qcom/qcom_scm.c)也已本地核对：只在成功时更新srcvm，错误直接返回。元数据正确不证明调用时机正确。

实际probe/remove及helper提取测试337场景、ASan/UBSan、606次分配与释放；四个删除remove reclaim、删除probe unwind、错误时丢owner、错误时返回成功的负例均被运行时断言检出。[主机测试](fastrpc-host-tests-validation.json)。ARM64目标模块W=1告警0、同vermagic、import符号、原183/185源及Image/DTB/config保持，完整Module.symvers/modules.order恢复。[构建](fastrpc-module-build-validation.json)。初始checkpatch两处对齐检查及host stub两处误导缩进失败记录保留。

第一次受控热重启未刷分区，原驱动先启动。尝试临时unload/insmod被自动模块装载拦下：卸载后旧版立即出现，因此没有执行candidate insmod。原失败目录保持。随后将候选原子放入默认文件路径以供自动加载，已验证加载build-id与候选SHA95c9e2b0…匹配，taint0，旧4515b1b2…模块完整备份；当时只是under test。

三轮完整原固件文件服务/wise_light计划采用DSP-first cleanup并开启连续/dev/kmsg采集。**第一轮采样退出0，但stop时SCM归还权限−22，pool reclaim错误1，三轮总测试失败并立即停止，后两轮未执行**。[原样失败](candidate-runtime-failure-validation.json)。不能将主机绿灯当作TrustZone实际语义已验证。/dev/kmsg得到117记录、17167字节、EPIPE0、seq gaps0；按600秒边界自然结束，观察时进程已终止，没有凭ready文件重新启动采集。[采集范围](candidate-kmsg-validation.json)

原默认模块文件原子恢复，当前加载候选保留到受控复位，未强制卸载。维护内核fastrpc.c和原构建模块也恢复，失败源/模块/补丁另存，hci_qca185与原183的12源保持，最终仍tracked13。[源码恢复](source-restore-validation.json)。第二次受控热重启恢复实际加载的原FastRPC，未刷分区。源文件中的候选代码是失败原型，**不可把它作为已验收修复重新部署**。

## A.11离线提取完成

此前113阶段未完整下载的本机官方RMX1931_11.A.11，现在取得249个已核验区间，新增约45.4MB，保留113的失败与完整cache。所选firmware-update/modem.img压缩64611543字节，解压144011264字节，ZIP CRC449fd477通过，SHAe870086c…。[区间与CRC](a11-package-range-validation.json)

在独立Python3.14 venv中固定pycryptodome3.23.0；初始系统Crypto缺失、旧python3.12不存在两次失败保留。OZIP分帧仅按已固定MIT参考程序读取算法，未执行其脚本或包内updater。只读取相关ZIP member，并未下载/验收整个2.64GB包，不称全包已验签。

mcopy离线提取SLPI，版本SLPI.HY.2.1-00068-SM8150AZL-1（20190612）。22个程序头、20个加载段，split大小逐个与MDT匹配；同linked base、候选/原跨度均20MiB且fits，物理段布局不同。含LSM6DS3C/MMC5603/STK3331字符串只说明代码内容，不证明实际注册或采样。[布局与来源](a11-reference-validation.json)。**未向手机部署A.11，也未刷modem映像**；下一步仅在新启动、完整门控及独立路径下测试本机SLPI文件。

## 当前现场与后续

第二个新183启动已加载原FastRPC文件4515b1b2…，失败候选未加载；默认hci_uart185仍f6c5ed35…、build-id匹配。原BlueZ配置/密钥保持，蓝牙关/扫描关/连接0；Phosh/声卡、Wi-Fi5180、ADSP/modem running，SLPI offline/供电0且此新boot未启动。0秒日志、九类所列故障0，784树文件/770模块仅hci_uart1覆盖，boot/logdump/persist/NV/原来源核验。[恢复现场](restored-runtime-r2-validation.json)。不混入上一boot的采样、183历史音频SSR/声学/PM或185的PM证据。

两次RESTART2均根据当次新取boot身份、分区/模块核验、所有DSP/GUI/无线停止及F2FS冻结，只各发一次；分别观察新的fastboot身份/产品后各reboot一次，均无flash。所有私人包SHA验证，原始firmware、校准、密钥、trace、模块在E:/edk2-samurai-out/kernel186与手机k186*；只发布脱敏结果。

继续顺序：用原驱动及连续SCM入口/返回追踪核对owner mask、权限状态和rproc/glink/sysmon停机顺序，不能试遍未知owner或忽略−22；设计新的、实际能验证的生命周期修复。并在当前未启动过SLPI的boot测试A.11惯性注册/流，保持原固件/校准可回退。GPS真实fix/UTC/aiding/桌面桥、实体camera PM8008及CCI/C-PHY、蜂窝SIM/IPA与业务仍开放。相关同SoC仓库与官方源见[184研究](../kernel184/README.md)，它们的结果不替代本机证据。
'''
(ref/'README.md').write_text(readme,encoding='utf-8',newline='\n')
checkpoint=f'''# Realme X2 Pro 当前检查点

最后核对：2026-10-15，阶段186，完整外设goal active。当前kernel183/logdump183、boot/DTB172、modules132且仅hci_uart185覆盖、Mesa149/UCM173。186两次热重启无flash；失败FastRPC候选已恢复原文件/源码，并在第二新boot确认原版加载。规则见[边界](WORKING-BOUNDARIES.md)。用户暂无耳机，不重复问。

## 当前部署与实机依据

| 项目 | 最后核对 |
| --- | --- |
| 当前{runtime['uptime_seconds']:.2f}秒 | 新boot taint0、Phosh/声卡、Wi-Fi5180；ADSP/modem running，SLPI offline/供电0且此boot未启动。0秒日志及九类所列错误0 |
| 默认模块 | 原fastrpc4515b1b2…已恢复/加载build-id核对；失败95c9e2b0…未加载。hci_uart185 f6c5ed35…保留，784文件/770模块仅1覆盖 |
| SLPI证据 | 原00121属性查询通过；DSP-first stop后第二rproc start0，但后续FastRPC probe反复−22；不能称完整重启通过 |
| 失败候选 | 337主机场景/606 alloc-free/4负例及ARM64构建通过；实机第一轮wise_light采样0，stop reclaim−22，计划后三轮未通过且后两轮未执行。原模块文件/维护源恢复 |
| A.11 | 官方同机型区间/所选modem.img ZIP CRC449fd477/SHAe870086c…通过；SLPI2.1-00068已离线提取，22头/20段/同base/20MiB fits，未部署手机 |
| 蓝牙185 | 启动NUL边界修复已部署；原扫描错误1/候选0、3模式响应、热重启及开启s2idle45.205秒/RTC1/QCA4回调err0、延后扫描通过。Wi-Fi即时醒后检查失败保留 |
| 光线184 | wise_light实体96测量、原始通道变化；独立libssc候选CLI41样本/SensorProxy光线/接近Claim/Release通过。lux0/惯性缺失，系统库/自动服务未改 |

依据：[186](reference/kernel186/README.md)、[恢复现场](reference/kernel186/restored-runtime-r2-validation.json)、[原停启范围](reference/kernel186/lifecycle-validation.json)、[原样失败](reference/kernel186/candidate-runtime-failure-validation.json)、[A.11](reference/kernel186/a11-reference-validation.json)。185完整检查点逐字保留[through185](archive/NEXT-SESSION-through185-2026-10-15.md)，相对链接按工作区根解释；[185](reference/kernel185/README.md)、[184](reference/kernel184/README.md)仍保留。

## 源码、产物与回退依据

- WSL内核/home/cy122/pmos-samurai-kernel136/kernel当前tracked13：原183的12源及hci_qca185保持。fastrpc原a15e99ea…已恢复，失败ba187458…与95c9e2b0…候选另存，仅研究使用；[恢复](reference/kernel186/source-restore-validation.json)。Image/DTB/config、完整16793行Module.symvers和770项modules.order保持。
- 失败[补丁](reference/kernel186/fastrpc-reserved-pool-lifecycle.patch)/[构建](reference/kernel186/fastrpc-module-build-validation.json)/[主机测试](reference/kernel186/fastrpc-host-tests-validation.json)不可作为修复验收。实机当前DT VMIDs3/5/6，SCM只有成功才更新srcvm，仍需核对实际权限与停机时机。
- 原fastrpc备份手机k186-load-fastrpc-r2/fastrpc-original-private.ko、主机E:/edk2-samurai-out/kernel186；原hci_uart ae57a822…仍k185-deploy及185封存。软件/rootfs132更新可能覆盖hci_uart185/UCM173/Mesa149；不强制卸载。
- 当前boot身份手机k186-reboot-runtime-r2/boot-id-private.txt。186baseline/preflash属于第一旧boot，186r2-preflash和候选测试属于第二旧boot，下一操作重新取身份。当前新的SLPI首启机会未使用。
- 当前镜像与重要回退E:/edk2-samurai-out/kernel183/181等保持，boot172/DTB172、BDS164/固件172/FdtBlob129保持。原183音频[SSR/声学/PM](reference/kernel183/README.md)属旧boot，不混入当前；UCM173由callaudiod管理。

## 续作与已知风险

1. 完整GPS/实体camera/蓝牙/传感器/蜂窝目标保持active。优先原驱动SCM入口/返回及rproc/glink/sysmon顺序追踪，查明SDSP pool回收−22；不要试遍未知owner、忽略SCM失败或复用失败源。原第二probe错误至少2259/2260、末尾ring覆盖，初始导出前缀假设失败保留。
2. 当前新boot未启动SLPI，可做完整门控后A.11独立路径首启/属性及惯性流试验；仅本机SLPI文件，不刷modem、不导入外机校准。A.11 strings/布局检查不算传感器已工作。
3. 原00121 accel/gyro实例为空。184libssc名称配置仅独立候选，lux均0、自动亮度/接近日常/惯性/持续服务未验收。旧C28/C35磁力计结果各自保留。原RPC日志没见prjName/pcbVersion/modemType请求，元数据缺失不是已证根因；旧13-byte SMEM布局无效，应使用已核对100-byte OCDT。
4. GPS LOC历史55个in-progress不算fix，继续UTC/aiding/标准服务；蜂窝sim-missing，IPA/双槽/错误传播及真实注册/数据/通话/SMS仍开放。camera内部TPG不算实体出图，继续PM8008四输入/冷地址/复位/chip-enable本机供电契约及CCI/C-PHY。
5. 蓝牙连接/音频、物理冷启动/长稳仍未测，按边界只扫描；Wi-Fi醒后关联延迟、USB/充电/显示/触摸等待办见[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。保护NV/校准/私人数据和电池保护。

导航：[会话索引](sessions/INDEX.md)、[文档索引](DOCS-INDEX.md)。
'''
assert len(checkpoint.encode())<=6500,len(checkpoint.encode())
old.write_text(checkpoint,encoding='utf-8',newline='\n')
status=root/'linux-port/docs/HARDWARE-STATUS.md'
data=status.read_text()
intro=next(line for line in data.splitlines() if line.startswith('用途：'))
replacement='用途：当前硬件验收清单。最后核对：2026-10-15，阶段186仍kernel183/logdump183、boot/DTB172、modules132且仅hci_uart185覆盖、Mesa149/UCM173。SLPI DSP-first stop后第二rproc start0，但FastRPC共享池再probe−22；候选实机回收−22失败，原模块/源码恢复并热重启确认。A.11本机SLPI已离线提取/CRC与布局检查，未部署；见[186](../../reference/kernel186/README.md)。蓝牙185修复保留，184光线库仍独立候选，完整外设goal active。当前新boot不混入旧音频/PM证据，规则见[边界](../../WORKING-BOUNDARIES.md)。'
data=data.replace(intro,replacement,1)
row=next(line for line in data.splitlines() if line.startswith('| 其它传感器 |'))
new='| 其它传感器 | 184 wise_light实体与独立CLI/SensorProxy接口通过，lux仍0；186原固件属性查询通过，DSP-first stop后第二rproc start0；本机A.11 SLPI2.1-00068完整离线提取及CRC/布局检查通过 | 整个停启链未通过：FastRPC再probe−22；生命周期候选实机reclaim−22，原模块/源已恢复。A.11尚未部署，accel/gyro实例仍缺，持续服务、光照准确度/自动亮度、完整磁力计/旋转及接近日常开放 |'
data=data.replace(row,new,1)
status.write_text(data,encoding='utf-8',newline='\n')
(root/'sessions/186-slpi-lifecycle-native-failure-and-a11-reference.md').write_text('''# 186：SLPI停启故障、失败FastRPC原型与本机A.11参考

2026-10-15。DSP-first stop后原SLPI第二rproc start成功，但后续FastRPC共享池再probe−22；新回收原型主机337场景/4负例通过，实机第一轮采样通过但reclaim−22，总试验失败，原文件/源码恢复并热重启确认。A.11所选modem.img ZIP CRC通过，SLPI2.1-00068离线提取，未部署或刷写。

完整范围、失败和回退见[186](../reference/kernel186/README.md)，[当前检查点](../NEXT-SESSION.md)、[硬件清单](../linux-port/docs/HARDWARE-STATUS.md)。完整外设goal继续active。
''',encoding='utf-8',newline='\n')
(ref/'checkpoint-validation.json').write_text(json.dumps(dict(stage=186,
    previous185_checkpoint_preserved=True,previous185_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
    checkpoint_bytes=len(checkpoint.encode()),failed_candidate_not_accepted=True,
    current_kernel=183,current_goal='active'),indent=2)+'\n')
print(json.dumps({'checkpoint_bytes':len(checkpoint.encode()),'failed_candidate_and_restore_documented':True,'goal':'active'}))
