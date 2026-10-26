# 277：RAW 空间清晰度统计与标准 FocusFoM 实机部署

2026-10-18。继续完整多摄及骁龙 ISP 目标，保持 active。**本阶段部署了 AF 所需的 RAW 空间统计和标准元数据，没有实现 AF 搜索、距离标定或 Spectra 硬件成像。** [此前标准镜头/CCI适配](../kernel276/README.md)

## 当前部署与分层

手机仍 boot276/Image183、`7.3.0-rc6-rmx1931-samurai-k132+`，776模块/961包；libcamera五组件升级 `99990.7.2-r23`、config/stack `0.1.0-r18`，PipeWire/SPA/Gst保持1.6.9-r3。没有刷写、重启、内核模块替换、driver unbind/unload或DSP停启。Phoc/Phosh原PID保持，仅PipeWire/WirePlumber正常退出并重新启动以加载匹配库。[原生事务](package-install-validation.json)、[最终核对](final-health-validation.json)

| 层 | 本阶段状态 |
| --- | --- |
| SoC／主线内核公共驱动 | 沿用276 CCI/LC898219XI/CAMSS，全部776模块保持；无新增内核或硬件ISP功能 |
| 板级设备树 | 沿用boot276，镜头phandle/独占VAF及双CCI共享I/O supply保持 |
| libcamera公共软件ISP | RAW绿色像素空间取样、平滑及4×3分区梯度统计；兼容已支持的打包/非打包Bayer和native quad绿色相位，无机型/镜头/应用分支 |
| IPA／标准接口 | 标准只读`FocusFoM`，仅在统计有效且frame identity匹配时报告；沿用每4帧统计一次的节奏 |
| 模组调校／AF | 尚无搜索状态机、AfMode/AfTrigger/AfState实现、DAC到屈光度映射或模组AF距离标定 |

[0027完整补丁](0027-softisp-raw-focus-statistics.patch)、[实际统计实现](focus_stats.h)。这是下游公共功能候选，不是上游接收记录。[原厂资料分层](../kernel276/OEM-TUNING.md)仍适用。

## 实现与主机验证

从RAW按正确绿色相位平均4×4物理像素区域，最多320×240个空间样本，3×3平滑后求二维梯度平方；每分区按平均亮度归一化，组合有信息的分区得到无物理单位FoM。统计发生在白平衡、gamma、锐化之前；黑暗或饱和区域不作为有效测量。**归一化不能代替固定曝光，也不能保证所有场景均可对焦。**

输入格式、stride、完整有效行长度及ROI先检查，再读取；CSI-2低位、非对齐ROI、普通/quad绿色相位均有用例。空帧/无有效区域不冒充旧分数。SwIspStats增加frame identity，IPA不会将另一个共享快照的FoM标到当前请求；这不是对原有全部IPA异步接口的全面重构。

实际生产helper通过C++17/Werror、20组格式/相位组合、CSI-2与非打包等价、颜色纹理与绿色分离、灰场/暗场/饱和、裁剪、短buffer和异常尺寸检查，ASan/UBSan通过。[主机验证](focus-stats-host-validation.json)

正常abuild构建完整13个签名包，保留26个既有补丁和发行版功能。原214工作区2254项恢复，r22缓存2274项保持。13包及本机信任签名、34个AArch64 ELF、五IPA签名、新core/verifier、工具/Qt/Python入口QA通过；主机模拟不等于相机实测。[构建](r23-package-build-validation.json)、[功能](r23-full-feature-configuration-validation.json)、[QA](complete-host-qa-validation.json)

首次构建入口解析旧生成器字符串时SyntaxError，发生于实际构建和工作区移动之前；改为AST解析后完成一次真实构建，没有重放不明状态的构建进程。

## 固定曝光的实机 RAW 对照

