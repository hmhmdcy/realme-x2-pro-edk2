# session103：MAX98937原生声卡、有限PCM与全零麦克风

2026-10-11，已真实刷入Linux #102，boot/logdump两分区及EDK2内嵌DTB读回一致。原生Realme X2 Pro声卡注册，FE播放MultiMedia1和采样MultiMedia2、QUAT_MI2S_RX与WCD934x SLIM收发后端已接入。

两颗MAX98937均读revision0x43，左右GPIO148/37由正确驱动独立拥有，空闲复位解除但global00/amp80。驱动先ID验证、无寄存器缓存、只允许核实的寄存器图，任一I2C配置错误置failed并复位，devm失败/卸载/shutdown关闭。原厂GPL MAX98937的55项表按真实enum逐地址生成，保留thermal warning75/shutdown8c/hysteresis08与brownout配置，数字44/PCM模拟1采用原厂无DSM保守值；禁止任意增益用户接口，没有OEM DSM/misc共享static实现、没有校准或NV写入。没有把MAX98927地址作偏移移植。

低级播放实测：48000Hz/stereo/S16_LE，峰值128/32768（-48.16dBFS），2秒1kHz并带渐入渐出，960帧/4period满足原生DSP对齐。tinyplay退出0/错误空，耗时1.97秒；两颗功放各starts1/stops1，关闭后global00/amp80/powered0/muted1/failed0，PCM closed。**无人在场听音，不能宣称扬声器物理声音、音质、DSM或大功率长期保护已验收。**

采样实测：AMIC1/ADC1/DEC0/TX0，以及按原厂handset-mic修正选择的DMIC0/DEC5/TX5，各录241920帧、48000Hz/mono/S16、5.04秒。live状态RUNNING，首轮hw_ptr/appl_ptr47039，period960/buffer3840；正常关闭且错误空，但两份PCM全部0，SHA `e679d4670636dba8edb11cf198762f27ea4eb979dc6c8647209096084905881c`。**DMA转动通过，真实麦克风信号未通过。** 原厂private mixer路径证据和官方19781音频DTS表明数字麦克风需要偏置路径；当前card仍有初始AMIC1 Handset Mic关系，缺DMIC0/1 Pin与MIC BIAS1连接。先修该缺失再实测，不能仅凭源码断言它是全零的唯一原因。私有录音不上传或公开。

原生版本查询在首次collector中报错，保留partial；retry1记录exit1/error，不能当服务API成功。当前DSP/ALSA和PCM RPC可用；只做一次普通q6core解绑/重绑（两PCM closed、功放关闭、精确service@3身份），之后查询仍失败；**无ADSP/MPSS强制崩溃或重启，未证明仅为早期缓存。** 下一轮需观察实际APR opcode/status/payload，再决定修复。

无线回归：首次自动MPSS up47.486181秒、worker结果0，本轮没有manual恢复；checkpoint uptime1005.42秒/MPSS持续957.933819秒。5GHz认证/DHCP/路由/DNS/577B HTTP、网关3/3通过。临时私人连接profile未内嵌。阶段102/103邻近两次暖启动成功，initramfs/无线源/固件逐字节不变，不宣称历史40秒fatal、2.4GHz reason7/删除等待、冷启动/休眠/长期稳定已修复。

蓝牙附近扫描历史保留；本轮正常stop后HCI为空，不配对连接；phase2错误2。振动ID97/standby/starts0/error0，无新播放，用户无人测试，机械确认暂缓。两个DSP running/fatal0/taint0/SMMU fault0；显示frame-done timeout2保持开放，旧85–88快照保留。

完整核验：240文件checkpoint SHA `c97b8765c3c5e704ef29e845e4b3f1ec2bbc3aca9a8c8ca80f409b0506057826`，六个原包逐字节一致且nested manifests纳入外层清单，首个runtime/首个checkpoint partial保留；80块2MiB/8192Kbit/s完整备份和boot/logdump读回、实际FDT仅五个合法UEFI chosen字段差异、initramfs/原模块/六NV源/persist/stock DTBO保持。新增音频服务/card/pinctrl节点、正确功放compatible/vdd/channel/prefix和4个音频config变化；其它已修改源码保持。EDK2只变DTB FFS/容器，EUD/F1/compat/shim/ramdisk/执行代码保持。

Image `c730a9d7ebe73aff8b393c4940be03e196c365b2ceec750872bb99334be2b82e`；DTB `e6350842005bed457f5545650ef068ba08c464f47a5d54b937c55539f7d90b99`；CPIO `71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7`；boot `301a958c440cadecd8d465c7c3f1918860b61fc0ee665410bc3632f9a45e3048`。

构建/调试边界：首轮默认PATH遗漏原Rust检测器，元数据变化触发guard，完整保留并恢复原PATH重建，最终仅音频config变化。canonical漏识别slim-ifc-dev导致phandle数值差异，改为校验唯一同一IFD目标，未忽略节点差异。首次tinyalsa误将-static用于shared目标失败，保留原日志，固定v2.0.0源码的静态archive/四ARM64工具通过。首次fastboot检查在F1切换时尚未枚举，没有写分区；独立确认后用新prefix刷机。postflash EUD首次attach过早失败，原生日志设置com-up后两次15秒捕获并释放，完整内核证据在NCM包中。旧tinymix省略contents命令只打印usage，旧tinypcminfo路由未启时EINVAL/错误方向ENOENT保留，实际播放/采样用明确路由与设备。首次collector在版本查询处退出，重放因目录guard停止；UUID本身有效，并非已证明熵故障。checkpoint首次假定extra模块目录失败；retry1外层find错误排除nested SHA清单，retry2只排除自身SHA清单后240文件全验。首次采样审计要求非零，真实全零触发失败；保留失败数据并明确登记信号未通过。

原厂GPL驱动参考：[固定Realme MAX98937实现](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/audio-kernel/asoc/codecs/max989xx/max98937.c)。SM8150资源/[0x1b21 strict SID](https://github.com/ClearStaff/linux-sm8150-mainline-hotdog/blob/403b56c33e2ccdda25d90378970a5e5b928dee19/arch/arm64/boot/dts/qcom/sm8150.dtsi)与同机OEM SID互证，不套SDM845 0x1821、不旁路SMMU。工具为[tinyalsa固定v2.0.0](https://github.com/tinyalsa/tinyalsa/tree/1c5fb68ced57d838f2b7ecd0c00bc1fefc9ab60d)，Android BSD许可证；二进制仅私人。

15组硬件目标继续，下一轮先数字麦克风/电源与APR响应取证。充电不重跑旧OEM/NV/OTP/unseal/FET/OTG/MCU/I2C_FORCE探针，NV仅RAM COW；Android/data/GPT/原NV/persist/SSH/rootfs01/F2FS保持。没有提交推送；固件、原DTBO/XML/库/日志、身份/凭据/录音/镜像/二进制只私人目录。
