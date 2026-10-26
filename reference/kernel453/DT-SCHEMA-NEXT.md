# 453：DT 结构与框架释放顺序审查

本轮完成现有 DT 草稿的编译、相关 schema 依赖核对和原 C 释放顺序的宿主反例。发现当前 V4L2 core 在允许释放 `sd` 的回调之后继续写 `sd->devnode`；[0064 最小补丁](0064-media-v4l2-core-clear-devnode-before-subdev-release.patch)仅将清空操作前移。**原 BU64253 C、公开 binding、DT 草稿、Image 和手机状态未改；built-in core 尚未更新。** 本轮没有 SDK、手机或实际 Image 构建操作。

## DT 验证结果与限制

复用本地 dtschema 2026.9、jsonschema 4.26.0、DTC 1.7.2，没有安装工具或改共享树。[工具与固定源码指纹](schema-inspection.json)、[编译和依赖收据](schema-validation.json)、[可复现脚本](schema-validate.py)。

- 公开 `rohm,bu64253.yaml` 的 `dt-doc-validate` 仍失败：放到规范 bindings 路径后，只剩缺少 `maintainers`。直接从 reference 路径验证还会报告 `$id` 与路径不匹配。
- 私有规范路径副本只加入明确标为 schema-only 的 `example.invalid` 占位元数据，结构检查通过。它不是维护者身份，不能作为公开 binding 可上游提交的证明；公开文件未加虚构维护者。
- 以实际 source354 当前 board 为 baseline，加入现有 lens DTS 草稿后，cpp/dtc 均成功。两份 dtc 日志的既有告警完全相同，均为 8376 字节、SHA256 `c353ee414d7c1c8f54ac9e5c56551deb5031e5222d2ee5ecc9f8659acef773e4`；没有新增告警，不能称整板无告警。
- FDT 语义差异只有两个 `lens@c`、Q L6/P L3 两个 2.8 V regulator 节点，以及 IMX319/S5K3M5 两个原 sensor 的 `lens-focus` 属性；无删除节点。核过 251 个显式 phandle 引用单元，各 lens 的 0x0c 地址、单独 VAF consumer、FW 名称均匹配。
- 完整现存 bindings 加私有候选生成 processed schema 成功；定向验证 `rohm,bu64253`、`qcom,pm8008`、`qcom,i2c-cci`、`sony,imx319`、`samsung,s5k3m5` 五组均零诊断。这个结论只覆盖相关依赖，不是全树 `dtbs_check` 或运行中 DT 的验收。

该草稿未应用。新 lens 若因 FW 缺失/非法或 probe 失败，sensor 的 async lens 依赖可能无法完成；必须先准备匹配私有 FW 再启用 DT，并保留原 DT 回退。没有将结构通过当成 AF、PM、供电或镜头动作通过。

## 实际 PM 与锁：静态核对

下面行号均来自 [schema-inspection.json](schema-inspection.json) 固定指纹的真实内核源码；完整副本私存于 `E:/edk2-samurai-out/kernel453/schema/kernel/`。

正常控制路径未找到同一 mutex 的同步重入：`v4l2-ctrls-api.c:843` 起在 handler lock 下调用控制；BU64253 的 `pm_runtime_get_if_in_use()` 仅检查/增加活动引用（`runtime.c:1230` 起），不调用 resume；`pm_runtime_put()` 使用 `RPM_ASYNC`（`pm_runtime.h:549`），不在控制回调持锁时同步调用 suspend。`__rpm_callback()` 在调用驱动前释放 PM spinlock（`runtime.c:374` 起）。remove 当前先 `pm_runtime_disable()`、后取 lens mutex，避免持该 mutex 等待 PM callback；实际 disable 的 barrier 见 `runtime.c:1512` 起。这是静态锁顺序审查，未跑内核 lockdep 或并发压力。

两类 PM 错误必须分开：

1. `rpm_resume()` 的 callback 失败分支只恢复 `RPM_SUSPENDED`、取消 pending 请求（`runtime.c:939–947`），**没有赋值 `runtime_error`**。因此当前驱动 init/I2C 失败后，下一次正常 open 可以再次到达 resume，并先处理上次保留的 VDD 引用；不能把这种失败称为框架粘滞错误。
2. `rpm_suspend()` callback 返回非 `-EAGAIN/-EBUSY` 的错误时会置 `runtime_error`（`runtime.c:746–752`），下一次 resume 在 `:796` 返回 `-EINVAL`，不会进驱动。因此 VDD disable 的致命 suspend 失败不能保证再次 open 自动恢复。当前 C 没有盲目清除该错误。恢复需先确认真实供电/引用状态，再受控处理；不能在 VDD 仍可能开启时谎报 suspended。`__pm_runtime_set_status()` 的实际状态要求见 `:1294` 起。

## 三项未解决的框架/移除风险

**打开 FD 跨解绑的对象寿命。** 现 C 用 `devm_kzalloc`，remove 立即清理 entity、controls 和 mutex，未提供 internal `.release`。但 `v4l2-subdev.h:926–936` 明确 close 可以晚于 unregistered，release 才是最后用户消失后的释放点；实际 `subdev_close()`（`v4l2-subdev.c:144–153`）仍访问 sd 并调用驱动 close。`v4l2-dev.c:455–480` 在 fops close 后才 `video_put()`；`v4l2-device.c:263–293` 的 unregister 不等待最后 FD。正常 module pin 不能保证手动 I2C unbind 下 devm 内存存活。

