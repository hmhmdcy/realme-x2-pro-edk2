# 本轮标准控制核对

- [libcamera控制定义](https://docs.libcamera.org/master/internal-api/namespacelibcamera_1_1controls.html)：曝光与增益独立支持Auto/Manual；Auto下的手动值忽略且不保留，转Manual无新值时冻结最后计算目标，返回Auto从手动目标起步。AeEnable同时设置两模式，同请求的独立模式优先。本机固定v0.7.2的Camera核心已处理AeEnable，无需再次实现这一转换。
- [2026-08上游AgcAlgorithm提案](https://lists.libcamera.org/pipermail/libcamera-devel/2026-August/061425.html)将请求模式与捕获值分别处理。本轮没有整体移植该47补丁系列；在现有simple软件IPA中增加模式状态，并把来源标签与DelayedControls一起延迟，在真实SOF处快照。来源元数据不直接回显当前请求。
- 固定版本的IPA生成器注释允许自定义start签名，但线程代理的非void分支未转发额外输出参数。完整构建复现后，0019补上转发；所有原管线/代理保留，候选仍须普通和隔离IPA实机验证。
- 模型内的2/1帧传感器延迟保持原值，光学延迟尚未标定。数值、来源标签与历史吻合并不等于完成光学校准或画质验收。
