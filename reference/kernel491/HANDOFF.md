# 摄像头／骁龙 ISP 交接

2026-10-24。用户要求先暂停相机、优先完成充电适配；本次仅整理文档与提交。相机目标保持暂停，没有恢复设备、SDK、构建或采集工作。手机启动／USB／guard 由充电任务维护，不能把旧相机事务的 boot、PID、健康快照当成当前身份。

## 已完成及证据范围

| 范围 | 结果与依据 |
| --- | --- |
| 正式安装 | [484](../kernel484/README.md)：五个 libcamera 包 `99990.7.2-r33`，config／stack `0.1.0-r28`；原生 APK 升级→精确 r32／r27 回退→再升级均成功，最终保留 r33／r28。441 三个 ISP 模块＋468 sensor，四份原厂私有 profile。 |
| 四摄默认路径 | 两次 forward 共 14 例，四摄 GST 256 张 640×480 NV12、RAW-only 24 帧、主摄双流 12 帧；268 次 IPE 成功＝242 数学＋26 bootstrap。实际 `/usr` 库、有效 IPA 签名、UID10000、maps、lease 与回执已核对，RAW-only 零 IPE。961 条 DB 中其余 954 包不变，回退逻辑、服务及资源释放通过。 |
| 主摄 720p／1080p | [441](../kernel441/README.md)／[442](../kernel442/README.md)：普通／隔离 IPA，同 SOF FULL／PD10、WB、已生效 GTM 与成功历史；442 得到 219 张成功图像、205 次数学提交、14 张 bootstrap。固定 FULL／参数，仅改变真实→黑→白→同真实 PD10：三输出互异，首尾真实输出全字节相等，确认 LTM 实际消费。441 r7 整轮积压失败仍保留，不能写成根因已修复。 |
| 长焦原厂 mode2 | [468](../kernel468/README.md)接入 4208×2368、LL4848／FLL3312，保留原 mode3 和 IQ；[469](../kernel469/README.md)720p、[474](../kernel474/HARDWARE.md)1080p 完成同帧消费及独立 PD10 四回放。474 普通／隔离各32帧，共64 IPE＝60数学＋4 bootstrap。 |
| 控制与生命周期 | [479](../kernel479/HARDWARE.md)长焦 mode2 九步曝光／增益，变化及三帧平台均 SOF+2，与现有2／2一致；不外推全局 delay。[461](../kernel461/HARDWARE-SUMMARY.md)同步 IPA 回执重入 stop 的 UAF 已修；Manager／长稳缺口继续保留，未宣布关闭。 |

以上证明已测范围的软件与硬件链路，不等于绝对色彩、光学、长期或全部摄像头功能验收。bootstrap 帧是明确单遍，不能把所有交付图像统称为数学双遍。未导出片内 DC SRAM，scratch 内容不作 SRAM 证据。

## 新候选及准备成果

[485](../kernel485/README.md)复用 Meson 安装处理，移除 core 的构建 RUNPATH；[486](../kernel486/README.md)启动器按真实 pwd 设置 HOME／USER／XDG。[487](../kernel487/README.md)由本机原厂描述符、HAL 加载器和实际消费指令闭合三 sensor 像素尺寸及有效菜单；[488](../kernel488/README.md)补 `0x2027` 的 YUV／15bpp 映射，不改 PD10 布局或猜填 rotation／delays。

[489](../kernel489/README.md)只增量编译两个 core 对象，最终 core SHA256 `b345af8b1430718b8fbcbbfde95916d66312bf0fc0e1b237edfb177332818bdd`。ARM64 SDK 默认加载、五组件 RTLD_NOW、原 IPA 验签、系统 profile／worker 路径解析和 UID10000 配置查找通过；未启动 CameraManager／worker，属于软件验证。IPA、签名、代理、base、数学、系数、驱动和私有 profile 未改。

[490](../kernel490/README.md)备齐签名 r34／r29 七包及精确 r33／r28 回退，57项载荷只有 core 改变；缓存961包 DB 的精确七包模拟通过。**未安装，不是当前手机版本。** 首次 CLI 失败与489测试错误均保留。

[491](README.md)完成仅更新包的定向复验工具：一次 forward、四摄640与主摄720／1080普通／隔离共8例、原生 APK 精确恢复 r33／r28；不换 KO／profile，不创建／删除持久仓库。实际未绑定归档23文件、46,870,927B，SHA256 `1e196141bb7066cf79bab14829d6d9168e6f851cc75853653cd8a1a9615b0319`。见[准备验收](preparation-validation.json)、[本地事务](local-validation.json)、[传输验证](transport-validation.json)与[独立复核](independent-review.json)。没有绑定、上传、安装或执行手机回调；仅支持当前 r1 namespace。

双遍源链已闭合：原厂主摄两 mode 开启 LTM／dataCollection，经原 IPA 参数到441内核 coarse gate；但现有 `m2m_status` 没有 DC／pass 计数。491拟采的是同 SOF 处理与成功交付，结合冻结源／profile 判断 gate；独立 PD10 扰动因果仍引用442，不冒称新硬件 pass 计数。

## 恢复工作时

1. 等用户明确恢复相机，再与充电任务串行交接设备；当前不保留相机设备／SDK／Git窗口。
2. 从充电最终记录取得届时实际 Image、boot、endpoint、原密钥 transport、guard 和481／468基线。501启动验证仍由充电独占，不能将候选或旧363预检 pin 写成新基线。
3. 核对476预检脚本固定的旧363 uname是否适用，再使用私有481 `formal-expected-private.json`；其 SHA256 为 `1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705`。不得沿用旧440期望或旧 owner／handoff。
4. 检查491源码、私有包和未绑定模板是否仍匹配。若变更，生成新模板；真实 transport 完整 argv 尚须核验。只执行新窗口一次 stage／launch，未知状态仅观察同一进程，不重放已终态事务。
5. 先完成 r34／r29 默认路径与警告的短复验、精确回退和资源／服务检查，再决定后续部署；未变的原厂数学和 LTM 因果证据直接复用。

尚未完成：共享 Manager 重开／lease 和统计积压根因、精确 crop／LSC 与绝对 WB／色彩、连续 AF、编码录像／HDR／热功耗、长期与跨启动稳定、多摄同步、第五 OV02A1B 的 PHY／初始帧／共享资源及 RAW。BU64253 寿命与 V4L2 mux／旧FD析构组合仍未部署，见[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)。

## 资料位置

公开源码、补丁、工具与脱敏收据在 `reference/kernel441`—`kernel491`；原厂导出、个体校准、照片、ELF／KO／APK 和原始日志仅在 `E:\edk2-samurai-out\kernelNNN`。核心续作原件为私有481正式期望／安装回收、489 build-r1、490 repository-r1 的 forward／rollback、491未绑定模板；完整哈希及来源见各阶段记录。

Windows编辑源为 `E:\RealmeX2Pro edk2`，canonical Git为 `/home/cy122/edk2-samurai/repo`，文档镜像前缀 `Platform/Realme/sm8150`。以后访问WSL源码／构建／ext4先用原461 storage `mounted_build()`；复用原32GiB卷，留2GiB，不改锁或盲目卸卷。公开副本按既有工具脱敏；提交只收相机选定变更，充电等其它改动保留。
