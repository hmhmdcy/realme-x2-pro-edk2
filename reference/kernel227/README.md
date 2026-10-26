# 227：FastRPC 发布、回调对象及模块引用候选

2026-10-16。全外设适配目标继续进行。本阶段完成候选源码、隔离模块构建及主机故障注入；**尚未部署，不能算传感器功能修复验收**。当前手机仍为 boot219 / Image183、相机 r13/config-r8、原 FastRPC 189 模块。

## 具体问题与修改

原驱动先注册misc设备，后初始化channel的kref、锁、idr和列表，早到open会访问半初始化对象。双节点的第二次注册失败，还可能释放第一节点已使用的channel。当前RPMsg核心先建立端点再调用probe，失败/卸载时先调用驱动再销毁端点；仅提前kref或在错误路径直接put仍不够。

[候选补丁](fastrpc-publication-lifetime.patch)包含：

- 全部对象字段先初始化，发布drvdata后populate子设备，再注册misc；所有节点成功后才打开ready门控。open在同一channel锁内检查ready/rpdev、选择session、取得引用并挂入users，成功后才替换文件私有指针。
- 初始channel引用交给先注册的devm action；RPMsg端点销毁并排空在途回调以后，driver core才释放它。错误路径先注销misc、清理部分子设备、撤销发布，owner action最后恢复原DMA配置并put。
- drvdata的release/acquire发布配对，回调在锁内检查ready/rpdev。189 freezer等待逐字保留。
- 实机只读基线有1个FastRPC FD，但模块refcount为0；`fastrpc_fops`漏了`.owner = THIS_MODULE`。补上模块保活，并把退出顺序改为先注销RPMsg、后注销CB驱动。ELF检查确认新fops的owner指向`__this_module`，原版没有该重定位；实际VFS引用数待部署验证。

这不实现invoke、异步put_work或DMA的SSR排空；ready关闭后的晚到回复会被丢弃。活跃客户端卸载、共享池reclaim−22、物理传感器精度/运动/冷启动仍开放。源码生命周期依据见本地`drivers/rpmsg/rpmsg_core.c`、`qcom_glink_native.c`、`drivers/base/dd.c`、`drivers/char/misc.c`、`include/linux/fs.h`、`fs/file_table.c`；[前一轮研究](../kernel226/RESEARCH-FOLLOWUP.md)所审Qualcomm三补丁未原样部署。

## 验证与产物

[源码锁](fastrpc-source-validation.json)、[构建](fastrpc-build-validation.json)、[主机测试](fastrpc-host-validation.json)、[最终检查](source-final-validation.json)。

最终源码SHA256为`f378afedc84d4d0cc29166686210fbf706ea16be59dd4270cab2f3c3ac5faec8`，候选模块SHA256为`7ca5d442fb8351f841dcae3d16e4f981d9b08e7326b42c674f7ceaf4f08bdc0a`，50216字节，vermagic与当前#183相同。模块留在私人输出`kernel227/fastrpc227-candidate-private.ko`，隔离构建目录为`/home/cy122/x2pro-linux/fastrpc227-publication`。

使用当前准备好的kernel配置和Module.symvers，通过外部`M=`构建原版及候选，W=1编译/链接、modpost和导入符号检查通过；最终候选构建连同保留核查约3.54秒，没有修改canonical源码、对象、Image、DTB、配置、符号或模块顺序。51个相关文件与git状态/diff指纹保持。该时间不能外推为libcamera工具链提速。

故障注入直接提取锁定源码的probe/open/session/callback/owner函数，模拟内核API；ASan/UBSan下11例通过：单节点、双节点、第一/第二misc失败、部分child失败、无session、owner action失败、DMA配置失败、SCM失败、回调已读channel后跨越probe失败，以及分配失败。原版负对照在第一次早到open检出未初始化kref，退出86。模拟器不验证真实DMA、DSP重启或物理传感器。

两次初期checkpatch失败分别为样式/屏障说明及补丁头格式，已修正；保留中间源、头失败日志和收据。最终checkpatch无错误；仅现有`idr_init`搬移触发一条弃用API提示，精确排除该类别后为0。没有伪造Signed-off-by。首版主机夹具编译的表类型/符号比较警告已修正，旧日志保留；不是内核模块编译失败。

## 设备与下一步

[只读基线](device-baseline-validation.json)：仍同boot219，三DSP运行，taint及五类故障计数0；服务、模块和电源均未切换。原模块`88553112839d0a23604171edb03004a15e94f7cc3b174ebb3b9f2e56d3cc2fcc`/50240字节已在本机私人目录和设备`k227-baseline`备份。

旧FD不能因模块refcount为0而热卸载。下一步核清rootfs模块加载、`samurai-ssc`和initramfs路径，准备可回退的受控启动验证：核对新boot、loaded-note、实际文件保活引用及正常传感器读数；不以这一候选替代SSR排空。现有四轮GNSS零CNR结论和168h辅助有效期证据仍属226，未重复测量；用户未插SIM，蜂窝注册/业务待有卡，GNSS接收不以插卡为前提。

后摄的下一项明确依赖及启动限制见[PM8008设计](PM8008-DEPENDENCY.md)。
