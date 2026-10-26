from pathlib import Path
import json
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel132'
bundle = json.loads((ref / 'complete-bundle-validation.json').read_text())
power = json.loads((ref / 'persistent-power-validation.json').read_text())
assert bundle['matching_boot_logdump_rootfs_modules_complete'] and power['auto_registered_after_actual_flash_boot']
session = '132-persistent-mp2650-real-boot-and-complete-rootfs.md'
summary = ('阶段132已实际刷入boot与logdump，内核#132/770匹配模块及UEFI内嵌设备树通过，MP2650在QUP1/0x5c启动自动注册只读标准power_supply。'
           '42.13秒8份事件全部非空/ONLINE1/Charging，电压8/8为4.400–4.475V，输入电流7/8为400.00–418.75mA，另1份ENODATA；桌面PID/taint0/BlueZ/5180MHz与11来源保持，窗口无新增故障。'
           '新boot仍DPU超时4、BT UART重组错误2，GPU0仅此无负载启动窗口，131迟发CCU故障未修。'
           '完整rootfs132含936包/770模块/21,136条目反向metadata与内容零差异、双fsck、encoded UID10000读写及匹配四件套；完整userdata未全量刷入。'
           '两份可由稳定130 sparse完整重建的冗余raw删除3.63GiB，130 sparse/source/export和C128/129稳定源码/Image保持。15组功能边界和完整系统goal active。')