先用与生产候选逐字节相同的helper，在原r22上做独立原生libcamera测量；再部署r23，直接检查标准元数据与同请求RAW重算是否一致。两轮各四段、每段24组RAW4608×3456/RGB2048×1536配对，最后12组作为稳定阶段；曝光均31999us、增益1，镜头按标准V4L2设置208/304/880/208，无raw I2C旁路，不保存或输出像素。

| 位置 | 原r22独立helper FoM中位 | r23同请求RAW FoM中位 | r23稳定阶段元数据样本 |
| --- | ---: | ---: | ---: |
| 208 | 3964 | 3921 | 3 |
| 304 | 4035.5 | 4204.5 | 3 |
| 880 | 686.5 | 684 | 3 |
| 返回208 | 3966.5 | 3945 | 3 |

880失焦时分数下降，返回208后恢复；跨两轮环境/曝光历史不同，不能把两轮数值差异解释为画质提升。标准FocusFoM已声明可用，每4帧报告；本轮全部已报告帧都与同一request的RAW重算**完全一致**，稳定阶段共12个报告样本。未报告的帧不会重复旧分数。原先RGB平墙噪声梯度没有作为AF判据。[独立RAW对照](raw-focus-r1-validation.json)、[真实元数据对应](focus-metadata-r1-validation.json)

独立重算中位约10ms，采样数随分辨率有上限；这不是整条管线时延或持续30fps验收。这里实机验证的是GW1的FoM；其它三摄完成取流回归，尚未逐一验证其FoM光学曲线。镜头控制GET仍是缓存目标，不是实际位置反馈。

## 更新、回退与最终状态

精确旧r22/r17七包、配置/包数据库和服务身份已在手机及PC保存，2529160字节，SHA `fb587046bc48d22fc9e23b3ddd1cb0a1a0a802ec53f0250c9564191b8beab039`。新旧签名、七包原生升级及精确旧版本降级模拟通过；未执行回退往返。本次无需更改boot或内核回退。[暂存](package-preflight-validation.json)、[双份回退](rollback-validation.json)

原生七包事务核对49载荷，其余954包记录与全部776模块逐字节保持。Phoc3586/Phosh3803保持；PW10140/WP10143正常加载系统库，无私有库覆盖或deleted映射。SSC/SensorProxy/greetd正常，三DSP仍运行；物理旋转未重测，旧273 EPERM根因未证明修复，GPU默认故障/Cairo CPU回退和旧modem watchdog仍开放。

新r23下前摄＋主摄/广角/长焦18段241帧交替通过，包含主摄SIGINT正常退出37帧和重开；无强杀，回归期间无服务重启。[四摄回归](four-camera-regression-validation.json)

最终四sensor/lens/双CCI/CAMSS休眠，九rails及共享I/O OFF/users0、四MCLK/双CCI clock关闭；十个相关加载模块note匹配，fault0/taint0、CCI错误无、pstore空。[最终健康](final-health-validation.json)

实际r23/r18配方及部署锁已提升，旧r22/276锁已归档；内核源码仍`samurai-cci-io276`/`0d69276125ec8e7d0cc083ac421e2ad7fe79a3c8`，Image183未整体重编，最新完整统一内核/rootfs未部署。[提升收据](source-promotion-validation.json)

续作用`reference/kernel277/host.py`，仍核`/var/lib/samurai/k276-work/boot-id-private.txt`。服务身份文件是`/var/lib/samurai/k277-services-verified-private.json`；当前没有k277启动guard。私人日志/回退在`E:/edk2-samurai-out/kernel277`，不公开环境、密钥、校准或样片。所有本轮采集/构建/包事务均已终态。

下一步将该空间统计接入libcamera的AF控制与搜索状态机，处理移动/稳定时间、陈旧帧、低纹理失败、取消/连续模式与标定数据；不能用固定位置扫描脚本代替产品AF。继续r23完整手动曝光矩阵、四摄GUI/录像及模组画质。Spectra仍为RAW RDI→CPU ISP，公共硬件PIX/统计、参数接口及pipeline/IPA尚需实现，第四枚物理后摄仍未确认。完整目标未完成。