模块引用也已核对：`v4l2-device.c:111–169` 的注册引用在最后 subdev release 后才 put；`subdev_open():119` 的额外引用是 media parent owner。它们保护模块代码，与 devm 对象寿命是两回事。未来 lens 需要单独 driver/framework 引用、保留 device、延后 controls/mutex/内存释放，并处理从未匹配 async 的 probe 和错误路径，不能只把 devm 改成 release 中 kfree。

**core 在 release 回调后写已释放对象。** `v4l2-device.c:175–182` 先调用 `internal_ops->release(sd)`，再写 `sd->devnode=NULL`，与上述可释放 sd 的契约冲突。[精确原 C 宿主脚本](schema-pm-proof.py)逐字提取该函数体，回调实际 `free(sd)`；原版 ASAN 明确 heap-use-after-free、退出 1，仅前移清空操作后 ASAN/UBSAN 退出 0。[失败及修正收据](schema-pm-proof.json)保留两次结果和函数指纹，完整日志与可执行文件私存：

- [原版失败日志](E:/edk2-samurai-out/kernel453/schema/release-order-original-run-private.log)
- [前移清空后的日志](E:/edk2-samurai-out/kernel453/schema/release-order-candidate-run-private.log)

这是原函数与最小宿主结构的内存反例，不是完整内核执行。没有通过延迟 free 或猜测 RCU 宽限期规避。0064 当前树 `git apply --check` 通过，未内核编译、未启动。[全树回调静态扫描](schema-core-compatibility.json)在 176 个含该 internal_ops 类型的 C 文件中找到两个显式 `.release`：dcmipp byteproc 从 `sd->dev_priv` 取对象后 kfree，dcmipp input 用 container_of 后 kfree；二者均不依赖非 NULL devnode。`v4l2_get_subdevdata()` 只读 dev_priv（subdev.h:1165–1167）。当前树未见此重排的直接依赖冲突；未覆盖树外模块、其他内核版本或运行并发，不能代替完整兼容性测试。

**remove 中 VDD disable 失败。** 现 C 只记录错误并继续返回 void。I2C remove 后会释放 devres（`i2c-core-base.c:623–639`、`dd.c:593–606`）；`regulator/core.c:2665–2675` 对仍有 enable_count 的 regulator_put 会 WARN。因此不能把已有“保留 supply_enabled”视作移除路径完整恢复，也不能假定再次 disable 一定成功。本轮未注入该硬件失败。

私有 lifetime/隔离审查草案已生成，见 [设计收据](schema-lifetime-draft.json) 和 [生成脚本](schema-lifetime-draft.py)。它提出 driver/framework kref、晚 close 不触碰新 binding PM 计数、移除先禁止新操作并结清旧 open 引用；disable 失败时保留 regulator/device/module/driver 引用、阻止同设备重绑并明确隔离至重启。**这是待审查故障策略，可能仍带电，不是正常断电成功或自动恢复。** 私有 C/patch 位于 `E:/edk2-samurai-out/kernel453/schema/bu64253-lifetime-quarantine-review-private.*`，未 C 编译、未框架验证，不替换现有已构建 C。

## 未来单点 core Image：可复用条件

[只读审计](schema-image-inspection.json)、[脚本](schema-image-inspect.py)确认原 Image363 固定提交为 `ba61a62293e0f6bc5838c06f2e85e033e3d702a8`，该提交本地可取。当前 source354/453 source-view 是 `5b0e7a9ac5b311a4c4fe17cf48b7ed4fc9a7b91d`，相对原提交有 39 条路径变化（包括 DT、videobuf2-dma-sg 和 CAMSS）。目标 `v4l2-device.c` 在两个提交逐字相同，0064 可限定为原 363 的单点源码变更。

现存共享 Image、vmlinux、Module.symvers、modules.order 仍精确匹配原 363 收据；`.config` 已变为 `e48f834d…`，不再是原 `23e088a9…`。相关 core 对象、thin archive、链接缓存和原 initramfs363 仍存在。但完整 O 是后续候选复用的可变缓存，最终 Image/vmlinux 相同不能证明 thin archive 现在引用的每个对象都仍是原 363。`.cmd` 与生成 Makefile 含绝对 source354/build 路径，迁移路径也可能扩大重编。

后续可以只请求 `Image` 目标，复用原 initramfs 和已匹配模块，无需 rootfs 或全 modules 重建；前提是新私有源码固定到原提交、恢复经过 Image 嵌入配置核对的原 config、复制为独立可写 O，并让 Kbuild 重建不再可信或路径已变化的依赖。**当前证据不足以保证只重编一个 `.o`。** 不能直接在当前 453 view/O 上构建 Image：它指向较新源码，且其 vmlinux.o 链接到共享对象；不能改共享缓存、伪造时间戳或直接用当前 441 HEAD 混入其它底层变化。

这一步尚未实际准备新的 Image 树/O、编译、封装或部署。core 在原 config 中为 built-in，普通 lens `.release` 修复需先协调该 core 修复的 Image/启动窗口。现 driver 指纹仍为 `7eaba1a2…`，模块仍为已验证 r2 `ba5ad180…`。本轮结果不扩展为 DT 已应用、真实 PM/卸载通过、任何镜头 AF 或光学画质通过。
