from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214')
assert json.loads((here/'baseline-validation.json').read_text())['taint']==0
assert json.loads((here/'previous-evidence-recovery-validation.json').read_text())['whole_archive_and_all_members_verified']
(here/'README.md').write_text('''# 214：恢复连接，构建完整相机包（进行中）

前一轮属于实际进展：213同步暗场RAW与固定白输入对照证明了首帧ISP缺陷及候选修复。本轮重新发现USB邻居后，原密钥连回同一启动/原模型/内核183、taint0；scoped地址未变，尚不能据此确认此前超时的根因。[新鲜端点](fresh-endpoint-probe-validation.json)、[选择](transport-selection-validation.json)。

213私人归档已按64KiB续传，原2MiB前缀、完整归档和全部227个成员均核对通过。此前截断、USB/Wi-Fi超时和213最后复查失败保持为真实历史；恢复不等于USB大传输稳定性已修复。[回收](previous-evidence-recovery-validation.json)。

214随后完成新鲜完整基线：三个DSP running，相机三设备休眠、VDIG/VANA释放、测试图案关闭，taint/五类fault0，GPS0/Signalsfalse/rate30、蓝牙关闭无连接。相机三包仍99990.7.2-r4，库/配置和包数据库与213原备份逐字一致，额外保存48份原文件记录；本轮未安装产品或切换启动。[基线](baseline-validation.json)。

已建立独立宿主Alpine/aarch64构建root，用QEMU10.2.1执行ARM GCC15.2.0，不占用手机编译。原配方auto/virtual pipeline、所有子包、六个补丁、tuning/desktop输入保留，加入三个已验证相机补丁；0010仅增加可选外部IPA私钥选项，默认空值仍按上游生成。配方固定4个编译任务，使用保留的私有IPA输入，strip后重签IPA；APK沿用203签名密钥，未重新生成。[配方](../../linux-port/packages/libcamera/README.md)、[构建环境](build-environment-validation.json)。

第一次完整构建因我把新增校验和追加到尾部、与source中的插入顺序不符而停止；文件独立SHA512都正确，已修复位置顺序。第二次配置发现libyuv-dev只有头文件、没有未版本化运行库，补入签名libyuv包并加入显式构建依赖。两次失败日志保留；第三次在现有源码继续，当前正在编译，不能先写成构建/安装通过。[顺序修复](checksum-order-repair-validation.json)、[依赖修复](libyuv-dependency-repair-validation.json)。

CPU配置、两个heap模块自动加载及video/uaccess/专用FastRPC拒绝规则另有samurai-camera-config配方，payload与既有配置相同，目录0755/文件0644；固定相机栈子包已定义。源码同步清单也补入此前遗漏的linux-port/camera目录，最终同步检查待本轮源码稳定后完成。[配置配方](../../linux-port/packages/samurai-camera-config/APKBUILD)。

下一步完成真实构建及签名/依赖/文件清单验证，再做手机安装预检、可回退事务与默认用户客户端验收。关灯条件继续有效，RAW读前后必须DMA同步；不以暗场RGB全零直接判bug。前摄完整16MP/图像质量、传感器TPG位宽/控制延迟、后置四摄、GPU ISP及GNSS/蜂窝/蓝牙/传感器/电源/完整rootfs目标保持开放。
''')
path=repo/'NEXT-SESSION.md';text=path.read_text();old=text.split('\n\n')[1]
text=text.replace(old,'2026-10-16，阶段214进行中：重新发现USB邻居后连回同一启动，213归档227成员已完整回收核对，新鲜基线干净。完整相机r5配方保留原功能，正在宿主QEMU/ARM环境编译；手机仍r4，未安装/刷写/重启。完整外设goal active。[214进展](reference/kernel214/README.md)、[213对照](reference/kernel213/README.md)、[边界](WORKING-BOUNDARIES.md)。')
start=text.index('- 当前运输');end=text.index('\n',start)
text=text[:start]+'- 当前运输reference/kernel214/host.py，guard为/var/lib/samurai/k214-baseline/boot-id-private.txt；新鲜核验同212启动、3DSP running、相机休眠/供电释放、taint/五fault0。213图案/链路保持恢复，库和包数据库原样，48份原文件记录已备份。214完整包仍在宿主编译；212/211所有marker已闭环，不可重放。'+text[end:]
old='213证据回收时USB第三个1MiB块截断，随后小SSH也超时；';start=text.index(old);end=text.index('\n\n',start)
text=text[:start]+'213的USB截断及随后USB/Wi-Fi超时保持。214重新发现USB邻居后，同一scoped地址可达并通过原密钥/原guard；64KiB续传已核对整个归档及227成员，随后完整健康基线通过。原因尚未证明，不能称大传输稳定性已修；用214当前端点和guard，设备变更前做新鲜检查，不重放旧切换。'+text[end:]
text=text.replace('前摄下一步整合libcamera0.7.2原六补丁与linux-port/camera/libcamera/的三补丁，保留原auto/virtual pipeline、其它IPA/代理、工具、tuning和签名依赖，完成可复现包/部署后验默认客户端。','前摄r5完整配方在linux-port/packages/libcamera，保留原auto/virtual、全部子包/IPA/代理/工具/tuning；三个已验证补丁外增加可选外部IPA密钥构建项和显式libyuv依赖。当前宿主QEMU/ARM编译中，CPU/heap配置也已配方化；完成签名/依赖/文件清单及安装预检后部署，验默认客户端。')
path.write_text(text)
path=here.parent/'kernel213/README.md';text=path.read_text();text+='\n214后续：重新发现USB邻居后连回同一启动，64KiB续传已核对完整归档和227成员，随后完整基线干净；本轮原失败记录不改为通过。[回收证据](../kernel214/previous-evidence-recovery-validation.json)、[后续基线](../kernel214/baseline-validation.json)。\n';path.write_text(text)
path=repo/'linux-port/packages/libcamera/README.md';text=path.read_text().replace('独立宿主ARM/Alpine环境','独立宿主QEMU模拟ARM/Alpine环境');path.write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(device_guard='/var/lib/samurai/k214-baseline/boot-id-private.txt',device_transport='reference/kernel214/host.py fresh strictly authenticated same USB scoped endpoint',state='Fresh same-boot USB neighbor discovery recovered access;213 archive all227 members verified via64KiB transfer, new214 full baseline clean/original camera r4/database unchanged/48 file records backed up. Full-feature r5 abuild-r3 compiling under host ARM QEMU; source checksum order and explicit libyuv dependency repaired after two terminal configure/input failures.',next='Observe existing active-camera-build PID/log and exec session, do not restart on observation timeout. Finish all-feature package build; build config stack; verify signatures/keys/dependencies/payload and reproducibility; preflight/install reversible camera transaction and default UID10000 capture. No flash/reboot planned. Full peripheral goal active.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('214 checkpoint records recovered227-file evidence, fresh clean baseline, and live host full-feature build; goal active.')
