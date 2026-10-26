# 当前实装 R8：充电源码整合入口

本目录固定当前实装的**充电层**：R8 温区/Full 充电器、R7 FLOAT 输入提供端、未变的保护提供端和实际服务。旧 `charging-management-20261023/kernel-integration.patch`、`delivery.json` 保留历史，不能用于描述当前 R8；它们的旧模块与本目录的映射不同。

这里提供 12 个完整内核源码/header、4 个实际安装的服务及其依赖源码，以及必要的 Kconfig/Makefile/DT 增量。没有复制 ko、Image、DTB、私有现场原件、boot ID、密钥或序列号。没有改动平台 recipe、相机、蓝牙、共享源码/build 或 Git index，也没有访问手机、SSH、USB、SDK 或构建新 Image。

## 实装映射

完整 SHA 和每个来源见 [source-manifest.json](source-manifest.json)。

| 当前组件 | 完整源码来源 | 已有构建/安装依据 |
| --- | --- | --- |
| R8 MP2650，ko `10ec06fb…6297f` | thermal-bands 四个改变文件；kernel-v2 五个未变依赖 | `thermal-bands-build-result.json` 的九项 sources；R8 payload/update/handoff |
| R7 USB input，ko `7d4e0f94…c4f70` | 原 C `b712764f…7098`；FLOAT decode `a17caa2c…548fd` | `source-float-build-result.json` 两项 sources；R7 payload；R8 manifest/handoff 保留该模块 |
| gauge protection，ko `75b97e0d…783c7` | 现 `samurai-gauge-protection.c` `5d77236d…45b6`，复用同哈希 gauge headers | 原 integrated-build sources/module；R8 manifest 与 loaded note |
| 管理服务 `61451ffe…55aa4` | Full userspace revision 2 的实际服务；原 OpenRC 与两个已安装依赖 | userspace test receipt；R8 实装 manifest；update service hash |

R8 实装 manifest SHA 为 `320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f`。`source-manifest.json` 只导出其必要映射，不复制私有 manifest 原件或现场采样。三个 loaded-note 的摘要来自既有 R8 handoff；本轮没有重新读取设备。

## 文件与接入边界

- [kernel-integration.patch](kernel-integration.patch)：新增 `kernel-sources/drivers/power/supply/` 的 12 个确切文件，加三个模块的 Kconfig/Makefile 项。没有改 DWC、PHY、EUD、PD 或原 bq/mp2650 驱动。
- [native-usb-supply.patch](native-usb-supply.patch)：唯一 DT 增量是 `&usb_1_dwc3 { usb-psy-name = "samurai-usb-input"; };`。不增加静态充电节点；现服务继续显式选择已核过的本机 runtime 接线。
- [kernel-config.fragment](kernel-config.fragment)：只列这三个模块的 `=m`。它是后续源码整合的必要选择，未应用到共享配置。
- `rootfs-sources/`：按四个实际安装路径保存原字节。它们是现服务的源文件，不是新增现场工具或新的安装/更新事务。

两份补丁以固定原 Image363 commit `ba61a62293e0f6bc5838c06f2e85e033e3d702a8` 的 Kconfig、Makefile、源 DTS 完整 blob 为基线。根会话从 Git 对象导出到私有缓存，本轮只读这些缓存，三个基线 SHA 均记录在清单中。GNU `patch --dry-run --fuzz=0` 和实际应用到独立临时树均成功；应用后 12 个新增文件和三个增量的完整字节逐项比对通过，见 [patch-check-result.json](patch-check-result.json)。这不是整个新平台树的编译结果。

**源 DTS 增量不是当前部署 DTB 的重建声明。** 当前 native DTB 仍以既有 `c559d2c4c9a83e85473b1b24724bb8938f1084bd3efcae9c4b67f37c2a4c4503` 为准，原 Image 仍为 `15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468`。既有 USB DT/boot 收据证明只加入该电源引用；后续相机或平台 DTS 改动不能由本补丁覆盖。向已有该属性的维护树接入时，应核对已有同值，不重复增加节点。

## USB 100mA 与请求帽

| 层次 | 当前含义 |
| --- | --- |
| USB 启动描述符 | 两份实机启动脚本已按既有 rollback 收据恢复 `MaxPower=100mA`；当前仓库两条创建路径也是 100。本目录只记录哈希，不替换 USB 脚本或平台 recipe。 |
| 原生 USB 预算 | DWC3 接受的回调额度独立进入 USB 提供端。描述符 100 不能自行证明主机许可；SDP 使用实际 native 额度。 |
| 源动态限缩 | R7 FLOAT 处理已纳入；提供端按实际源状态报告预算，不向 PMIC 发起 APSD/PD/role 动作。 |
| 服务请求 | 输入请求帽 900mA、充电请求帽 250mA；实际输入继续受源预算和温区限制。R8 handoff 是 SDP/native/source/input 全为 100mA，不能写成强制输入 900mA。CDP 许可较高时，900mA 帽仍有效。 |
| 电压 | 继承上限为单芯 4.3625V、整包 8.725V；OEM 有效温区可以继续降低目标。 |

R8 使用单一 OEM effective band 贯穿 policy/Full/recharge，同时保留原始温度 `<-20` 或 `>=530`（0.1℃单位）的更严格绝对停充门。已有离线方向迟滞/Full 测试和实装 INHIBIT/AUTO 证据不等于实物全温界、完整 Full/再充、净充电或图标延迟验收；PM 恢复失败也没有由本次源码打包解决。

## 复核和复用

`prepare-source-package.py` 是离线导出器，只按已有 receipts 校验/复制源码、构造补丁，并在临时目录检查补丁与结果哈希。已通过的构建、thermal/OEM 差分、FLOAT、服务和旧 PM/USB 套件没有重跑。生成物存在但字节不同会拒绝覆盖；新源码必须另建版本。

未来重新构建的二进制可能产生不同摘要，不能直接冒用本目录记录的已实装摘要或把本源码包当现场更新脚本。这里没有安装、卸载、重启或睡眠入口。维护者应在原平台构建中使用这些精确源文件与必要增量，并为自己的产物建立新的来源映射。

未部署的 USBIN 初始化、APSD rerun、EUD 软件/CSR 窗口、PHY 窗口、DWC 检测窗口/恢复修正、USB500 试验、PM 工具及其它 WIP 全部排除。源集合对**当前充电层**完整；整个平台和既有 Image 的来源仍由原平台包负责。
