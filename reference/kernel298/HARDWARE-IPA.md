# CAMSS 硬件 pipeline／IPA 接入约定

本文件记录298实际接口边界，不代表已实现或部署 libcamera 硬件 pipeline。当前产品仍使用 Simple＋软件 ISP，libcamera r24配方未改。对应源版本0.7.2，现有维护源码位于保留的278 r24-r3构建树。

| 层 | 复用接口与职责 | 当前缺口 |
| --- | --- | --- |
| 板级 | 标准DT描述供电、时钟、CSI连接与方向 | 不为调校数值新增DT属性 |
| SoC驱动 | VFE175公共图像／参数／统计节点、MC链接、VB2、FRAME_SYNC事件 | 多参数排队、严重IRQ延迟、多个丢失SOF边缘和其它模式尚未验收 |
| sensor/lens | CameraSensor、CameraLens、V4L2曝光／增益／镜头控制，CameraSensorHelper换算与DelayedControls | 实测曝光／模拟增益延迟；不把sensor gain code当线性增益 |
| pipeline | MediaDevice／MediaEntity与V4L2VideoDevice管理FULL NV12、META_OUTPUT参数、META_CAPTURE统计及其buffer生命周期 | 尚未加入或部署CAMSS硬件handler；不能由Simple最短RAW路由自动等同硬件ISP |
| IPA | 以带epoch的SOF号关联图像、统计、参数回执及每帧上下文，复用现有IPA buffer与IPC机制 | 不能按最近完成时间配对；丢帧保留序号间隔；空／错误／缺身份统计不得推进算法 |
| 模组调校 | 用户空间按sensor、模组变体、模式和增益范围选择数据 | 64 DN与R2.22/B1.90目前只是单场景估计，禁止标成原厂或暗场标定 |

BLS/WB继续使用既有 `camss_params_wb_gain`：归一化U16相等减偏移，U15Q10 gain；驱动负责U14／U12Q7量化。硬件BLS保持Q11 unity，额外动态范围伸展由算法明确决定，不能暗中塞入驱动。不同通道减偏移和加偏移尚不支持，不能通过丢弃差异伪装支持。

参数包用现有 `v4l2_isp_buffer` 和标准参数节点，不增加私有ioctl或用户空间MMIO。参数已QBUF后的原始用户映射变化不得影响已验证快照。pipeline必须记录实际完成状态与报告的首个生效SOF，遇到streamoff／重开时清理旧epoch上下文并重新发初始参数，不能假设停参数队列会自动把图像状态归零。

当前 `CAMSS_STATS_AEC_BHIST` 是线性Y、1024 bins，足以提供亮度分布线索，不能还原独立RGB通道。AE必须先明确BLS/WB对统计的影响及sensor控制延迟；自动AWB需要额外有效颜色统计或明确的RAW统计路径。不能将本轮从离线RAW取得的灰世界系数冒充硬件IPA在线AWB。

首个接入阶段应限定已验证的sensor模式与单参数在途，保留现有RAW产品回退；通过可发现的硬件能力选择路径，避免把机型、CCI总线编号或场景系数写入公共handler。正式安装前须完成配置、首帧、停流、取消、错误回收、重开以及应用回归。当前未将下游typed接口的存在或本地提交当成上游接受，更新仍需维护现有补丁。
