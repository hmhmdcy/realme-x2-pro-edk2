# 19781 原厂 VOOC / SuperVOOC / FFC 离线恢复

本轮补齐了一个可复用的小组件：**固定原厂源码的 STM8S 固件格式校验、条件镜像识别及七位接收消息分类器**。它只读取本地文件，输出元数据；没有 GPIO、I2C、回复、固件更新、升压或充电控制接口。未访问手机、SSH、USB、SDK、共享源码/build，未改现 R8、白名单或 APSD helper。

输入优先使用 kernel83 已缓存的同机 19781 Android R DTS、充电管理及构建配置记录；缺少的 VOOC 驱动/固件头只定向取得[同一官方固定提交](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/tree/23172a1571bd91156032cc9fef16284a82b63d2c)。新取得 12 个文件的路径、URL、字节数和 SHA 见 [source-manifest.json](source-manifest.json)。未将旧 Android 源或近型号数据混作本机实际状态。

原始源码（包含内嵌固件数组）、生成的 C 数组参考和测试二进制均只保存在 `E:/edk2-samurai-out/charging-management-20261023/oem-fastcharge-private/`。公开目录保留解析/提取/测试脚本、哈希及脱敏报告；[privacy-migration.json](privacy-migration.json) 记录原件字节不变的迁移。迁移只改变离线缓存位置和测试输出目录，不改变解码语义。

## 已恢复的本机源码链

| 环节 | 固定原厂依据 | 恢复结果与边界 |
| --- | --- | --- |
| MCU 节点 | `19781/sm8150-pmic-overlay.dtsi:438–505` | `qupv3_se15_i2c` 上 `oplus,stm8s-fastcg@26`，fw type `0x22`，4.4V 标志、normal charger path、multistep enabled；温度 `[120,430)` deci℃、UI SOC `[1,90]` |
| 实现选择 | `oplus_vooc_fw.c:77–92,583–744`；`oplus_stm8s.c:721–732,922–938` | ASIC ID 和 MCU ID GPIO 在此节点都未声明，原厂 fallback 选择 STM8S；RK826/RT5125/OP10 驱动共存并不证明本机采用它们。这里恢复的是 DT/软件选择，不是当前 IC 丝印或实物查询 |
| 固件选择 | `oplus_vooc_fw.h:113,4605–4995`；`oplus_stm8s.c:838–842` | `0x22 = VOOC_FW_TYPE_STM8S_4400_SVOOC_5000MA`，选 `Stm8s_fw_data_4400_svooc_5000MA`。名字里的 5000mA 不能作为现有输入预算或电流许可 |
| DP/DM 路由和握手 GPIO | overlay `499–505`；`19781/sm8150-pinctrl.dtsi:5306–5409` | TLMM switch1=59、reset=131、clock=92、data=93；八种 active/sleep pinctrl 及上下拉已提取。`switch_fast_chg` 在 `oplus_vooc_fw.c:1112` 开始执行 MCU reset/clock/switch 操作，不能只注册 DT 就启用 |
| 分压/普通充电器 | overlay `416–420,353`；`charger_ic/Makefile:96–99` | 同 bus `oplus,da9313-divider@68`；MP2650 位于另一个 I2C bus `qupv3_se1_i2c`、地址 `0x5c`。SM8150R 分支包含 DA9313、MP2650、msm8150Q board glue。DA9313 改模式受 `allow_reading` 门控（`oplus_da9313.c:208–239`），不是可独立盲开电源 |
| 供电证据 | 完整 MCU 节点及 `stm8s_driver_probe:693–914` | 节点没有显式 regulator supply，probe 也没有已恢复的 regulator enable 路径。不能据此猜 MCU 电压/电源轨，或宣称当前 rail 已供电；DT 地址不是原理图 |
| 启动条件 | `is_allow_fast_chg_real`，`oplus_vooc_fw.c:1041–1071` | 原厂必须 DCP、温度和 UI SOC 符合范围且没有 fastchg_to_normal。USB SDP/CDP 均拒绝；这一 gate 是必要条件，仍不等于兼容适配器、电缆握手成功或安全许可 |

完整可机读 DTS 属性、pin 原文、各输入 SHA 见 [config-result.json](config-result.json)。特别是 Android R 的 `qcom,vooc_fw_update_newmethod` 在 overlay **被注释**；旧 9668 缓存中启用此属性的状态不能直接复用。当前节点也没声明 `vooc_reply_mcu_bits`，源码 `oplus_vooc_fw.c:325–328` 默认 4；开启 multistep 后使用该分支。回复仍包含电芯类型等原厂上下文，本组件不生成回复。

## 固件解析交付

[fastcharge_codec.py](fastcharge_codec.py) 精确区分 `CONFIG_OPLUS_SM8150R_CHARGER` 的两个同名 C 数组分支。不能用首次正则匹配随意选择，或只看到相同 `0x22` 就忽略编译条件。

| 条件 | 大小/记录 | 原厂版本字节（末尾第 4 字节） | 镜像 SHA-256 |
| --- | --- | --- | --- |
| SM8150R 定义 | 6460B / 190 | `0x18` | `aa14367c829c32f9be333e23fc1f645da9e97c832b932030d64637e421ccd976` |
| SM8150R 未定义 | 6460B / 190 | `0x3c` | `8fe4c61b2b7ce600e149d65d7db08e6a5649d163371c993665a9c9c9e9ca2dd1` |