image = next(a for a in bundle['artifacts'] if a['role'] == 'rootfs')
body = f'''# 阶段132：MP2650持久节点、真实刷入与完整rootfs

2026-10-12。上一轮已完成隔离源码准备，属于progress；本轮全自动推进静态验证→完整构建→双分区刷入→真实新boot→连续采样及完整镜像。没有人工检查要求，完整系统goal active。

{summary}

## 实际补丁与验证范围

E118既有私有ext4卷中power132隔离复制稳定129源码和initramfs；驱动与129逐字节相同，没有新增充电配置写入。QUP1的既有i2c1节点保持400kHz，只新增无label的charger@5c compatible mps,mp2650；没有虚构IRQ/GPIO/电源引用。mps供应商前缀已在当前树。新增binding是本地候选，其示例维护者邮箱是占位值，尚未作为上游投稿元数据。

最初schema最小合法例被拒：dt-mk-schema输入漏了引用的power-supply.yaml，失败证据保留schema-test。补齐通用schema输入后，doc/mk无诊断、1正4反例符合预期，实际板级充电节点无诊断。libfdt逐项遍历新旧整树，仅多一个节点，所有既有节点和属性字节保持；不声称整块板的全部schema已验收。

#132 Image/DTB/770模块完整构建，所有模块可执行段与129相同，vermagic均匹配132，内嵌三个BT模块匹配，console 5:1/0600/root保持，其余cpio内容不变。module archive {next(a['sha256'] for a in bundle['artifacts'] if a['role']=='modules')}。

UEFI必须同步更新内嵌DTB，不能只改FAT中的samurai.dtb。canonical构建与压缩/FV/FFS/Android header检查通过，除DTB外所有可执行模块与实际129 boot一致；原固件源码/FD/FV/boot已逐字节恢复。boot尾部与新FAT仅Image/DTB两文件守卫通过。

## 自动部署与真实启动

新鲜当前129同boot抓取GPT18、NV6/source4/vendor1、persist、770旧模块及桌面/音频/SLPI守卫。首次旧preflash审计要求两个tracer都是0，与现机1/1不符；保留失败，改为记录初始合法0/1并由真正quiesce/freeze强制停至0，未绕过刷入前停止门槛。模块独立放入132 release，不加载至129；旧118/126/128/129目录不删。

BlueZ及桌面停止，DRM无userspace clients且CRTC inactive，PCM closed、双amp idle、所有remoteproc offline、追踪器0、来源/分区/新模块再次核对。fsfreeze成功后一次90 02 OUT收到F1；随后USB read I/O error随设备切换，未重发OUT/重启。fastboot独立核对同设备/product/分区几何，实际boot+logdump写回执通过并reboot。

SSH第16次有界观察恢复，无二次reset。真实#132、新boot身份、完整live DT节点/属性、boot/logdump/persist/GPT18/11来源和全部770模块通过。MP2650由真实DT启动自动绑定，未写new_device；属性0444，uevent有OF身份、ONLINE/status。标准BlueZ已自动启动，Phosh/Phoc和DRM/card1恢复，console warning0。

连续8样本42.132秒：ONLINE8/8=1、status8/8=Charging、电压8/8=4.400–4.475V、电流7/8=400.00–418.75mA，1份errno61 ENODATA，事件不丢。桌面PID不变/taint0/BlueZ running/Wi-Fi5180MHz，窗口所有故障计数增量0。新boot累计DPU frame done timeout4、UART reassembly2、GPU fault0；未施加GPU绘制负载，不能宣称GPU/持续显示修复。Charging是芯片状态观测，不是本机充电控制、功率预算、ADC外部校准或保护策略验收。

## 完整rootfs与空间

从已验130完整模板复制所有内容/类型/uid/gid/mode/link/xattr/devices，替换为唯一132 release的770模块，仅修改两个stage标记，936包/BlueZ DMS服务/default symlink/AutoEnable false/双频Wi-Fi profile/凭据/固件/UID10000 home保持。F2FS正确设备节点编码、稀疏完整payload与skip holes重建、两份raw只读fsck、21,136条目反向导出内容metadata零差异和encoded真实降权读写unlink通过。rootfs generation数值元数据首次沿用130，已修正生成器和finalize，重新只读验核，不重打包/刷入。

新rootfs sparse {image['bytes']}字节，SHA {image['sha256']}；boot {next(a['sha256'] for a in bundle['artifacts'] if a['role']=='boot')}；logdump {next(a['sha256'] for a in bundle['artifacts'] if a['role']=='logdump')}。四件套完整且hash实际重算，软件镜像可部署，完整userdata未bulk刷入/擦除；内核/设备树补丁与模块已实际部署。

两份130 raw逐一通过当前130 sparse全payload和空洞重建证明，inode/dev/size/mtime及无loop挂载重验后unlink，删除分配3895017472字节，无递归删除。稳定130 sparse/source/export保留，最新132 raws/export/template保留。C128/129 Image新鲜hash及源码/config保持，C未知旧对象不删，原WSL VHD未resize/compact。当前E118 inner余2188591104、E129 inner余1435234304；主机实际空余以host-space-validation.json为准。

## 下一项和失败边界

MP2650持久观测缺口已关闭，完整充电控制仍须补齐。已再次检索[MPS官方产品页](https://www.monolithicpower.com/en/mp2650.html)及[官方datasheet](https://www.monolithicpower.com/en/documentview/productdocument/index/version/2/document_type/Datasheet/lang/en/sku/MP2650GV/document_id/9664/)，下一轮核对本机原厂输入预算、2719/短路保护、热敏/NTC和battery limits，形成明确寄存器及恢复契约后实现/有界实测；不能直接拿eval-board或其它板默认值当本机配置。GPU131转储/CCU映射生命周期、DPU4/UART2另留档，避免重跑33场景/全桌面debug。15组中的物理camera/PM8008、GNSS真实fix、蜂窝数据/通话、指纹、休眠等继续开放。

所有一次性prepare/build/stage/quiesce/flash/collect/cleanup脚本均已实际执行，不重放。依赖工具生成与staging审计曾并发，导致一次verify脚本尚未生成，模块实际staging已经成功；后续只补审计，没有重放staging。私有现场仅E:/edk2-samurai-out及手机/var/lib/samurai，公开只保留统计与artifact hash。
'''
(r / 'sessions' / session).write_text(body)
for name in ['README.md', 'FLYWHEEL.md']:
    p = r / name
    text = p.read_text()
    first, rest = text.split('\n', 1)
    p.write_text(first + '\n\n' + summary + '\n\n[阶段132](sessions/' + session + ')。以下131及更早内容为历史，当前状态以上述132记录为准。\n' + rest)
p = r / 'DOCS-INDEX.md'
first, rest = p.read_text().split('\n', 1)
p.write_text(first + '\n\n- [阶段132](sessions/' + session + ')：持久充电观测实际刷入、新boot及完整匹配132四件套、冗余130 raw证明清理。\n' + rest)
p = r / 'linux-port/docs/HARDWARE-STATUS.md'
text = p.read_text()
first, rest = text.split('\n', 1)
rows = []
for line in rest.splitlines():
    if line.startswith('| 电池与充电 |'):
        line = '| 电池与充电 | #132持久QUP1/0x5c DT自动注册只读power_supply；42.13秒8份事件完整/ONLINE1/Charging，电压8/8，输入电流7/8另1份ENODATA，属性0444 | ADC外部校准、2719/短路保护/热敏/USB预算/失联与实际充电控制继续待办；Charging观测不能当控制验收 |'
    elif line.startswith('| 原生显示面板 |'):
        line = '| 原生显示面板 | #132新boot DRM/card1/Phosh/Phoc、taint0；启动DPU frame done timeout4，42.13秒空闲观察无新增 | 持续绘制/命令帧/休眠/长稳与GPU迟发fault未修，无负载0新增不能判修复 |'
    elif line.startswith('| 普通USB与OTG |'):
        line = '| 普通USB与OTG | #132实际boot+logdump刷入，一次冻结/F1/fastboot自动飞轮、新boot NCM/SSH/SCP恢复及GPT/persist校验通过 | OTG/USB3/休眠/长稳；保留同设备物理by-path守卫 |'
    rows.append(line)
