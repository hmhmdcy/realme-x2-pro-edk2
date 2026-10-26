# 455：BU64253 lifetime r3 独立候选

本轮将 [453](../kernel453/README.md) 的 lens lifetime 问题推进为独立、可编译候选，**未部署**。原 C、453 source-view/O/模块、共享 source354/build、Image、SDK 与手机均未改。候选仍依赖 [0064 core 修正](../kernel453/0064-media-v4l2-core-clear-devnode-before-subdev-release.patch)先进入实际内核，不能单独加载到当前未修 core。

[候选 C](bu64253.c)、[相对 453 的补丁](bu64253-lifetime-r3.patch)、[设计收据](design-validation.json)。source SHA256 `37d9754e69e75c2782c9b6cd464fba03e3abe0d3a1b8d1c53932d2ef40dc349b`，module SHA256 `2f4abac12900e5cee36409690e4a9c7ce212c7809d207f7cbc497f21eef79bb3`。二进制、完整日志和两份既有私有 init FW 放在 `E:/edk2-samurai-out/kernel455/`，没有新取 EEPROM/NV 或改原厂调校值。

## 对象和电源引用

| 引用 | 获取与释放 |
| --- | --- |
| driver base kref | probe 初始化为 1；detach 确认 VDD-off 成功后 put。disable 失败保留。 |
| framework kref | 每次成功 `.registered` 增加 1，最后用户的 `.release` 原子交换标志并 put。旧注册尚未 release 时拒绝另一轮 registered；未匹配 async 的设备仍有 base ref。 |
| device | probe `get_device()`，最后析构 `put_device()`；晚 close 所需设备内存不会随 unbind 消失。 |
| regulator | 完整验证 FW 后才 `regulator_get()`；最后析构且 enable 引用已关闭时才 put。控件、entity、两把 mutex 同样延后至最后 kref。 |
| power module | **在 regulator_enable 前 `try_module_get()`**；enable 失败平衡 put，disable 成功且完成 off 延时后才 put。disable 失败继续保留。remove 中没有新增模块引用。 |

所有旧 generation 都留在全局实例表直到最终析构。同一 device 的 BU64253 probe 在旧 FD 或隔离故障对象尚存时返回 `-EBUSY`，避免与新 binding 的 PM 状态混用。remove 先禁止新 open/control，注销 async、结清旧 open 的 PM 使用计数，再 barrier/断电；晚 close 完全跳过 PM。正常绑定期间 close 仍使用异步 `pm_runtime_put()`。没有新增默认 DAC、ID、park 命令或满量程扫镜。

锁顺序为 lifecycle mutex → lens mutex；runtime callbacks 和 control 不获取 lifecycle mutex。remove 调用 PM barrier 时不持 lens mutex；注册 ref 的 release 不获取 lifecycle mutex，允许 unregister 同步触发它。控制的 `get_if_in_use` 与异步 put 延续 453 的框架核对。宿主只执行顺序案例，未证明实际线程竞争、内核 lockdep 或全部 notifier 回调组合安全。

disable 失败无法由 void remove 拒绝 unbind。候选保留 base/object/device/regulator 和**预先持有**的 power module 引用，保持实例表占位，明确隔离至重启；VAF 仍可能带电，不能称为正常清理或自动恢复。不会强制 disable、猜测寄存器、定时无限重试、清除 PM 错误或对仍 enabled 的 handle 执行 regulator_put。驱动框架随后可能重置 PM 状态，那个状态不能证明物理电源已关。实例表只约束本候选的同设备重新 probe，不是通用总线绑定否决机制。

真实模块框架已只读核对（[收据](framework-review-validation.json)）：`kernel/module/main.c:772–782` 在引用无法释放时拒绝正常卸载，之后才置 `MODULE_STATE_GOING`；`:935–949` 的 try_module_get 检查 live 状态并 `atomic_inc_not_zero`。Image363 开启 MODULE_UNLOAD、关闭 FORCE_UNLOAD。因此本策略靠上电前引用阻止进入 GOING；并未声称 remove 中才 `__module_get()` 能挽救已开始的 rmmod。没有执行实际 rmmod 或 sysfs unbind。

原 453 PM 分类仍适用：resume callback 失败不自动置该内核的 runtime_error；fatal suspend 失败会粘滞并阻止后续 resume。候选没有用宿主 PM 桩冒认这部分真实框架运行，也没有随意清除错误。若受控解绑时断电成功，可在旧 FD 最终释放后重新 probe；若仍失败，保留隔离状态。

## 实际编译与宿主检查

[构建脚本](build-module.py)、[真实 in-tree 收据](module-build-validation.json)：独立 `/mnt/samurai-full282/kernel455-lens-private/{source-view,O}`，先由 449 mounted_build 取得现存卷。仅 olddefconfig、modules_prepare 和 `drivers/media/i2c/bu64253.ko`，20.024 秒；W=1/KCFLAGS=-Werror 零诊断，intree=Y，k363 vermagic 精确匹配，41 个导入全部在原 Image363 Module.symvers 中。没有 Image/rootfs/全 modules 构建。vmlinux.o 是私有实际副本，不是指向共享 O 的链接。

配置来自经过指纹核对的 Image363 嵌入 config `23e088a9…`；olddefconfig 仅补显式 disabled ICP 项。构建源码视图复用当前缓存，但八个相关公开 API 头与固定 363 commit 逐字相同；进一步核过实际编译 `.cmd` 的 735 个源码文件依赖，除新 driver 外，其余 734 个均受 Git 跟踪，且不与 363 以后改变路径相交。[依赖/模块规则审查脚本](review-framework.py)只读，没有把当前 HEAD 当成未来单点 core Image 的基线。

[原 C 宿主脚本](check-lifetime-c.py)、[当前 ASAN/UBSAN 收据](lifetime-c-validation.json)：原候选从常量/结构直到 remove 的整个 C 主体逐字抽出，并执行 0064 修正后的原 core release 函数。框架、PM、module、regulator、锁和链表入口明确由顺序桩提供；不是 Python 镜像实现。

42 个案例覆盖两份有效 FW 的原始三条 init 字节、正常多 open/close、未匹配 async、三个注册/释放周期及重复/拒绝回调、unregister 后 close、remove 后双晚 close/阻止旧 FD 期间 rebind/最后 close 后重绑、GOING 时拒绝上电、enable 失败、18 类缺失/非法 FW、额外 property/I/O 和注册资源错误、6 个 init short/NACK、2 个 init rollback-disable 保留/重试、2 个 remove/suspend-disable 隔离路径。非法 FW 在 regulator lookup/PM/电源/I2C 前失败。

测试末态**有意仍保留两份可达隔离对象与两份 power module 引用**，regulator_put 次数为 0、WARN 为 0；这与“全部分配都已释放”不同。它验证本候选在模拟失败时保留所需资源，不证明实机 rail 状态或故障可恢复。

首轮宿主编译失败是桩计数名 `puts` 与 stdio 函数重名，仅重命名桩计数；r1 失败日志保留。r2 的 42 例通过；r3 增加两份有效 FW 的精确 init 字节断言再通过，候选 C 与已编模块均未变化。[最终指纹和全部日志收据](final-validation.json)。

仍未覆盖真实内核 PM/锁并发、notifier 热解绑、实际模块卸载、DT 应用、故障电源、镜头动作或 AF。下一步先审查此故障隔离策略，再由主线协调精确 363＋0064 的独立 Image 与启动窗口；本轮不执行这些动作。
