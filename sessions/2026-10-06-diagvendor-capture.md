<!-- split out of DIAG-CAPTURE.md on 2026-10-08 (document 1 of 2), verbatim -->

# 诊断镜像 boot-samurai-diagvendor —— 抓原厂按键驱动失败原因

生成：2026-10-06 14:1x (Asia/Shanghai)

## 产物（已复制到 E:\edk2-samurai-out\）

| 文件 | 大小 | sha256 |
|---|---|---|
| **boot-samurai-diagvendor.img** | 6,674,432 | `7e43f7c7296663a91b5dcba7db18762a529ec1807f8bf08c5f04c36dc1d3b853` |
| SM8150_UEFI-samurai-diagvendor.fd | 7,340,032 | 见 WSL 构建目录 |

回滚镜像（务必保留）：`E:\edk2-samurai-out\backup\boot_stock_RMX1931.img`（`dfe18875…`）

## 这个镜像做了什么（相对 release2）

1. `ButtonsDxe` 换回**原厂抽取版**（`Platform/EFI_Binaries/Drivers/Devices/samurai/ButtonsDxe`），
   并加入原厂 `TLMMDxe`，FFS GUID 改成唯一的 `8681CC5B`（避免和共享 `DALTLMM` 的 `8681cc5a` 撞）。
2. `BdsEntry` 开头插入 **DIAGFREEZE**：最下面 80 行画白色带 + **先关看门狗** + **冻结 180 秒**。
   目的：把 DXE 阶段最后 ~200 行日志（含原厂驱动的 `ButtonsInit:` 报错）冻结在屏上。
3. `PlatformBm` 插入 **DIAGREPORT**：打印
   `ButtonsDxe / ConSplitterDxe / PmicDxe / TLMMDxe` 的 LOADED/missing、
   `ConIn/SimpleTextIn/InEx/images` 计数，然后 60 秒按键回显窗口；
   **结束后照常进启动菜单，不会自动进 U 盘模式**。

已核对：FV 内 `ConfigureButtonGPIOs`×3、`Locate oppo project protocol failed`×1（= 原厂驱动在）、
`DIAGREPORT` 宽字符串×4（= 诊断代码在）；boot 结构 = header v1 / page 2048 / gzip(BootShim+FD) / 尾部追加 DTB。

## 刷机 + 抓取步骤

1. 手机进 fastboot：长按电源 15s 关机 → 按住 **音量下 + 电源**。
2. `fastboot devices` 确认能看到序列号。
3. `fastboot flash boot E:\edk2-samurai-out\boot-samurai-diagvendor.img`
4. `fastboot reboot`
5. 盯屏幕（时间线）：
   - **0–数秒**：framebuffer 上滚出 DXE 日志；找 `ButtonsInit:` 开头的行。
   - **到 BDS**：屏幕**停住 180 秒**，最底部出现**白色带** = 冻结生效 → 这时拍照/抄下整屏。
   - **冻结结束后**：出现 `=== DIAGREPORT ... ===` 报告 + 60 秒按键窗口 → 再拍一张。
6. 没看清就**重启再看一次**（不用重新刷）。

## 判读表（看 DIAGREPORT 上方的日志）

| 屏上出现的行 | 含义 | 下一步 |
|---|---|---|
| `ButtonsInit: failed to locate TLMMProtocol` | 缺 EFI_QCOM_TLMM_PROTOCOL | 查 TLMMDxe 是否真的 LOADED（看 DIAGREPORT） |
| `ButtonsInit: failed to locate PmicGpioProtocol` | 缺 PmicGpio | 换/加原厂 PmicDxe、GpiDxe |
| `ButtonsInit: failed to locate PmicPONProtocol` | 缺 PmicPON | 同上 |
| `ButtonsInit: Failed to locate PlatformInfo Protocol` | 缺/不匹配 PlatformInfo | 换原厂 PlatformInfoDxe |
| `ConfigureButtonGPIOs: EnableInput failed for VOL+/VOL-` | GPIO 配置失败 | 看 Status，查 TLMM/PmicGpio 参数 |
| `ButtonsInit: ConfigureButtonGPIOs() failed` | GPIO 阶段失败 | 同上 |
| `ButtonsInit: InitializeKeyMap() failed` | keymap 失败 | 对比原厂/共享版 keymap 配置 |
| `Locate oppo project protocol failed` | OPPO 专属协议缺失 | 可能可选；看是否紧跟着别的错误 |
| DIAGREPORT: `ButtonsDxe missing` | 原厂驱动被卸载（已确认失败） | 上面必有一条就是原因 |
| DIAGREPORT: `TLMMDxe missing` | TLMMDxe 没加载 | 重点查 FFS GUID / DEPEX |
| DIAGREPORT: `KEY scan=0x0002` | 音量下键产生了 SCAN_DOWN | 说明驱动其实能工作，问题在别处 |

按键 scan code 参考：`SCAN_UP=0x0001`、`SCAN_DOWN=0x0002`、`SCAN_ESC=0x0017`。

## 安全红线

