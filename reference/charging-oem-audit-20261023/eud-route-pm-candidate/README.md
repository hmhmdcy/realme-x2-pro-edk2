# EUD-off 路由跨待机恢复：Image506

2026-10-25。已实际安装并采用 Image506。正常待机从“永久退休”改为“暂停、join、恢复复核”；移除、证据损坏或恢复失败仍永久失效。手机当前 boot5c8d / FATb29e、USB161b / chargerbef4 / 保护f6bef / 服务83469 / manifest8b402，原桌面、启动固件、所有模块和永久 rootfs 与上一轮505完全相同。

[实际装机和两轮RTC](phone-activation-result.json)均通过，驻留15.076秒及14.855秒，分别success+1/fail0，所选12条回调err0，实际路由complete回调在dpm_complete阶段出现；无路由复核失败日志，原key/NCM、SDP源/native/硬件500mA、CC250mA/CV8.725V和保护正常恢复。两原worker6389/6687终态0、已退出，独立trace和alarm清理，最终AUTO Full/cause3。当前缓存0/0、cc134保持，未查询或rearm MAC。新外部USB KO的正常O taint4096不变。

两轮实际prepare/complete、匹配源码和无失败日志支持正常恢复路径；**待机后的真实物理新连接/APSD传输仍未测试**，不据此宣称完整APSD、物理USB唤醒、图标提速或快充通过。内核未启用function tracer/kprobes/kcore，没有为检查状态开放这些接口或读取内核RAM。

来源直接复用已安装505的[provider](../eud-route-provider-candidate/README.md)、[实际owner](../apsd-eud-route-client-candidate/README.md)、主线qcom EUD已有CSR定义及原BDS关闭交接。本机实际EUD节点只有compatible/reg/status/phandle，没有额外clocks属性。provider先获得真实producer排他，再申请0x088e0000+0x2000资源并映射；唯一新增硬件操作是在原CSR+0x1014连续读取两次，要求均为0。每次begin/validate及正常PM complete均同时复核EFI记录和现场CSR；没有写CSR、FIFO或中断清除寄存器。

正常prepare先标paused并换代，禁止旧lease使用，再调用真实owner的pause_join，停止任务并按原顺序恢复PHY、DWC和PD。complete仅在交接与CSR仍有效、未被撤销且没有遗留lease时解除暂停；owner仅清自己的route暂停位，不清其它PM/PD/PHY/UDC fence、不制造首次物理off、不重复本周期命令。失败保留原错误和排他，不自动重试失败的PHY恢复。永久移除继续使用原cancel_join；失败退休保留映射和资源，直到实际join完成，在放行其它producer之前才释放。

[源码复核](source-review.json)确认owner只修改原resolve一个函数，新增pause/resume，另外36个完整函数逐字保持；producer仲裁、原永久退休、PD/PHY/once和预算函数保持。[provider测试](provider-test-result.json)为原12组加11组真实pthread/引用/暂停边界，[整合测试](owner-test-result.json)为原8组加5组完整owner/PD/PHY/route C；OS、调度和MMIO边界建模，不能替代实机传输。

provider初稿测试发现重复prepare会把失败pause转为退休重试，已修复为保留原暂停结果；owner初稿只在新模拟命令尚未完成时提前拆卸，修正测试收尾后通过。真实首编译发现EFI目录重复本地头文件仍为旧版；补齐第四个输入后，[增量构建](image-build-r2-result.json)通过且零诊断，首编译失败保留。配置、全部builtin导出、电量计、initramfs和builtin元数据均与505相同。

| 实际私有产物 | SHA256 | 字节 |
| --- | --- | --- |
| Image506 | c03cf30de35a3a621dff2568805e098656d499de45d5ce9af39c802e74356c24 | 59374080 |
| logdump/FAT | b29ea41a7a076555f5f6848c9f343dbd8fb0f9271adbd4d3acd4fff9d092b0ff | 67108864 |

[FAT检查](logdump-package-result.json)复用505构造器，仅替换Image；读回、fsck -n、另一个DTB和其它所有字节保持。此次实际只写logdump，boot校验相同后直接返回，没有重新刷写。正常重启后原key/NCM自行恢复。临时试运行guard经新boot接纳后正常退出；两RTC后恢复精确原manifest/OpenRC并删除临时helper，永久rootfs没有变化，后续正常重启没有新接纳倒计时。

[当前逆向](inverse-result.json)为仅恢复已采用505 FAT b388并正常重启，boot5c8d及manifest8b402不变；保留稳定分区UUID/起点/大小/编号检查和完整本机备份。实际逆向未执行。505到504的完整逆向属于上一轮，不能与本轮混用。所有已终态构建、stage和RTC入口禁止盲目重放。

仍需完成：首次物理off/新连接、FLOAT及完整APSD（含PM之后）、物理USB待机唤醒、2719精确语义/TCA、温界、低电预充、10小时计时及高功率/快充。C盘约19.46GB、E盘约153.57GB可用；两份已传输压缩包清理被自动审批审查拒绝（blocked by policy），文件暂存，未绕过拒绝执行删除。
