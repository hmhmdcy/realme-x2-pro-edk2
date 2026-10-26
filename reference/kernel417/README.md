# 417：类型化逐帧 ISP 参数通过 Media Request 真机验证

候选驱动现在能把 CST/CC/CV、Gamma 和 LTM 参数随输入缓冲区提交到标准 Media Request。同一会话连续切换旁路、颜色、零 Gamma、LA2048 和 LA1024，两种格式共16帧的全部有效像素，与此前固定诊断的参考输出逐字节相同。**尚未接入 libcamera 自动调校，完整适配目标继续。**

| 层次 | 本阶段变化 |
| --- | --- |
| SoC / ISP | 复用405/406已验证的有界参数编码、请求内IQ存储与DMA所有权；未新增任意寄存器或CDM入口 |
| 板级 / 传感器 | DT、电源、CCI和传感器模式未修改；第五摄像头仍待适配 |
| 主线接口 | 采用现有Media Request、V4L2 controls、vb2/m2m框架；新CID与参数结构仍为本地实验UAPI，未获上游分配 |
| 驱动 | 新增每文件句柄控制器、逐请求参数快照、输入字段校验、请求完成与取消回调 |
| 用户空间 | 新增实际V4L2请求客户端；正式r30/r25 libcamera仍使用原旁路路径 |

## 接口与所有权

[UAPI](qcom-ipe-a5.h)定义6008字节的固定宽度、原生端序数据包。全零表示旁路；version1必须携带正确size、已知flags、清零reserved和显式padding。输入请求必须恰有一个OUTPUT缓冲区并显式携带此控制；CAPTURE正常入队。无请求的旧路径保持旁路。

控制设置先校验，硬件工作线程在导入图像前应用请求并取得私有快照。直接设置当前控制返回EACCES，不能替换另一线程正在处理的请求。EXECUTE_ON_WRITE确保相邻相同数据包也被复制。核心仍在启动DMA前复制、检查并生成有界IQ；不确定完成时保留核心拥有的整页参数和图像引用。

实现见[补丁](request-iq.patch)及[源码状态](source-state.json)。维护分支`samurai-ipe-request-iq417`，提交`f0b6ea869e3e748e6c1ccfe06865ac8d02c3ef3a`，源码已提交且干净。W=1、KCFLAGS=-Werror的[内核构建](intree-build-validation.json)通过，匹配core/adapter成对使用；[实际校验器模型](params-validation.json)在ASan/UBSan下通过28项检查。

## 真机范围与失败记录

[运行结果](runtime-validation.json)、[像素对比](pixels-validation.json)证明：

- NV12 640×480 MMAP，以及NV21 650×480、stride672的导出DMA-BUF，各8帧；同一会话顺序为0/1/2/2/3/4/0/1，两个请求FD循环复用。
- 控制提交后覆盖用户内存，完成后读回原参数一致；相邻重复零Gamma及返回旁路的结果一致。
- 输入未改写、输出尾部、序号、时间戳、控制完成检查通过；全部有效像素等于406相应固定参考，零Gamma为Y0/UV128。LA灰块内部为128/64；没有将边缘或整个彩色图像解释为常量。
- 空请求、缺少参数、非法量化值、直接控制设置和隔行输入被拒绝。

保留三次未通过的实验，不能计作成功：

1. [r1](runtime-r1-validation.json)：测试脚本枚举了不存在的`/sys/class/media`，图像处理尚未提交；已改为枚举设备节点并核对媒体模型。
2. [r2](runtime-r2-validation.json)：候选遗漏必需的`buf_out_validate`，第一次Request QBUF被拒绝并产生一条vb2 WARN，未启动图像DMA。新增ANY→NONE及拒绝隔行的回调后重建。
3. [r3](runtime-r3-validation.json)：过严地把LA灰块内部结论扩至边缘，像素断言失败；6次固件帧完成不作为像素通过。改回406已验证的8块内部区域后，r4又逐字节比较了完整有效图像，零差异。

r4运行没有新增内核故障。r2产生的**taint512仍保留**，未清除、未为了清标记而重启；r4按已知512基线检查。此结果不能表述为taint0或从未发生警告。

## 当前设备与后续

临时候选已卸载，正式core395/adapter393/CAMSS389、原配置与加载标识已核对恢复。四路摄像头各12应用帧，共48帧；IPE49次完成，其中前摄多完成1次，单独记录。[当前状态](current-state-validation.json)确认资源释放、ICP/CAMSS/双CCI休眠、17时钟为0、9路供电disabled/users0，桌面两个服务均为uid10000单实例。四次417事务都已终止，候选未永久安装。

下一步把此接口接入实际r30/r25 `CamssIpe`及IPA请求，按请求成功提交/失败丢弃调校历史，随后接入407—416恢复的算法与当前传感器元数据、统计域。非零LTM/LCE、完整原厂LA/mask/weights/scalars/inverseGamma、强制错误恢复、持续AF/光学与多摄同步仍需完成；[完整范围](../kernel363/REMAINING-CAMERA-SCOPE.md)保持有效。

原厂HAL、系数、夹具、二进制、图像和设备日志保存在私有输出目录，未纳入公共补丁。此前数值结论及415版本地址纠正见[416](../kernel416/README.md)，不重复扩大已通过的TMC离线矩阵。

框架依据：[Linux Media Request API](https://cdn.kernel.org/doc/html/latest/userspace-api/media/mediactl/request-api.html)、[V4L2 m2m](https://docs.kernel.org/driver-api/media/v4l2-mem2mem.html)，具体回调以当前内核vb2和vim2m源码为准。