- **只刷 boot**；绝不碰 `op1/modem/persist/super/userdata/metadata/xbl/abl/GPT`。
- 刷前确认备份在位；要回滚：`fastboot flash boot E:\edk2-samurai-out\backup\boot_stock_RMX1931.img`。
- 该镜像不会自动进 U 盘模式；万一进了，别让 Windows 初始化/格式化任何盘。

## 仓库当前状态（诊断态，可回退）

已改：
- `Platform/Realme/sm8150/samurai.fdf.inc`（原厂 ButtonsDxe + TLMMDxe 8681CC5B）
- `Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c`（DIAGREPORT + PrintLib.h）
- `Common/edk2/.../BdsDxe/BdsEntry.c`（DIAGFREEZE）
- `tools/tools_def.txt` + `Common/edk2/Conf/tools_def.txt`（GCC_AARCH64_CC_FLAGS 追加 `-std=gnu17`）

回退：在 repo 根执行 `python3 ~/edk2-samurai/diagtools/undodiag.py`（会移除 DIAGFREEZE/DIAGREPORT、去掉 TLMMDxe、把 ButtonsDxe 还原成共享版）。
`tools_def.txt` 的 `-std=gnu17` 建议**保留**：这次构建一开始失败就是因为它被 `build.sh` 从仓库版覆盖丢了。
---

# 最终结果（2026-10-06 16:2x）

## ✅ 音量下键已修复

| 检查项 | 修复前 | 修复后 |
|---|---|---|
| `DIAGREPORT` 里 `ButtonsDxe` | `missing` | **`LOADED`** |
| `SimpleTextIn` / `InEx` | 2 / 1 | **3 / 2** |
| 音量上键 | `SCAN_UP` | `SCAN_UP` |
| **音量下键** | 无反应 | **`SCAN_DOWN (0x0002)`** |
| 电源键 | 可用 | 可用 |

## 根因链（三层缺一不可）

```
缺 OppoProject.efi (OcdtDxe)      -> 缺 OPPO project 协议 903C579D-...
缺 ResetRuntimeDxe.efi            -> 缺 reset reason 协议 A022155A-...
ButtonsDxe.depex 未含 903C579D    -> 分发顺序不保证，OppoProject 可能晚于 ButtonsDxe
```

三者补齐后，原厂 realme `ButtonsDxe` 才能启动并读取 SMEM project（本机 = **19781**），
加载对应的按键映射，VOL+ / VOL− 均正常。

## 诊断过程中排除的错误假设

- ❌ `6231E399-807B-5A6A-DB81-D15B87041A4F` 不是 OPPO 协议（它是所有 sm8150 ButtonsDxe 都有的通用协议）
- ❌ 原厂 ButtonsDxe 的问题不是缺 TLMM（TLMMDxe 已 LOADED）也不是 keymap 本身
- ✅ 真正缺的是 **OPPO project 协议（903C579D）** 与 **reset reason 协议（A022155A）**

## 产物

| 镜像 | sha256 | 说明 |
|---|---|---|
| `boot-samurai-release3.img` | `c9feb0cab6abb66b4f3722f041449034d908c15bbf9a95b7903e394026360cde` | **正式版**：三键可用、无诊断冻结/面板 |
| `boot-samurai-fix3.img` | `7d384fddd06fb742006c1aea6072dc434300dc7e5f051031395bf9c8f081170b` | 定位版（含 40s 冻结 + DIAGREPORT），已完成使命 |
| `samurai-binaries.zip` | — | 设备固件二进制备份（15 个文件，144 KB） |
| `backup\boot_stock_RMX1931.img` | `dfe18875661164e7cb64eba7942b856e80ffe20abb537aec815da4bf43995cdd` | 原厂 boot（回安卓用） |

## 代码与文档

- 已推送：`hmhmdcy/edk2-realme-x2-pro` → commit **`696bf82`**
- 新增：
  - `Platform/Realme/sm8150/BINARIES.md` — 固件 blob 来源与 DEPEX 补丁说明
  - `Platform/Realme/sm8150/fetch-binaries.sh` — 一键下载 + 打补丁
  - `Platform/Realme/sm8150/fix-buttons-depex.py` — 幂等的 DEPEX 补丁脚本
- 更新：根 `README.md`（状态表 / 移植笔记 #4 / 已知问题 / 中文简介）、设备 `README.md`、`tools/tools_def.txt`（`-std=gnu17`）

## 遗留可选项

1. **验证正式版** `boot-samurai-release3.img`（未在真机跑过；fix3 已验证，正式版只少了诊断代码）
2. **EUD（Embedded USB Debug）**：SM8150 的 EUD 节点在本机原厂 DTB 中确认存在
   （`qcom,msm-eud@88e0000`，`reg = <0x088E0000 0x2000>`）。
   启用寄存器：`0x088E0000 + 0x1014 = BIT(0)`（`EUD_REG_CSR_EUD_EN`）。
   量产机可能被 `APPS_DBGEN_DISABLE` 熔丝禁用，建议先从 Android 侧试：
   `echo 1 > /sys/bus/platform/drivers/qcom_eud/*/enable`，看 PC 是否出现 VID 0x05C6 的 USB hub。
3. **持久日志**：pstore / 屏内日志查看器 / USB RAM 盘（见讨论）

---
