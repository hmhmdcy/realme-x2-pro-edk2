# 471：长焦1080p仅替换proxy的旧／新／旧比较

复用原厂长焦mode2、468 sensor候选及profile、441模块、461 core、444 IPA6／签名，仅在隔离worker中替换[451一次分配proxy](../kernel451/README.md)。三段实际顺序为A1旧→B新→A2旧，各32帧1920×1080 NV12；相同用户路径、GST消费者、配置、原厂IQ、PLL、缓冲数和历史提交顺序，三段共同启用现有[452有界FULL环](../kernel452/README.md)。无需构建、Image或重启。

[独立审计](inspect-comparison.py)及[结果](analysis-validation.json)核对96消费＝96物理IPE＝87成功数学＋9bootstrap，实际sensor均4208×2368。三段真实`/proc/.../exe`分别匹配旧`c7887708…`／新`35526054…`／旧，UID10000／cap0、独立IPA映射及FULL FD均见证。所有消费的原始同SOF PD10／GTM／WB／成功历史和LSC参数上下文通过。该结果是参数链证明，仍未验收AWB锁定或光学画质。

| 29张数学样本／段的中位墙钟 | A1旧 | B新 | A2旧 |
| --- | ---: | ---: | ---: |
| tone日志→host返回，ms | 15.626 | 3.566 | 4.073 |
| Pair→成功receipt，ms | 37.105 | 25.543 | 15.170 |
| 消费SOF缺口 | 22、30 | 无 | 无 |

新proxy本次返回尾部低于两侧旧值，但A2自身已经大幅变快，Pair→receipt也快于B。**不能据此声称稳定吞吐加速、缺口根因修复或长期无丢帧。** 分位、原始事件时间、供给区间和CPU分布见[独立分析](ANALYSIS.md)；没有为得到性能“通过”设定B必须更快或无gap的门槛。

三段FULL成功DQ分别34／33／32，共99，额外2／1／0张没有进入IPE或消费；guarded trace有105 QBUF／99 DQ，八CPU事件零覆盖／丢弃。A1和B各有一条正常stop之后的失败观察回执：已准备数学、尚未排入IPE，SOF晚于最后消费帧，所有原始回执均核对且未过滤；这两条不计入96消费／96物理IPE，也不把它们写成成功提交。

有界环分别完整保留557／522／512事件，零覆盖、时钟错误或Q计数下溢，记录真实内核SOF事件携带的timestamp及用户态callback时间。该timestamp是内核IRQ事件时间，仍不是外部测量的传感器物理边沿；FULL timestamp则为完成时间。它们使本轮两个缺口的关联不再依赖邻DQ窗口插值，软件队列快照仍不等于物理FIFO。

A1的FULL ioctl大多在CPU0–3，B全部在CPU0–3；A2从SOF10至31的22次DQ均在CPU4。容量分组只参考448历史缓存，未新测频率或IPA worker CPU。此为本轮相机Manager线程迁移与广泛加速同时出现的直接观察，尚不构成容量租约的实机因果。当前租约仍仅由lensActive触发，三段为inactive；下一最小底层候选应审查该条件对无lens的processed IPE路径是否过窄，不调整原厂PLL或扩大缓冲掩盖缺口。

三个正常capture结束后，原sensor文件/note、正式440／434库／包／三模块、服务、相机四PM/core/m2m及R8均恢复。外部新鲜两样本保护有效/error0、限值与manifest保持；worker已退出、独立trace及用户目录不存在，新增故障0／taint0。设备已明确交回充电，后续设备基线须重新交接，候选未永久安装。原件52文件、归档180980字节，SHA256 `196dcef2c85d2d8b6c2d40c019f430f4d7376ebfcfd330409e33687cbfffae6e`，私存`E:/edk2-samurai-out/kernel471/runtime-collected-r1`。

前置只读采样本身成功，首次host freshness断言拒绝；未加载候选或开流。同一query／observation原件保持，随后在原600秒限内严格缓存重审通过才stage／launch；没有改钟、放宽校验或重复设备采样。准确的首次两端时间差未保留，不能给该次断言失败编造精确原因。私有重审收据保留；该实机事务已终态，禁止重放。

[prepare-runtime.py](prepare-runtime.py)、[preflight-handoff.py](preflight-handoff.py)、[capture-body-tele.py](capture-body-tele.py)沿用467／468恢复顺序，另为每段选择proxy和保存独立环。工具自检收据仅说明已有缓存解析能力，本案实际结果以analysis-validation为准。后续[472控制阶跃准备](../kernel472/PREPARATION.md)独立复用306工具；不把本次proxy比较当作mode2控制延迟或1080p独立LTM因果验收。
