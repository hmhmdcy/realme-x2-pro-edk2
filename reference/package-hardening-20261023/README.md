# 2026-10-23：平台修复固化与蓝牙 APK 候选

本轮仅做离线审计、精确载荷打包和隔离目录验证；没有连接手机、使用SDK bind、构建整机、刷写、重启或启停设备服务。相机、充电/USB、NEXT-SESSION和其它会话产物不在修改范围。唯一公共配方改动是经主线审查的 `samurai-platform 5-r2`：显式依赖pulseaudio-bluez，19项源载荷及校验保持。现有rootfs已含插件，这不是新的蓝牙音频验收。

**第二轮纠正：这些APK的pre-install/pre-upgrade只是advisory检查。** 真实APK3在脚本返回失败后仍会提交载荷与包数据库，再返回错误并标记broken_script。首轮手工执行hook的“拒绝”不证明APK事务被阻断。原签名r0/r2保持不变，包内历史guard说明以本页及[真实事务报告](staged-rollback-validation.json)为准。唯一推荐的入口是APK执行前完成外部校验的显式事务；目前工具严格限于已注册的隔离root，不能直接用于手机。

**交付完整性事件：平台副本1已隔离，当前仅副本2有效。** 我的收尾脚本复用路径变量，把artifact-manifest JSON误写到platform-packages1的APK；该2301字节误写件不是APK，已移到私有scratch标记invalid，原目录只留QUARANTINED说明。未重建或覆盖副本2：其真实签名、19份实际数据块字节/签名mode及两个原package() staging重新核对全部通过。主引用改为platform-packages2；历史两构相同不代表当前两份仍有效。错误原因、SHA和时间见[事件记录](PLATFORM-INTEGRITY-INCIDENT.md)及[核对报告](platform-integrity-incident.json)，未部署。

## 固化与遗漏审计

| 项目 | 已有事实 | 本轮结果 / 待办 |
| --- | --- | --- |
| 音频173 helper、两UCM | platform配方内三文件逐字匹配173已验收清单 | 已有源码固化，不重复改路由；183音频离线清理属于内核，不能冒算作UCM包功能 |
| BT helper、地址助手 | 当前BT helper与234留档逐字相同，相关配方校验正确 | 锁定六项平台/桌面文件；完整连接/音频仍需设备验收 |
| 蓝牙185修复 | 当前363固定Git对象的hci_qca.c仍精确等于185修复后645ded49… | 使用当前k363三模块，不能安装旧k132模块；已有源码/构建证据纳入签名包 |
| 蓝牙204 RX wake/sleep | 当前363板级源码及后续启动链已带 | 记录来源，不打包任何旧boot、Image或DTB |
| TFTP206/207启动助手 | platform的samurai-wifi=854c9a8c…、MCFG助手=d4c62be6…与207canonical逐字相同 | 两项已在5-r1配方，无启动脚本遗漏，不重打包它们 |
| TFTP207程序 | b3bb82b9…有固定源、干净重建、真实QRTR和部署证据，但packages内缺更新服务程序配方 | 新增单程序采用候选和独立构建入口；文件owner仍待设备确认 |
| samurai-radio-tools源码配方 | platform依赖该包，仓库未给出完整对应APKBUILD | 当前包所有权和能否拆出TFTP需要现场核对；不能把缺配方等同于当前文件无人管理 |
| GNSS旧构建入口 | packages/README和apk3/build.py仍描述203并固定helper202 hash，而当前helper是2-r1 | 该入口会拒绝当前helper；不能当当前所有包的总构建器。本轮独立入口不复用它 |

原厂/公共依据优先复用项目已有固定源和本机产物：185主线QCA来源、204本机GPIO46/同平台PDC、363固定内核提交、TFTP固定linux-msm/tqftpserv与qrtr。未下载或替换原厂固件、NVM、配对密钥或个体校准。

## 已产出但尚未设备安装

全部二进制位于 `E:/edk2-samurai-out/package-hardening-20261023/`，用既有203私钥签名，主机私钥未复制。