已有第三方 `samurai_defconfig:408` 声明 SM8150R=y，且旧 source audit 确认了这一选项；这不是新取得的原厂生产 `.config`，也不证明当前 MCU 内固件是 `0x18`。因此两分支都保留、都测试，不将当前 MCU 版本伪造为已知。

原厂 `stm8s_fw_write:353–404` 与 frontline/lastline 检查表明记录为 **2 字节小端 Flash 地址 + 32 字节数据**。编程时原厂把地址两字节倒成高字节在前，再拆成两个 16 字节数据块发送；本工具只解析文件，绝不发送。两镜像地址首 `0x8800`、末 `0x9fe0`，从 `0x9f80` 到 `0x9fe0` 有 64 字节未表示区间，不能强行补零或认成损坏。版本位于文件 offset 6456。解析器检查完整记录、范围、对齐和严格递增地址，可再与选定固定镜像逐字节比较；**未恢复出独立 MCU 校验和/签名算法，SHA 只校验本地源镜像一致性**。

可调用纯函数 `firmware_branches()`、`inspect_stm8s(data, expected)`，或对已存在的本地 bin 使用：

```
python fastcharge_codec.py firmware LOCAL_FILE --sm8150r yes
```

这个 CLI 只接受有界本地普通文件；不搜索设备，不读 MCU，不导出刷写命令。没有匹配固定镜像即拒绝。它不是泛用未知 MCU 固件验证器。

## 七位消息分类交付

原厂 `oplus_vooc_fastchg_func:889–931` 按 MSB-first 累计 **7 bit**；普通通知第三个 bit 后要求头部 `101`。等待 MCU 版本、适配器版本或适配器型号时例外。已恢复通知为：`52` present、`54` absent、`58` IIC-reading window、`5a` normal-temp full、`53` low-temp full、`56` firmware-version request、`59` bad connection、`5c` temp over、`5b` adapter firmware update、`5d` BTB over、`5e` adapter-model request。

分类器明确接受 `normal / adapter_model / mcu_version / adapter_version` 上下文，并复用源码真实分支优先级。例如 pending adapter_model 时，`0x58` 是型号 payload，`0x52/0x54/0x5e` 仍先走通知；pending MCU version 时 `0x5b` 可以是版本 payload。这防止把所有字节查通知表、误解为握手事件。无上下文普通帧不满足 `101` 即拒绝，合法头未知命令标为原厂 data_error。型号码 `0x0f/1f/3f/7f` 的错误分类保留。

```
python fastcharge_codec.py frame 1010010
python fastcharge_codec.py frame 0011000 --context mcu_version
```

这些是**构造的接口示例**，不是从手机采集的报文。分类器不推进充电状态、不产生 GPIO 时序或 reply、不允许某次 IIC 窗口访问当前保护查询总线 owner。

`opchg_read_ap_data`（`oplus_vooc_fw.c:1163–1173`）每读一个 bit 都会主动驱动 clock，再延时采样 data；它不是可随意启动的被动监听 API。`stm8s_get_fw_verion_from_ic:490–538` 会切 clock/reset、进入 MCU boot 路径、写地址命令；某些 boot mode 还会走 update。probe `895–903` 在当前 old-method 配置会安排 fw_check_then_recover；不能直接加载原厂 driver 只为“读个版本”。

## FFC 的准确位置与当前不可直接采用部分

19781 `pm8150b.dtsi:358–384` 配置 `vooc_project=3`、双电芯、`ffc_support`，没有 `dual_ffc`。`oplus_chg_check_status_full:6721–6740` 在原厂快充转 normal/warm 等条件、充电器已关闭且没有 FULL/FAIL 时，延迟计数到 4 后对**双芯且 !dual_ffc 直接进入 FFC2**；不是每次普通 USB attach 都先进入 FFC1。`oplus_chg_turn_on_ffc2:3939` 调整 MP2650 的普通 CC/CV 目标，FFC 因此包含 MCU 快充退出后的 host-managed 阶段，不是另一条独立 USB 协商协议。

本机 FFC2 原厂配置为 12–40℃（35℃分界），normal/warm 电流 350/400mA、SW 电压 4.415V、CV/OVP 4.465V/节、退出电流步长 100mA；完整原始属性已提取。FFC1 的配置也保留，但本机上述分支跳过它。**这些原厂电压高于当前已采用的 4.3625V/节**，不能通过复制 FFC 表或“复用原厂”抬高现有目标。本轮没有实现或授权更高 CV、电流或高压输入。

## 验证与下一可接入缺口

[test-result.json](test-result.json) 记录：原厂完整 `is_allow_fast_chg_real` 函数 10 个源类型/边界案例；原厂 15 条真实顶层分支谓词与 decoder 的 1024 个接收上下文/数值差分；两组真实 C 条件数组与 Python 提取逐字节一致；15 个截断、反序/重复地址、错误镜像分支、错误 token/frame 等拒绝边界。C 参考使用 ASan/UBSan、`-Werror`。测试范围没有原厂 action body、电气时序、活并发或实物固件更新，不能作为快充验收。

下一步能直接复用的是该**纯解析器和固定配置收据**，供后续受控 owner 保存真实 MCU 元数据/通知时解码、校验具体分支。剩下的最小接入缺口是：确认当前 MCU/rail/固件身份，设计有独占 GPIO/DPDM/总线生命周期的握手 owner，并保留现有保护和源预算；原厂 probe 的 reset/升级必须与只读识别分开。当前真实 SDP/CDP 连接不满足原厂 DCP gate，不能拿这些表或消息直接开启 SuperVOOC。未找到可把当前 100mA 原生预算合法升高的快充捷径；本组件对现有图标延迟不作修复声明。
