# 462 r3：IMX471 对象保留到最后一个 subdev 用户退出

r2标明的旧FD跨unbind问题确有本机软件调用路径。[源码核对](source-chain-validation.json)确认后，r3已形成[单文件增量补丁](0001-media-imx471-retain-sensor-until-final-release.patch)，用V4L2现有registered／release回调和独立sensor引用延后析构。18例实际C有限生命周期检查、两份预期UAF反例及受影响对象构建均已完成。**仍为NOT deployable**：当前没有组合新内核、KO、加载或硬件验收。本轮无手机／SSH／SDK，r1／r2冻结件及共享source354／build未改。

完整候选、原始源码快照、对象、编译日志和ASAN反例地址只在私有kernel462/r3。本目录补丁基于已冻结r2；不修改r1的DT／binding，不增加第五节点、模式或原厂调校数值。

## 已确认的真实调用链

Image363配置中VIDEO_V4L2_SUBDEV_API=y。20个相关函数已逐字对照原363提交ba61a622…，均相同；当前CAMSS整文件有后续变化，但下面的节点创建函数本身与原363相同，未用整文件名相同代替核对。

| 阶段 | 实际源码及含义 |
| --- | --- |
| 创建节点 | CAMSS的camss_subdev_notifier_complete调用v4l2_device_register_subdev_nodes；IMX471设置HAS_DEVNODE，因此具备可打开的subdev节点路径。没有新查手机当前节点或FD。 |
| 打开 | v4l2_open取得video_device引用；subdev_open建立每FD状态和fh，fh继承ctrl_handler。模块引用保护代码，video_device引用保护节点；r2没有sensor allocation引用。 |
| 解绑 | async unregister经v4l2_async_unbind_subdev_one到v4l2_device_unregister_subdev，再注销video_device。旧FD使最终节点release延迟，不能阻止r2 remove当场cleanup状态／控件／entity。driver core随后devres_release_all释放r2 sensor。 |
| 晚退出 | subdev_close仍读取sd->internal_ops，poll仍读取sd->flags；最后video_put还会走v4l2_device_release_subdev_node及v4l2_subdev_release。sensor过早释放因此可被真正消费，不能仅以“新ioctl已拒绝”否定缺口。 |

[456的0064](../../kernel456/README.md)将sd->devnode清零移到driver release回调之前，允许回调最终释放sd；它不拥有sensor内存，也不代替驱动的延后析构。本轮重建的0064源码SHA精确等于456来源收据8378f997…e639f。

## 最小对象寿命改动

sensor改用独立kzalloc，并持get_device引用。bound driver有一个base kref，每次成功registered另加一个framework kref；release在最后节点用户退出时只释放该framework引用。这里没有给每次open新增上电、PM引用或lens式open_count，原sensor的open／close电源语义保持不变。

所有未析构generation留在实例表，同device的旧FD尚存时拒绝新probe；旧framework注册尚未release时也拒绝另一轮registered。正常notifier注销但driver仍绑定时base引用保留，最后旧FD退出后可以再注册。只有base与framework引用均退出后，才执行subdev cleanup、entity cleanup、ctrl handler free、mutex销毁及device put。

控件、active state与每FD state共用sensor mutex。detach先在这把锁下标记removing并排空已取得该锁的操作；control／set-format／enable-stream／disable-stream入口在PM或寄存器消费之前拒绝移除后的操作。随后不持该锁地async unregister与PM disable／barrier，再关闭r2资源holder并释放driver base引用，避免同步release或PM回调反向等待锁。

r2的供电／route holder C段SHA仍为de18a25d…161f9，逐字未变，复用其35例现有证明。若它关闭失败，独立holder继续保留自己的设备／模块／句柄；sensor在最后FD退出后仍可析构。对象寿命和故障资源持有各自按已有真实引用结束，没有把保留一个普通布尔值当作内存保护。

## 已执行验证及其限度

[实际C检查](lifetime-c-validation.json)逐字提取候选sensor结构、alloc／destroy／registered／release／detach／remove，并执行原subdev_open、subdev_close及0064 release／node release。ASAN／UBSAN通过18例：分配失败、六个partial-probe初始化边界、无匹配／无节点、有节点正常退出、双FD晚close、旧FD期间重probe拒绝、最终close后重建、notifier注销后的重复注册、注册失败清理、实际open的状态分配／media-owner错误，以及两个独立r2故障holder接口场景。

这些是实际所列C函数加顺序框架／PM／状态／资源接口桩；未执行整个probe、传感器寄存器函数或真实r2电源函数。r2供电证明按不变的C段复用。每FD状态和video节点的分配／引用由显式桩管理，没有将宿主模型称作内核线程测试。

同一套有限模型另保留两份实际ASAN反例：旧r2 remove后模拟driver-core devres释放sensor，再走原晚close，命中heap-use-after-free；新driver配旧363 core最终release，命中回调已释放sd之后的devnode写入。r3配0064的正向案例通过；没有隐藏反例日志或用它们冒称实机故障已经出现。

[最终单对象构建](object-build-r2-validation.json)使用精确Image363配置23e088a9…及冻结r2 consumer头，在独立r3稀疏source-view／生成O中，以j2、W=1／-Werror通过：imx471.o为120296字节，SHA256 `4cc514f2271baa7f6d6f3ca8f65e708855e91372549d1883db98c06bbbc3c3cd`；C SHA为 `aea390bbc2edbeb67be58cdf5e8280f2861c7f32798aa960a6c140bb6c799f24`。无编译诊断，构建后可用空间6.37GiB。相对旧363缺失的导入仍恰为r2的mux_state_get／mux_state_put，没有新增另一组缺失API。未复制整树／整O或巨大vmlinux.o，未生成KO／Image／rootfs／全模块。

历史初版r3对象／收据保留；最终probe错误分支保留原有资源／entity／finalize诊断，再重跑受影响检查和对象。r1／r2没有覆盖。[最终冻结收据](r3-final-validation.json)记录完整文件及产物指纹。

## 可继续的进展与运行边界

旧FD对象过早释放已从笼统阻塞推进为单文件、可编译且有限路径已核的候选。后续组合必须同时包含0064、r2内建mux新导出和r3 IMX471；**456 Image单独只含0064，不含r2两个导出，不能直接满足r3**。本轮不构建这个组合，也不将相同uname release当作新内核实际运行证明。

下一授权硬件窗口可安排受控解绑：先停流并禁止新的open／上游stream请求，保留一个已打开的停流FD，核unbind后晚close、旧FD期同device重probe拒绝及最终释放后的重绑。现有core并没有本轮新增的贯穿整个subdev_open／async unregister的锁；本轮只做顺序案例，没有证明并发首次open、所有ioctl／graph／stream请求与unbind的全部交错。这个受控窗口前提不能被省略，也不扩展为任意热拆承诺。

supplier仍须保持绑定，管理员强制解绑供应商／parent controller或gpio-mux模块卸载不由本轮修正。r1的quiescent provider bootstrap、实际provider-ready、DT切换和物理route／reset／MCLK验证仍适用；第五摄像头的独立时钟／PHY／模式缺口不在这份sensor寿命补丁中验收。真实PM／锁并发、模块加载、解绑和硬件供电尚待主线串行窗口。