p.write_text(first.replace('阶段131', '阶段132') + '\n\n' + summary + '\n\n[阶段132](../../sessions/' + session + ')。其余条目的旧轮次证据保留，不能扩大为本轮硬件验收。\n' + '\n'.join(rows) + '\n')
(r / 'NEXT-SESSION.md').write_text(f'''# Realme X2 Pro 继续检查点（阶段132，2026-10-12）

{summary}

先读[阶段132](sessions/{session})、reference/kernel132/complete-bundle-validation.json、persistent-power-validation.json及15组HARDWARE-STATUS。完整系统goal active，用户授权全自动搜索/源码/反编译/静态检查后刷入并日志验收，难错留档换项，无人工检查要求。

当前内核#132，release 7.3.0-rc6-rmx1931-samurai-k132+。新boot身份只取E:/edk2-samurai-out/kernel132/embedded-boot-id-private.txt或phone /var/lib/samurai/k132-first-runtime/boot-id-private.txt，132 source-boot-id是旧130/129 boot，不可再用于当前冻结。当前标准BlueZ运行、5GHz5180、Phosh/Phoc存活，MP2650 DT永久绑定，SLPI仍offline，观察窗口taint0。启动DPU4/UART2/GPU0仅新boot无负载状态，GPU131整体失败边界保留。

四件套全在E:/edk2-samurai-out/kernel132：boot-partition-k132-charger.img、logdump-k132-charger.img、modules-k132-private.tar.gz、samurai-rootfs-f2fs-k132-device-fixed.simg；全部真实hash见complete-bundle-validation.json。rootfs132为{image['bytes']} bytes/SHA {image['sha256']}，936包/770模块/21,136条目/双fsck/encoded UID10000验证。内核/DT/模块已上机，完整userdata未bulk刷入/擦除，稳定129/130等保留。

E118 20GiB既有volume挂载/home/cy122/pmos-samurai-kernel118，power132包含完整kernel/initramfs/modules-root；E129 16GiB volume挂载/home/cy122/pmos-samurai-rootfs129，rootfs132/image-export132-fixed/最新132两个raw及旧129/130 template/export。130两个raw已证明重建后删除，稳定130 sparse retained。C128/129完整源码和Image新鲜hash保持。后续操作E118/E129必须在同一次WSL调用先run各ensure helper，空闲退出会卸载，不根据旧/run锁或过去挂载判断。内余约2.19GB/1.44GB，不盲目clone或resize原WSL VHD。

prepare/source copy/build/schema resume/canonical firmware/stage/quiesce/freeze/flash/runtime collect/power sample/rootfs copy/pack/export/cleanup均已执行一次性，禁止重放。源码/设备树实际改变仅一个charger节点；MPS binding维护者邮箱暂为本地占位，投稿前需真实维护信息。UEFI原构建已恢复。131临时SDK随本次真实重启消失，已验私有归档保留，未改包数据库。

下一项继续完整充电功能：用已保留本机OEM源码/固件和官方MP2650 datasheet核对2719保护、热敏/NTC、2S电池限值、USB供电预算/失联和寄存器恢复契约，实施可自动验证的实际控制。永久绑定后不能继续运行旧new_device/delete_device脚本，也不能绕过i2c client busy强制访问。GPU/显示/UART难错留档后按新证据解决，禁止重跑旧33GPU场景。camera/PM8008/HAL/物理stream、GNSS真实fix、蜂窝数据/通话、指纹、休眠等不缩减，不把部分接口通过当完整系统完成。
''')
static = json.loads((ref / 'source-static-validation.json').read_text())
static.update(full_build_pending=False, actual_deployment_pending=False, actual_new_boot132_and_persistent_observation_verified=True)
(ref / 'source-static-validation.json').write_text(json.dumps(static, indent=2) + '\n')
print('K132_ALL_FIVE_CURRENT_DOCS_15_GROUPS_AND_NEXT_CHECKPOINT_UPDATED', flush=True)
