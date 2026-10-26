# 174：SLIM 端口中断停流、暂停回归与声卡重探测缺陷

2026-10-14。已部署 kernel174/logdump174，保留 boot172、DTB172、modules/software132、Mesa149、UCM173。端口中断补丁在声卡手工重新绑定之后，通过 8 次录音启停、3 次真实暂停/恢复，以及原生和桌面声学回归。首次启动的声卡重探测失败尚未修复；不能把本次回测写成正常启动或完整音频验收。

## 修改与软件验证

[增量补丁](wcd-port-lifecycle.patch)只改变 WCD934x：端口 IRQ 从 DAPM 上电移到 stream START/RESUME/PAUSE_RELEASE；先屏蔽、清理旧事件，再启用流和相应中断。STOP/SUSPEND/PAUSE_PUSH 先屏蔽对应端口，随后断开流并清理事件。更新只触及当前 stream port mask 的位，保留其它端口；寄存器设置失败返回错误，启动失败清理已分配流，停止失败仍尝试后续清理。

IRQ handler 对已经屏蔽的待处理端口事件只做确认，运行端口的 overflow/underflow 错误仍报告；读取失败不会使用未初始化值，错误端口屏蔽改为 regmap_update_bits。原厂同机型源码也检查中断是否启用，但其关闭等待机制与当前 SLIMbus API 不同，未照搬关闭等待。

[58 个实际 C 函数用例](host-tests-validation.json)覆盖 32 个端口编号、共享寄存器位保留、启动/暂停/恢复/停止顺序、8 个启动失败点、6 个停流失败点及 6 个 IRQ 读失败点。ASan/UBSan 通过；删去 STOP 屏蔽或 IRQ mask 检查的两个负对照都失败。checkpatch/diff check 通过；W=1 WCD 对象零警告。完整构建只有未修改 EUD 源的 inherited unused-function 警告。

[构建审计](build-package-validation.json)确认 DTB172、15 个显示源及配置保持；770 个模块与132兼容，仅两个模块的 build-id 不同。完整 FAT 回读、文件系统检查通过。只刷写 logdump，未重新构建或刷写固件；boot172 与 NV 在设备回读通过。Image174 SHA256 为 `4a074dff44498ae6fc366e9ff0a8896afe3d479038df50c8202051b8f66adff1`，logdump174 为 `2bd3cd106f7e20e14fac1d78529a8df60f2fc4e94870c1d4656c4df20c8676c3`。

## 恢复、首次启动失败与真实范围

在原172启动中读取 `/sys/kernel/debug/regmap/217:250:1:0/name` 触发 `regmap_name_read_file+0x54` Oops，taint128。故障属于读取前已运行的 kernel172，174未部署；原始日志保留私人目录，原因未修复，不继续重复读取该接口。受控停机后未刷分区，重新启动原172；[恢复验证](recovery-validation.json)确认 taint0、boot/logdump172/NV保持、UCM173默认 profile 自动恢复。

恢复时 fb0 blank 返回 EBUSY，CRTC仍 active。第一次显式 DRM disable 返回0，但关闭fd后 fbdev又恢复模式；没有把 syscall 成功当作显示已停。关闭当前启动的 fbdev_emulation，再用 DRM null modeset、关闭fd，连续状态检查才确认全部 CRTC inactive。该设置只属于停机启动，新启动自动恢复Y。两次切换均重新取启动身份、完成远程处理器/音频/显示停机和 F2FS freeze，一次F1收据后USB EIO，没有重复发送。

174首启14秒已检测WCD/初始化MBHC，约19秒 codec 重新探测后 `SLIMBUS_0_RX` 初始化报 -EINVAL，声卡消失，两个回测在读取声卡的前置条件失败，未发声。源码定位到 machine `jack_component` 保留旧 component；`samurai_setup_jack` 拒绝新 component，而 `jack_created` 也缺少卡生命周期清理。为何本次启动发生 codec 重探测仍需核对，不能未经证据称为已确认SSR。

另一个调查线索是未修改的 `drivers/mfd/wcd934x.c`：每次STATUS_UP使用非devm `regmap_init_slimbus`，失败、STATUS_DOWN和remove均未调用regmap_exit；DOWN只移除MFD子设备。需要核对regmap/debugfs与devm IRQ chip的状态/设备生命周期，这可能解释旧debugfs对象保留，但尚不能认定为本次Oops的已证实根因。

[一次 machine unbind/bind](card-rebind-validation.json)重建 card 私有状态并恢复声卡；之后所有174声学和停流结果都属于此恢复后的同一启动。不是自动重探测通过。后续永久修复须按 ASoC cleanup 顺序释放 jack：本树在 link exit 后才移除 component，card remove 位于 component remove 后；不能在晚期 card remove 中盲目调用已移除 codec。候选应覆盖 RX/TX共享、卡解绑/重绑定及失败清理，并补重新探测和启动回归。

## 实机回归

- [录音停止](capture-stop-validation.json)：8次FE录音，16/32/48kHz各有覆盖，后端按板级约束48kHz；每次帧数正确、RUNNING/closed见证。另用 libasound 同一PCM完成3次 PAUSED/RUNNING转换并读取暂停前后帧。所有SLIM trigger返回0，underflow/overflow/Port Closed、WARN/Oops/传输故障新增均0，mixer保持。
- [原生四例](dmic0-ucm174-low24-analysis.json)：左右编码能量相关系数0.9727/0.9856，目标功放关闭负对照差20.07/42.53dB，左右均检出。
- [桌面双向](desktop-acoustic-validation.json)：普通用户 paplay+parecord，经 Speaker sink/Mic source，左右相关0.9516/0.9633，对同启动原生功放关闭参考差18.99/41.46dB；sink/source volume和mute保持。不能据此评价人声音乐质量。
- [最终快照](final-validation.json)：538.8秒，taint0，underflow/overflow/Port Closed总数0，传输和内核故障0；保留首启ASoC注册失败1条。单Pulse CARD/alsa-card，HiFi (Mic, Speaker)，真实CARD两个jack off，PCM关闭，功放8/8启停配平且关闭/静音，17原控件恢复，NGD suspended，模块132/NV核验通过。

端口策略模块重启后缺失已解释：运行中 callaudiod 主动卸载 module-switch-on-port-available，并监测 sink/source 可用性选择端口。见[固定上游源码](https://gitlab.com/mobian1/callaudiod/-/blob/fe87a9267f1e074d19055d7a236e6b6f759af11d/src/cad-pulse.c)及[来源核验](callaudiod-source-validation.json)；本机二进制含对应卸载符号。173手工补载仅是当时现场动作，不代表应重复加载或改默认配置。实际耳机插拔/profile切换仍未验。

用户暂缺耳机，不重复询问。下一步优先 jack/card 重绑定生命周期和 debugfs Oops，再补人声音乐、瞬态、耳机实物、冷启动/休眠/长稳。当前174是手工恢复后通过功能回归的候选，完整目标保持 active。回退可用完整 boot172/logdump172+UCM173；171 SD1人工听音版本继续保留，不能用更早SD0组合替代。

私人证据位于 `E:/edk2-samurai-out/kernel174/k174-all-private.tar.gz`、两个声学包及恢复目录；手机 `/var/lib/samurai/k174*` 保留失败与恢复记录。公开目录只含脚本、补丁和脱敏结果。无新人工听音确认，无耳机实物验证。
