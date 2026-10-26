# BU64253镜头接入：无需设备重启的能力与当前缺口

2026-10-23，只读离线核对。**Image363已经具备动态OF/overlay和software-fwnode内核能力，不必为这些选项重建Image；但当前没有现成的“加载BU64253模块＋写sysfs”标准镜头热接入流程。** 若坚持不重启，需要另做受控的OF overlay加载模块或software-node板级桥，并在相机完全停用时重新注册目标sensor和CAMSS媒体图。若不引入临时桥，可直接准备新镜头模块及一次DT-only boot；这仍无需重建Image/logdump/rootfs。

本轮没有访问手机、绑定SDK、构建、改变生产树或执行热接入。BU64253协议、模组绑定及第五模组的原件恢复由[镜头原件盘点](LENS-SCOPE-NEXT.md)负责；本文只判断连接和生命周期前提，不把可实现性算成实机通过。

## 配置来自已运行Image本体

[检查器](inspect-live-lens.py)首先验证私有`kernel363/Image-k363-private`的SHA，再从其`IKCFG_ST`/`IKCFG_ED`之间解压配置。得到的配置指纹与[363原始构建收据](../kernel363/boot-candidate-build-validation.json)精确相同，没有使用可变的当前`build/.config`冒认运行配置。

| 原件 | SHA256 |
| --- | --- |
| Image363，59243008B | `15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468` |
| Image内解压`.config` | `23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed` |
| 保留`build/vmlinux` | `8e2bc2bd1de55eb53c58915ec03ae25dc77c9401e137d50fccbdcc173ff4dd96` |

配置明确为`OF=y`、`OF_DYNAMIC=y`、`OF_OVERLAY=y`、`CONFIGFS_FS=y`、`V4L2_ASYNC=y`、`V4L2_FWNODE=y`、`VIDEO_V4L2_SUBDEV_API=y`、`MODULES=y`、`MODULE_UNLOAD=y`；`MODVERSIONS=n`、`TRIM_UNUSED_KSYMS=n`。`VIDEO_BU64253`尚无配置项及源码，不能把配置中的缺项解释为需要更换整个内核才能新增外部模块。

`OF_CONFIGFS`在该版本配置和OF源码中均不存在，`drivers/of/Makefile`只按`OF_OVERLAY`编译`overlay.o`，OF目录没有configfs加载前端。`CONFIGFS_FS=y`也用于其它子系统，不能据此假定`/sys/kernel/config/device-tree/overlays`存在，安装一个用户态`dtoverlay`命令不能补出缺少的内核前端。

与Image收据匹配的`vmlinux`实际包含以下函数及其`__ksymtab_*`导出：`of_overlay_fdt_apply`、`of_overlay_remove`、`device_add_software_node`、`device_remove_software_node`、`fwnode_property_get_reference_args`、`i2c_new_client_device`。内核OF、I2C、software-node及V4L2 async/fwnode共9个相关框架文件，从Image363提交`ba61a62293e0f6bc5838c06f2e85e033e3d702a8`到当前source354逐字节相同。这些是可编写匹配模块的依据，尚未编译或装载新桥。

完整解压配置和检查收据仅存私有`E:/edk2-samurai-out/kernel450/live-lens/`。检查器的`--exports`重新验证Image/config/vmlinux及导出；`--dt`检查当前保留DT；`--grep kernel:相对路径 逗号分隔字串`与`--lines libcamera:相对路径 起行:止行`只读查看精确代码。每次执行均先调用449存储守卫，不占SDK。

## 标准lens绑定何时建立

当前IMX319和S5K3M5探针分别在`drivers/media/i2c/imx319.c:2762`、`s5k3m5.c:1575`调用`v4l2_async_register_subdev_sensor()`。

`drivers/media/v4l2-core/v4l2-fwnode.c:1229–1291`在这次注册时解析`lens-focus`，将所引用fwnode加入sensor自己的async notifier；缺属性则允许sensor无lens继续注册。之后匹配的subdev必须具有`MEDIA_ENT_F_LENS`，`v4l2-async.c:316–335,365–378`才通过`media_create_ancillary_link()`建立sensor→lens的标准ancillary link。新增一个I2C client或让驱动probe成功本身不能替代该引用和链接。

只给已经绑定的sensor追加`lens-focus`属性，不会重新运行上述解析。当前CAMSS notifier仅实现`.bound`/`.complete`，complete会遍历sensor重建pad链接并注册subdev节点，见`drivers/media/platform/qcom/camss/camss.c:5444–5503`；没有本轮已验证的局部镜头热插拔恢复逻辑。因此接入事务应先关闭全部相机消费者、释放CameraManager和媒体FD，再重新建立目标sensor notifier及CAMSS媒体图，不能在持续取流中追加lens。

libcamera也需要重新枚举：`src/libcamera/sensor/camera_sensor_legacy.cpp:279,653–675`仅在CameraSensor初始化时从`ancillaryEntities()`创建`CameraLens`；450管线`:233–238,280–285`在初始化IPA时冻结lens model及controls，开流时才重新打开已发现的lens。保持原Camera/Manager存活不会自动发现后来出现的实体。

