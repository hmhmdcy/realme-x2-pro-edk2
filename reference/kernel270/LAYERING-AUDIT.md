# RMX1931适配层次与升级依赖审计

后续[273](../kernel273/README.md)已加入主摄GW1/C-PHY并部署r21/r16，现三颗后摄可原生取流；控制切换、AF/Spectra和SSC开机失败仍未完成。本文其余源码规模、包数、身份和审计结果属于270阶段。

后续271已更新细分增益模块、r20/r15配方及camera部署/源码锁，修复本文当时发现的锁落后问题；最新状态见[271](../kernel271/README.md)和根检查点。本文其余数字和“当前”描述属于270审计时点，不替代后续部署记录。

2026-10-18。核对本地Linux/EDK2源码、构建与部署收据，并以270当前启动补做只读检查和用户确认场景后的有限相机采集。没有更新或刷写内核/固件，没有开展新内核版本迁移测试。

判断：已经达到主线内核架构上的SoC驱动、板级描述和标准用户态联合适配阶段，多个功能实际可用；尚未达到上游原生支持、发行版完整集成或零补丁更新阶段。完成度需要同时看功能、代码分层、上游接收、部署一致性，四者不能互相代替。

| 层面 | 当前证据 | 维护边界 |
| --- | --- | --- |
| 引导 | 原厂XBL/ABL→BootShim→EDK2→外置EFI-stub Image→Linux rootfs；FAT logdump保存Image，DTB来自UEFI配置表 | 仍有samurai专用BDS、启动参数和显示交接逻辑；不是完整发行版内核安装链 |
| 固件 | EDK2按本机内存/显示/按键/UFS适配；270只改变内嵌DTB，固件可执行代码不变 | 依赖Qualcomm/OPPO DXE及modem/DSP/Wi-Fi等固件；UEFI持久变量、本机完整ACPI仍开放。Linux主要走DT，借用cepheus DSDT不是本机ACPI完成 |
| 硬件描述 | SM8150公共资源与RMX1931 DTS、sensor dtsi、regulator/pinctrl/CSI endpoint/reserved-memory；若干binding schema通过 | 覆盖已接入硬件，不等于全树binding验收或全部接线确认；DTB仍内嵌boot固件，更新DT要重打包boot |
| 板级 | 真实电源、GPIO、方向、时钟和连接逐步下放DT/设备包；SSC方向通过标准ACCEL_MOUNT_MATRIX配置 | 仍有专用sensor-power sysfs及C内电压策略；公共pinctrl直接处理本机面板GPIO6复位，属于待继续评估的跨层逻辑。板级ASoC machine driver本身是正常分层，不因带机型名就判为不合理 |
| 内核与驱动 | 基于固定Linux7.3-rc6祖先a90ee4305；最新samurai-multicamera270为edd2e8c14，本地源码干净 | 相对祖先25提交、125文件、+12960/-1111，包含SoC/通用驱动/诊断/板级描述；不是仅补一份DTS。未见本轮改动上游接收证据；intree表示在此构建树中，不证明已合入Linus树 |
| 用户态 | 标准Phosh/Phoc、V4L2/MC/libcamera、PipeWire/GStreamer、ModemManager/GeoClue、SensorProxy等；应用通过公共接口使用硬件 | libcamera配方23补丁（含既有发行版补丁）、PipeWire额外6补丁、MM/GeoClue/libssc适配及本地Mesa修复；关键组件存在版本绑定和CPU回退，仍有维护成本 |

源码规模来自本地`git diff --shortstat a90ee4305..edd2e8c14`和`git rev-list --count`，不把增加行数直接视为代码质量评价。分支名upstream只是目录命名。270两提交本地未发布；发布到个人fork也不能代替子系统维护者接收。

**已做的底层收敛有实际内容。**

- [267](../kernel267/README.md)：双PM8008归公共MFD/regulator，IMX319用标准compatible与资源接口；GPIO/电压/接线进DT，撤实验供电与板级reset provider。已有模块和新DTB实机取流。
- [269](../kernel269/README.md)：删除五个废弃OF实验helper；把RMX1931 IOVA保留策略从公共SoC描述/驱动移到板级树，CAMSS保留通用DMA边界检查；自定义trace改动态调试。最新统一内核候选已编译，未部署。
- [265](../kernel265/README.md)、[268](../kernel268/README.md)：修PipeWire/SPA/Gst共享缓冲所有权及libcamera跨进程MC链接缓存；标准应用不再依靠私人库或应用复制开关运行。公共代码修复仍是下游补丁，需要上游维护流程。
- [270](README.md)：S5K3M5改标准compatible、按输入时钟选模式、DT管理电源，已有真实采集和实景；寄存器模式表来自同机OEM数据。

