# 179：相关机型参考与 PDR/QMI 接收锁阻塞

2026-10-14。核对Realme官方19781 overlay和OnePlus 7T Pro0039补丁：171实际使用SD1/GPIO140修复并得到用户双组滴声确认，UCM与麦克风闭环方法也已采用；不同功放/字宽/增益保持本机依据。新找到OnePlus 6/6T MBHC阈值提案，按本机校准取值的方法可参考，未套用其数值或宣称耳机通过。

使用实际PDR四函数及QMI RX/txn函数，薄适配提供control后有效reply：原函数遇无关NEW/DEL或匹配DEL均因list_lock阻塞RX而超时；直接reply成功。仅锁外等待的因果对照三例成功；总七场景，ASan/UBSan执行与最终编译stderr空。证明锁缺陷存在，尚未直接测量178实机的具体触发顺序；对照不是可部署补丁。

没有修改/构建/部署新内核或重启ADSP；只读实机仍#176、taint0、ADSP running、单声卡、两个PCM closed。178真实失败保留。下一步修事务/通知世代及寿命、release顺序和MFD parent IRQ退出，随后构建并验初启动/恢复。详细脚本、七场景收据和来源见[179](../reference/kernel179/README.md)。完整音频goal active。
