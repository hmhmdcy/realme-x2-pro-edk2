# 公共缓冲修复：下一轮从这里继续

用户要求标准相机软件无需逐个改动；r1的 `SAMURAI_CAMERA_COPY=1` 仅临时缓解。目标仍active，当前没有完整公共路径修复，也没有内核故障归因。

1. 先读本目录README最新部分及ownership-validation。已装r1不变；诊断插件仅独立目录，341次错误全部busy=-1、refs=1、metas=2。GetActive已由正常接口设false，原自动锁屏已禁用，不需要重复要求用户手动解锁。
2. 固定来源：1.6.9归档SHA256在profile-build-validation；SDK `/home/cy122/x2pro-linux/libcamera214-root/work/pipewire262`。保留profile-build/source及ownership-build/source，不覆盖已核产物。已核系统APK和回退仍在私人262目录及手机事务目录。
3. `stream.c:add_params`约1900行请求Busy metadata；SPA libcamera的Meta枚举仅Header/VideoTransform，现场只有两项。`spa_libcamera_buffer_recycle`约272行清OUTSTANDING后立即queueRequest，没有Busy检查。**缺失Busy不是已证根因**，仅增加枚举也不保证生产端尊重引用；若延迟回收，须证明客户端归还后不会因驱动时钟停止而永久饥饿。
4. `impl-port.c:tee_process`约284行将输出IO直接复制给下游后置NEED_DATA；`schedule_mix_input`约367行类似复制。`tee_process_reliable`约308行会交换归还buffer_id，但只挑一个可接收mix，不能不经验证就把所有相机设reliable，须核对单/多客户端语义。node.reliable在impl-node.c约1160行、port.reliable在impl-port.c约531行设置。
5. 下一步对照缓冲ID与归还路径，验证正常引用持有期内内容是否被覆盖，分清生产端重复交付和客户端队列账本问题。可用隔离PipeWire/WirePlumber实例加载候选SPA插件，避免为只测一个候选反复重启生产策略服务。候选编译入口是spa/plugins/libcamera/meson.build的libcamera.c、manager.cpp、device.cpp、source.cpp；SDK有匹配0.7.2头文件/库。
6. 通用修复验收应关闭复制环境，覆盖直接libcamera客户端、GStreamer libcamera/PipeWire源及实际Snapshot；检测持续帧、持有/释放、停流、重新打开、相机切换和其它消费者行为。只有公共路径通过后才移除现有临时开关；GUI快门/录像、暗场曝光和其它后摄仍未完成。

第一次GUI从真实desktop Exec启动，35秒2042递增PTS、0回收错误、0paintable Bus Error、全部状态恢复；没有GUI快门操作。D-Bus动作只读DescribeAll显示app仅quit/shortcuts，窗口只有countdown，不要臆造shutter动作。若续测GUI快门，可通过已安装Atspi的实际可访问性按钮操作，先读取控件再点击，保存文件和picture-stored结果。