IPA没有写死只接受某一款lens：`src/ipa/camss-vfe/camss.cpp:177–227`要求实际`V4L2_CID_FOCUS_ABSOLUTE`和YAML `autofocus.lens`精确匹配实际lens model，再检查扫描范围/步长/稳定等待等配置。故“驱动＋链接出现”与“标准AfMode/AfTrigger已启用”仍是两道门槛；新模组应从已恢复的本模组原厂行程、方向、初始化和延时数据生成配置，不复制主摄扫描参数。

## 不重启的两种可实施路径

| 路径 | 已有内核能力 | 仍需新增和验证 |
| --- | --- | --- |
| 匹配模块调用OF overlay API | Image363已导出GPL `of_overlay_fdt_apply(const void *, u32, int *, const struct device_node *)`及remove；OF动态I2C notifier可创建新child client | 一个有界、可回收的加载模块/DTBO，正确bus/regulator引用，sensor/CAMSS重新注册和逆向拆除 |
| 匹配板级模块创建software-fwnode lens | I2C board info支持`fwnode`/`swnode`；现有OF sensor可追加secondary software node；属性解析会回退secondary | 创建lens client和引用它的sensor secondary节点、供电映射、对象/模块引用生命周期及重新注册；当前没有专用相机桥 |

OF路径可以自然提供真实DT `lens-focus`，更贴合最终静态绑定。`i2c-core-of.c:160–212`根据OF动态增删通知查找父adapter并注册/删除设备；本机CCI的`i2c-qcom-cci.c:614`把adapter绑定到对应bus OF node，因此无需重新注册整个CCI控制器来发现一个新增的直接child。

不过，当前a30启动载体对应保留DTB，SHA `c559d2c4c9a83e85473b1b24724bb8938f1084bd3efcae9c4b67f37c2a4c4503`，**没有`/__symbols__`**。现有`lens-focus`仅在主摄`/soc@0/cci@ac4a000/i2c-bus@0/camera@10`。不能直接使用依赖外部`<&cci...>`/regulator标签的通用overlay；临时载荷必须用准确`target-path`定位，内部lens引用保留local fixup，现有供电引用从届时实际树按路径核对phandle，不抄其它DT版本的数值。没有必要为了生成`__symbols__`先重启一次。

software-node路径也确有标准引用语义：`drivers/base/property.c:605–624`在主fwnode未解析出引用时回退secondary；`drivers/base/swnode.c:1053–1116`允许给已有OF device添加唯一secondary节点并显式移除。以`PROPERTY_ENTRY_REF("lens-focus", &lens_node)`描述引用，再让新lens client持有同一个software fwnode，sensor重新注册时可以走现有V4L2 parser和ancillary link，不需要私有libcamera选镜头接口。驱动还需有匹配的I2C id入口；供电应使用可核对的标准supply映射/alias和runtime PM关系，不能依赖sensor偶然已通电。

`/sys/bus/i2c/devices/i2c-X/new_device`不提供上述路径。其实现`i2c-core-base.c:1264–1308`将`i2c_board_info`清零，只解析type和address，然后创建client；没有lens fwnode引用、sensor secondary属性、供电绑定或ancillary link。可写性及新地址出现都不能证明标准镜头接入完成。

临时接入需要先设计完整生命周期：停应用/桌面相机持有者并释放资源；重建目标sensor notifier与CAMSS图；移除时先释放Manager、CAMSS及sensor对lens/fwnode的引用，再删除lens client和overlay/secondary节点，最后恢复原sensor/CAMSS与服务。overlay API在失败时也可能返回已部分应用的changeset ID，必须按该ID清理；不能在V4L2仍持有引用时直接卸载板级模块。此处给出实现约束，没有执行这些状态切换或声称其已通过。

## 若采用一次DT-only boot

最小永久接入是一个匹配k363的BU64253 lens模块/包，加本模组正确CCI bus上的lens节点、reg和供电属性，以及目标sensor的`lens-focus=<&lens>`。节点地址、初始化/释放和行程以[本机原件](LENS-SCOPE-NEXT.md)为准；保留现有主摄lens和所有sensor时钟/像素模式。不需要新增特殊用户态镜头查找或改IPA私有协议。

模块需先准备好正常自动加载与失败回退，再让新DT的sensor notifier等待它；否则未匹配的lens依赖可能阻止CAMSS notifier完成。DT载体从届时实际a30或其后继启动镜像增量生成，保持DWC3 `usb-psy-name`、充电依赖、ICP映射和其它DT属性语义，使用原EDK2实际加载链；不改Image363/logdump或重装整套模块/rootfs。[充电DT-only先例](../charging-management-20261023/usb-boot-result.json)已经证明该分层，不能重放其旧事务。

首次验证应先确认两个标准实体及ancillary link、FocusAbsolute范围和实际控制写入/停流归位；再让新Manager加载模组AF配置，做一次Scanning→Focused/Failed、镜头ACK和原厂稳定等待的定向验证，同时检查资源/电源释放及无新故障。绝对清晰度、距离、连续AF与多摄同步另行验收。任何DT-only启动仍须由主线在手机串行窗口核对实际boot/回退后进行；本轮不要求用户立即重启。