**现机与完整候选仍有明显差异。**

目前boot270/Image183，release为7.3.0-rc6-rmx1931-samurai-k132+，774模块/961包；若干模块按Image183匹配构建后增量替换。269同提交Image/DTB/773模块完整W=1构建成功，尚未上机；相机诊断0，全树记录1140条诊断未完成分类。完整最新rootfs未闭环。现机[只读核对](runtime-layering-validation.json)仍有clk_ignore_unused、pd_ignore_unused、regulator_ignore_unused；说明整机资源依赖与电源管理尚需脱离bring-up保留策略验证。/boot为空。

源码/部署清单还需统一：根检查点已是270，camera/deployment-lock.json仍269，camera/kernel/source-lock.json仍223；这些旧锁可以保留历史价值，不能单独作为最新整机复现清单。249公开复建覆盖其固定用户态候选，不等于可复建当前270整机。

**硬件能力有实测，也有重要缺口。**

显示、触摸、Wi-Fi、音频发声/拾音、传感器、GNSS室外定位、蓝牙扫描和前/后摄均有分项实测。尚有默认GPU故障、充电控制闭环、真实SIM业务、指纹、NFC实际读卡、休眠/冷启动/长稳等开放项，详见[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。历史modem watchdog未因当前fault0而视为修复。

本次新场景下IMX319/S5K3M5各36帧与JPEG通过，长焦原图可辨认真实场景，但明显欠曝和噪点重；24组配对RAW/RGB证实曝光响应。主摄GW1仅完成数据交叉核对。路径为CSIPHY/CSID/VFE RDI采集RAW＋CPU软件ISP，Spectra硬件成像处理未接通。[实景核看](scene-r2-optical-review.json)、[资源回收](scene-r2-health-validation.json)。

**对更新的判断。**

普通用户态包已有升级能力：[本次full upgrade](../full-upgrade-20261018/README.md)升级55包、新增3依赖；但保留相机/GNSS关键约束和Mesa修改，未升级内核。它不能证明关键栈任意更新或跨内核版本兼容。libcamera/config与PipeWire core/SPA/Gst仍需要配套更新；发行版Mesa更新可能覆盖本地库修复。

现状不能直接换无补丁主线内核并保留既有全部功能。未上游的驱动/修复必须移植并重新编译模块；Linux不保证内部驱动API/二进制模块ABI长期稳定，参见[内核官方说明](https://docs.kernel.org/process/stable-api-nonsense.html)。EFI统一了入口，不能补齐操作系统硬件驱动。[DT稳定binding约定](https://docs.kernel.org/devicetree/bindings/ABI.html)有助于固件与内核解耦，但前提是binding与对应驱动得到维护。

接近最小补丁更新的后续工作：先统一当前Image/DTB/模块/rootfs与清单，消除未归类诊断并实机回归；再将通用缺陷、SM8150支持、芯片驱动、板级DTS、诊断分别整理，逐项争取上游接收；把设备配置/固件/调校独立打包，关键用户态修复进入上游或维护小型补丁队列；打通发行版内核/DT/initramfs安装和回退；最终以新内核版本、关键包更新及完整冷启动/PM/功能回归证明更新兼容，不能仅凭构建成功承诺。

**原厂资料可以用于调校，但要按数据类型转换。**

项目已有[19781下游设备树摘录与来源说明](../../linux-port/docs/ANDROID-DT-REFERENCE.md)、本机vendor sensor BIN及[独立S5K3M5解析](../kernel239/s5k3m5-crosscheck-validation.json)。供电/CSI/时钟进DT；模式、曝光/增益寄存器及单位转换进sensor driver/libcamera helper；黑电平/白平衡/CCM等应按当前SoftISP支持情况形成调校数据；EEPROM/OTP逐模组校准需先识别格式和实际模组。原厂CamX/Chromatix二进制不能直接当libcamera YAML载入，原厂Spectra算法也不能凭DTS自动获得。

当前长焦应先验证寄存器曝光/模拟增益的实际响应与单位、帧时序/裁剪/RAW位深和CFA，再调整AE与色彩。不能把RAW信号过低用gamma强行拉亮当作修复。引用原厂值时记录固件版本/模组/模式并与实机结果交叉验证，旧源码、不同供应商模组和其它ISP的参数不能直接混用。
