# 157：首次 PHY 重配前停止固件 DSI 控制器

基于实机 156 的首帧门控与桌面启动顺序。156 首次仍有 78 条 DSI 错误，标准 DPMS 24 次无新增；永久显示验收继续开放。

此前 manager 先启用/重配 PHY，再进入 host power_on；固件遗留 CTRL=0x1f5 到此时才被停止。157 在首次 PHY 配置之前，以 runtime PM 获取总线时钟，写 CTRL=0 并读回确认，随后平衡 PM 引用。每个 host 成功接管一次后跳过该动作，已经运行的 native host 不受触碰；失败返回阻止后续 PHY/host 启用，双 DSI 先核实两侧。[候选补丁](early-host-stop.patch)

这是根据源码时序与实机继承状态提出的接管假设，尚需实际启动验证。没有混入 152 worker 同步补丁，也未修改供电、DTB、配置或首帧策略。实际提取两个函数的 15 项普通及 ASAN/UBSAN 测试通过，156 基线两个停机顺序负对照失败。初次测试夹具丢弃日志参数触发 unused 警告，修正夹具后严格编译通过。[函数测试](actual-function-test-validation.json)

W=1、完整 Image/770 模块/DTB、checkpatch 和 FAT 检查通过。模块与 132 的差异继续仅为两个 GNU build-ID note，原模块兼容复用；其它源修改与 156 首帧源码哈希保持。[构建](build-package-validation.json)、[模块核验](module-compatibility-validation.json)

部署前重新确认当前 #156 启动身份，保存重要分区/NV/模块哈希并完成全套停机核验。实际只更新 logdump157。首次启动在 boot CTL shutdown 返回 -22，KMS 初始化失败，Phoc/Phosh 未运行；此时新增的停机路径尚未执行，不能用它解释该更早的失败。

保存初始现场后，单次 panel bind 恢复 DRM，card 索引由 1 变为 0，须按 by-path 解析。此时停机路径读到 CTRL 已为 0，native 初始化无 DSI 错误。第一次 greetd restart 保留 /run/greetd.run，未重新运行 initial_session；备份该空 marker 后停止 greetd、删除 marker、启动原配置，Phoc/Phosh 存在、taint0。实体画面未验证，用户外出。

随后 USB 断开。当前 RAM 诊断启动的 boot ID 与上述持久系统不同，说明发生新启动，原因未知且 pstore 为空。该 RAM boot 再次出现 UFS UIC 超时、分区探测阻塞与首次 CTL -22，没有挂载 F2FS/ext4/vfat。未伪装为首次启动成功；158 将停机位置进一步提前至 DPU CTL 清理之前。[部署工具](deployment-tools-validation.json)
