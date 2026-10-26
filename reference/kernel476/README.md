# 476：mode2 控制延迟离线执行准备

已交付本地分析器、私有BLS-only测量profile、捕获body、新鲜preflight接口和本地打包器。**没有访问手机、SSH、SDK、构建、上传或启动测量。mode2生效延迟未测，未预设2帧。** 472工具及其源码、ROOT474/475/NAV均未修改。

当前成品为 `E:/edk2-samurai-out/kernel476/k476-control-delay-r2-offline-template/control-delay-payload.tar.gz`，20个文件，SHA `5fa75688fc498ffae35fad0c51f4df7f828bbcaf95f21ea8f73048ce4ba9d137`。它是 **deployable=false** 的离线模板；worker在任何目标inventory或改变前拒绝未绑定／过期handoff。r1为同阶段较早模板，后续使用r2版本或用新鲜handoff重新生成绑定包。

## 固定输入与隔离

- 472已编译的static stepper `d8b73c3b…5ce98` 与capture `efaed465…1ef52`；RAW10 sensor4208×2368、CROP(0,376)/4208×2368、LL4848、FLL3312，NV12 320×180仅作请求／存活见证。
- 完整原461 runtime：core `9b352a12…af3af`、base、IPA、签名和旧proxy `c7887708…2038c`；不使用473／451性能组合。
- 468 mode2 sensor模块及441已核SoC模块；复用**实际成功473 worker**的CAMSS notifier卸载→sensor替换→SoC加载顺序，结束先卸SoC、恢复sensor、再恢复正式CAMSS。未安装475离线候选，默认正式expected仍为440 r32/r27／434／原sensor。
- 私有profile `mode2-measurement-private.yaml`，SHA `c4ebe947…b3ac8`：只有精确模式匹配、原厂BLS参考3840和归一化1.06201171875；没有sensor_controls、AGC、AWB、delay、动态IQ或IPE/PD10。
- 精确expected release/version由冻结363 Image（SHA `15746aab…d6468`）及363原adoption取得：`7.3.0-rc6-rmx1931-samurai-k363+`，`#363 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026`。没有用目标运行时uname生成expected。

## 工具与后续入口

[preflight-handoff.py](preflight-handoff.py) 复用473/461的只读查询渲染和观察检查，命名空间限 `k476-control-delay-r1…r20`。它不会发送查询。当前已在476私有preflight目录生成一份**未绑定、未执行**的r1查询，不能冒充新鲜前置结果。

后续由主线在得到charging owner-return后，按原流程使用 `--window-id`、`--owner-return`、`--adoption` 渲染新查询；由已有受控传输取得观察，再用 `--request`／`--observation` 检查。版本也在该只读查询内与冻结expected比较。成功handoff会带expected_uname。接口另接受 `--formal-expected` 的 `validated=true, expected={packages,modules,installed_files,library_sha256,kernel_release}` 包装，以便未来正式基线实际改变后接入；当前不使用该覆盖。

取得新鲜476 handoff后，本地执行：

```text
python3 reference/kernel476/prepare-runtime.py --window-id k476-control-delay-r1 --handoff /absolute/private/preflight/.../handoff-private.json
```

[prepare-runtime.py](prepare-runtime.py) 只在本地核输入／生成包；要求handoff不超过600秒、baseline哈希一致且包含原sensor记录。它没有上传或启动入口。未来绑定报告单独写入该新私有工作目录，不覆盖本阶段冻结的deployable=false模板报告。生成的包内容后续应位于目标 `/var/lib/samurai/<window-id>/`，具体传输／启动仍由主线现有授权窗口掌握。

[capture-body-control.py](capture-body-control.py) 使用已核fixture和无capabilities的uid10000 launcher，运行capture→stepper。它保留原9步写入、233个SOF事件、至少240帧；要求真实capture／stepper／隔离IPA进程与映射见证、两次mode守卫、零IPE作业、配对物理SOF、配置日志delayed-controls=0、fixture恢复和子进程退出。单独的stepper控制回读在原源码中每次执行并检查；日志逐次保存write起止、ret/errno，初值另有显式readback。最终STEPPER_RESULT成功才意味着全部回读均已通过，不虚构逐次readback日志。

## 本地分析与缓存验证

```text
python3 reference/kernel476/analyse-local.py --log /private/collected/control-capture-private.log --output /private/result.json
```

[analyse-local.py](analyse-local.py) 不导入transport，不调用306脚本顶层SSH。当前Pair末字段使用 `parameter-buffer-submitted`，不将submitted当作硬件锁存确认。它用真实写入SOF/event_ns和配对BHIST计算，保留306原前后窗口、median/MAD、10倍噪声／5%响应条件、首变化与三帧平台算法，按曝光／增益和升／降分别输出；不要求两种控制或两方向相同延迟。

缺少所需配对SOF、失败／pending／跨过下一SOF的写入、已知饱和或原规则低SNR均使该阶跃无效，不插值。可选 `--quality` 接受真实已知的per-SOF `saturated`事实；单靠均值不能证明没有局部剪切，本轮没有添造该证据。统计ROI沿用全幅线性BHIST，mode2 population2491136；没有新增RAW ROI解包。仍沿用普通稳定场景，不追加用户延期的纯色／遮光测试。

[regression.py](regression.py) 已对306原始私有日志做有限缓存回归，九个阶跃的既有判定全部一致：7个有效、2个低SNR；并核当前Pair末字段解析、缺帧与已知饱和拒绝。**该物理数据仅为mode3**，没有把它改标mode2或作为mode2延迟证明。[缓存回归收据](analysis-regression-validation.json)、[离线包收据](preparation-validation.json)。
