# 当前两文件冷回退后的恢复重启：设备检查

2026-10-24。承接[已接通的回退执行](../irq-native-usb-pm-rollback-connected-candidate/README.md)。本叶只完成恢复重启的证据审核、设备检查和原硬件执行尾复用；尚未接主机调度和单logdump operator，未操作手机。

旧恢复脚本针对旧R8三文件、只认502并写boot97811，不能直接用于当前USB/manifest两文件回退。这里核对当前6818939b及监督终态，支持同boot502旧驻留、504/4453新驻留、502/ace2新驻留三种分支；目标仅为logdump ace2，bootedd始终只读。

`proof.py` 复用原进程/原请求/原输出审核：完整十四项rollback原件、两进程真实wait0、两文件原版精确读回和相同已结束进程。当前notes按实际profile字典校验；before/stopped/after保护缓存必须对应同一原请求。写回成功继续是runtime_pending。

恢复后必须另做一次原严格密钥固定压缩只读probe。它沿现成current-probe的四字段请求，在来源绑定摘要内纳入本次rollback请求、成功结果与原binding；不能把还原前probe用于恢复重启。身份/载体/notes按实际worker校验，cache三夹与还原后cache一致，BOOTTIME必须晚于还原完成观察。`review_completed` 调用现有host的原launch/fetch审核，不派发任何命令。

`common.py` 保持原15个通用检查函数，改当前证据/manifest与三种内核profile。设备端再次读取十四原件并调用实际6818来源验证器，仅抑制其证据日志，绝不调用Device.begin/stop/replace。保护mac_evidence持有同实例只读fd，允许未捕获0/0或已终态1/1，拒绝1/0；不发新MAC查询。

恢复检查直接复用实际6818的safe_stopped、idle与retained函数：真实新鲜电芯/温度、独立保护、硬件INHIBIT、原输入/CC/CV上限和寄存器对应必须成立，旧Full/fault/timeout/cache必须保持；不要求USB预算已恢复或OpenRC标记已启动，不因预算0/ENODATA去提高额度、AUTO或清除故障。相机空闲与原厂保护仍检查。新source读取只把不可读的USB属性保留为errno观察。

`eud-quiesce.py`、`eud-restart.py` 仅替换嵌入的common。原脚本前缀及硬件收拢/RESTART2尾逐字保持；默认不执行。没有新热卸模块、服务恢复、刷写或自动重试逻辑。

六组定向检查与三个默认入口通过、原本地child均wait0：原15函数/硬件尾、三profile原件及目标、恢复后cache/时间、设备原件审核及只读来源验证、未知预算/Full/fault保持、临时普通文件上真实只读fd与inode变化拒绝。设备/来源IO边界建模；不是实机恢复、真实寄存器验收或重启成功证明。测试最初多行with括号遗漏在解析阶段拒绝，原文件及失败记录保留，生产逻辑未因此放宽。

下一步复用原主机owner与当前单logdump工具，补独立恢复事务、后置probe发送、预检两个fd独立释放和七原件context接线；再补新boot验收。齐备后才安排串行实机。手机最近确认仍502/edd/ace2、7cb/97c/7848/18e8，桌面和相机保持。