| 文件 | 位置 | 状态 |
| --- | --- | --- |
| samurai-bluetooth-k363-0.1.0-r0.apk | packages-1/，另有packages-2/逐字副本 | 97310字节，SHA85fa43b6…bb6；只采用已有k363三模块 |
| samurai-bluetooth-k363-0.1.0-r1.apk | packages-r1/ | 99675字节，SHA5ce0b0e1…dbf6；封存候选，存在失败后timer恢复缺口，**不推荐部署** |
| samurai-bluetooth-k363-0.1.0-r2.apk | packages-r2-1/，另有packages-r2-2/逐字副本 | 100663字节，SHAf4a7d4eb…71b5；修返回值和失败后恢复，尚未设备PM验证 |
| samurai-tftp207-0.1.0-r0.apk | tftp-packages1/，另有tftp-packages2/逐字副本 | 394964字节，SHA2f11eb93…c1d4；只采用已有207程序和来源/许可证 |
| samurai-platform-5-r2.apk | **platform-packages2/**，当前唯一有效原始副本 | 12387字节，SHA49c5b034…5630；19份实际字节/签名mode重核通过；副本1误写已隔离 |

**这些是待当前设备状态确认的候选，不能无条件安装。** 实际文件owner、当前release、hash和canonical path尚未从本次设备读取，没有写replaces或使用允许覆盖任意包的参数。r0和TFTP脚本检查同字节，r2脚本还检查bluetoothd已停止且hci_uart未加载，但脚本失败不阻断APK提交，不能将其当安装闸门。必须在调用APK之前外部完成这些检查，拒绝时根本不调用APK；工具不代替主线执行服务停用/卸载。当前USB运输不可用期间不部署。

TFTP的 `/usr/sbin` 别名需当前设备readback。隔离root中额外测试 `/usr/sbin -> bin` 时APK采用成功、符号链接保持、canonical程序字节保持；这说明该别名受测试，不替代实际owner核对。外部package-manifest显式保留canonical/owner待查标记。

平台5-r2完整候选虽与配方源逐字相同，包含既有USB脚本源码快照。充电会话有当前运行时变更，安装前还须逐文件对比并协调；本轮没有把19文件的源码正确性冒认作当前手机全部载荷相同，也未安装平台包。

r0脚本遇到r2文件会返回失败，但直接原生降级仍会把文件和metadata换为r0并留下f:sS，真实隔离DB已重现。现在[staged事务工具](staged-bluetooth-transaction.py)已验证先外部校验、原子恢复r0模块字节，再请求原生APK显式r0版本降级；模块owner、版本、字节与错误标志必须全部通过后才记完成。独立坏状态也已通过明确repair-r0路径恢复，未直接编辑DB。完整步骤和边界见[回退说明](STAGED-ROLLBACK.md)；这仍不等于手机运行时回退通过。

## 已通过与实际边界

- [源和当前ABI审计](offline-validation.json)：六项配方载荷、185补丁、固定363源码、三个AArch64 ELF、vermagic/依赖/build-id通过。
- [r0包验证](package-validation.json)：两次独立签名构建逐字相同、验签、篡改包拒绝、实际APK隔离采用、全文件mode/root owner通过；实际工具运行的钩子接受同字节k363，拒绝旧release、异机与1字节漂移；旧185 k132模块由ABI守卫拒绝。
- [r2包验证](pm-r2-package-validation.json)：两构相同、验签、隔离root真实APK r0→r2成功且仅hci_uart模块变化；钩子拒绝模块仍加载、daemon运行、进程查询错误和安装后重复切换。进程/模块状态为明确模型，不是设备服务验收。
- 上述r0/r2“钩子拒绝”只表示手工hook返回非零，旧事务使用no-scripts，不能证明APK拒绝提交。[第二轮真实事务](staged-rollback-validation.json)另验证原始带hooks的成功与失败提交，外部四类拒绝均未invoke任何APK、未改bytes/DB，r0→r2→恢复字节→r0完整闭环及脚本失败状态恢复通过，最终f:S而不是错误f:sS。
- [TFTP包验证](tftp-package-validation.json)、[目录别名验证](tftp-alias-validation.json)：两构相同、验签/篡改拒绝、实际APK采用、程序字节/权限保持、异机及漂移拒绝。207实际QRTR功能结果沿用既有同字节证据，未重跑设备事务。
- [平台依赖验证](platform-dependency-validation.json)、[平台签名包验证](platform-package-validation.json)：仅pkgrel/depends变化，19源checksum通过；实际执行package()，历史两次签名构建逐字相同。副本1后被我方脚本误写，当前仅副本2有效；副本2的签名、19份实际payload字节/签名mode、完整depends与无脚本均重新核对通过；未安装。

r0首次直接用APK3 extract时遇到265已记录的共享祖先目录表限制，两次失败日志保存在独立WSL验证目录；随后改用实际APK installer完成采用与全文件核验，没有把提取失败记成通过。

配对、BR/EDR/LE连接、A2DP/HFP、外部事件唤醒、phase5启动问题及PM长期恢复均不能据这些包的离线验证认定完成。r2还须主线补丁审查和受控设备窗口。没有相机或充电设备验证。

## 重建入口

`audit.py` 可只读核对既有模块归档；`--root`可只读核对明确的已挂载/staged root。`build-apk.py`、`build-tftp-apk.py`接受显式已存在私钥/公钥目录，输出到全新独立目录，均不安装或访问手机。原始模块和TFTP程序均在已有私有目录，不复制到公开源码。

蓝牙来源及源码重建边界见[REBUILD](REBUILD.md)；r1/r2的模块哈希、补丁、构建与模型快照分别在candidate-r1/、candidate-r2/。TFTP的[独立APKBUILD](samurai-tftp207/APKBUILD)仅封装已有可信207二进制，完整二进制输入保存在私有tftp-abuild-inputs/；abuild路径未执行，实际APK由独立Python签名构建器产生。源码重建继续复用 `linux-port/radio/build-tftp.py` 和已验证的十文件原始缓存。
