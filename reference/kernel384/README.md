# 384：原生 bypass 条带与实机像素对照

内核现在生成单 pass、全帧 1:1、关闭 IQ 模块的完整 bypass 条带，提交 API 和临时测试模块均已移除外部条带输入。本轮是有效进展，完整多摄／ISP校准目标仍 active。

本机维护源分支 `samurai-a5-ipe-native384`，提交 `5a0df37d3e9c8971d55186e468b38b424c8387dc`，父提交为383的 `a9f823f210344ab551e4859b4889358916345fbb`。候选已临时加载完成实机测试并卸载，未永久安装，Image363、DT365、boot366及r29/r24保持。

## SoC代码与适用范围

[bypass-striping.c](bypass-striping.c) 增加尺寸查询与序列化，复用383的分区组件；范围为8位线性NV12/NV21、输入输出尺寸和UV顺序相同、偶数宽高128..8192、显示/视频端口8/9、单/双核。允许有效的偶数填充stride/slice；运行层仍限制每幅图像64MiB，不能将8192²离线几何验证解释为可提交该尺寸的DMA。

生成纵向pass、各端口裁剪、FE/WE范围、四像素fetch halo、LTM网格坐标、径向坐标和估算工作量。即使IQ关闭，原固件仍消费其中字段。网格原函数LTMIPStripeConfiguraion用 `ceil(max(width,320)/12)` 和 `ceil(max(height,240)/9)`，倒数取整 `65536/grid`；条带网格余量和相位由输出起点计算。最初小尺寸原型忽略最小尺寸，已在扩展oracle中发现并修正。

输出清零后按字段写入，不复制原厂条带字节或未初始化padding。非法参数、尺寸转换、UV转换、短容量都在首次写入前拒绝，返回大小也保持不变。全局DMA所有权、错误完成retain、A5/两IPE引擎quiescence再回收的机制未改。

现有仓库和方案检索、固定来源和完整原固件验证基础沿用[383](../kernel383/README.md)及[382](../kernel382/README.md)，本轮没有重复下载。原厂HAL与固件仅私存，使用原算法作为oracle，模型不替换几何/CDM函数。不是重新实现开启高级IQ、缩放或几何warp的通用算法。

## 验证

- [serializer-validation.json](serializer-validation.json)：实际候选C函数体，ASAN/UBSAN，40组尺寸/端口/核心配置；整512KiB CDM和32字节job与原HAL条带经原固件准备的结果逐字节一致。包括128小尺寸、328/330和656/658分区阈值及8192宽度。非法/容量不足与尾部保护通过。
- [formats-validation.json](formats-validation.json)：另6组原HAL完整算法，含NV21和8192高度，每组配置无填充/有填充IO，新增12组完整原固件CDM/job比较。合计46组几何条件、52组命令准备对照；没有执行模型硬件enqueue或像素DMA。
- [transfer-validation.json](transfer-validation.json)：更新后的实际提交、编码、回复与停机函数体，24组分配/映射/回收、超时、回复长度/状态/token故障注入，保留DMA与PM和复位重试顺序通过。
- [intree-build-validation.json](intree-build-validation.json)：真实k363配置in-tree、W=1、KCFLAGS=-Werror，无警告错误。核心317008字节SHA256 `b429dc7b37fb22d9a5628a90eb3e27b780e4df3da568750f815ac7ae09a3b56d`，测试99712字节SHA256 `64141f53e861b10039cd7b334d73811a1fc90ef81fe1f926b35fcae42d7ffde7`。

[boot-runtime-validation.json](boot-runtime-validation.json) 对应唯一 `/var/lib/samurai/k384-boot-r1`，worker14251及collector均终态退出。相同378恢复启动，预检电量100%、24.3°C、CAMSS休眠。仅上传两模块、原FW与观察脚本，没有条带/IQ文件。INIT/PING、RT/非RT双handle及CONFIG_IO、RT单帧640×480、FRAME40/ACK72、图像MAP/UNMAP、双destroy、正常PC/WFI/停机和全部资源释放通过。CMD158/MSG173words，16消息/17中断/1debug，watchdog/protocol0、无新相关故障。未触发失败快照，不将snapshot_saved=false解释为失败。

[pixels-validation.json](pixels-validation.json)：实际输出460800字节与382使用原厂条带的实机结果全部相同。Y307200字节等于输入；UV143040字节精确相同、MAE0.203125，仍有原路径阶跃附近的色度滤波差异。输入CRC3426410711、输出3085177422。不能称全平面identity或完整光学校准。此测试只用合成图，不受现场低照度影响，没有重采摄像头。

[current-state-validation.json](current-state-validation.json)：维护源干净且与已验证提案相等；taint0、CAMSS与双CCI休眠、9相机电源disabled/users0、ICP模块和临时固件无残留、静态ICPdisabled。worker记录17相关时钟全部归零。四摄普通采集复用381证据；SSC旧attach/SLPI问题未在本轮修复，不宣称全平台健康。

## 接续

先扩展原生路径的实际尺寸/端口/双核与连续帧验证，再接V4L2 m2m/libcamera；推导并适配原厂Gamma/LTM/CCM等组合，继续全部多摄校准目标。基础bypass去掉条带文件依赖并不代表完整ISP已完成。

现场按低照度解释，黑画面和噪点不能单独作为链路失败依据；依赖光照的色彩/光学校准后续进行。第五2MP身份、更多模式、动态帧长/自动频闪、几何/同步/连续AF等仍按[剩余范围](../kernel363/REMAINING-CAMERA-SCOPE.md)推进。

私有原HAL/FW、反汇编、striping/CDM、完整日志与像素仅在 `/mnt/e/edk2-samurai-out/kernel384` 及既有各阶段私存目录。公共范围只含自有代码、模型脚本及脱敏结果；本地提交不push/PR。
