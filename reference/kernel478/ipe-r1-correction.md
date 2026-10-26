# 476 r1：默认 IPE 路径与先前快审结论更正

**476 r1 仍为 `passed=false`。** 原因是确实运行了 IPE，违反模板的“零 IPE 作业”要求；不是计数器误报。原 476 文件、日志、state 和本阶段最初快审收据均保留。先前快审把“没有动态 tone／PD10”推成“没有 IPE”，漏核了默认输出路径，这个推论有误。

实际冻结 461 源为 `/mnt/samurai-full282/libcamera461-completion-ownership/src/libcamera-v0.7.2`。`src/libcamera/pipeline/camss-vfe/camss_vfe.cpp`（SHA `befec1da…b40`）1612–1614 总是尝试获取 `qcom-ipe-a5`，1656–1659 在媒体设备存在时创建 `ipe_`；724–728 对 processed 输出启动它，1511／1550 对每个正常 NV12 帧排队。profile 的 `pd10` 只决定 PD10/coarse 要求，不是 IPE 总开关。

`src/ipa/camss-vfe/camss.cpp`（SHA `d963f91d…20c`）237–245 在 configure 清空 AGC/AWB/tone 等对象；1075–1077 在没有 `ipeTone_` 时返回空参数、revision0、fresh=false。`camss_ipe.cpp` 153–158 则把空参数转换成全零的 per-frame 请求控制包，仍执行 IPE；这里不能把软件包名 `bypass` 写成“硬件完全未运行”。当前 profile 没有关闭默认 IPE 的能力，也没有现成的 IPE opt-out 环境变量。

本次日志有 240 个唯一 SOF0…239 的 IPE queue、对应成功 receipt 和内核 completion，均为 `revision=0 fresh=0 bytes=0 pd10=0 result=0`，最终 history pending0。capture 返回0、240帧／240 Pair；stepper 返回0、233 SOF／9次控制，两个 mode2 守卫通过。九次写入 pending0、ret/errno0，开始于 SOF 后 48.958…267.709µs，调用持续 530.731…822.554µs，均在下一 SOF 前结束。逐次 `G_CTRL` 检查执行过，但逐次读回数值没有单独打印。

原始线性 BHIST 仍来自上游 VFE：IPA 892–909 从 VFE stats buffer 解析 population／weightedSum，pipeline 1357–1360 按 SOF 保存，1442–1445 打印 Pair 均值，然后才在1511–1550排 IPE。population恒为2491136、上游 ISP revision0／gamma0，DelayedControls0／AWB calculated0，没有 AGC 或动态 GTM/tone 更新。IPE 不会把已配对的 histogram 改成输出图像统计；其负载及背压实际存在，所以本次只能标为“默认单遍 IPE 下的上游 BHIST 控制响应”，不能称“无 IPE 隔离测量”。曝光／增益 metadata 仍是启动上下文，不能用恒定500／64佐证物理阶跃。

最小处理是保留整体失败，按实际链路单独分析既有写入与 BHIST 原件，无需因本断言修改传感器控制或重采。若以后仍要求严格无 IPE，必须在新 core 增量中显式禁止 IPE media 获取／`ipe_` 创建，复用已有直接 VFE 输出分支，并保留默认正常路径；仅换 BLS profile 或删除断言无法满足要求。本轮没有实现、构建或执行这个增量。

[更正收据](ipe-r1-correction-validation.json) 固定29份原件、源 SHA 与私有精简源码证据；原始 scene 数据和逐次写入明细留在私有 `kernel478/ipe-r1-evidence-private.json`。已确认模块／服务／充电恢复、fault0／taint0及外部健康通过；这些恢复结果不改写测量窗口的失败。
