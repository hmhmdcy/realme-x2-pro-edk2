# Image502：严格本机 BQ 即时通知增量

根会话已授权唯一私有构建；本叶只接受已 passed 的 Image501 repro 三树为基线，不用当前共享 build 的后续对象作为链接输入。新输出固定 `/home/cy122/charging-management-20261023/gauge-image502-notify-01`，已有目录拒绝重放。原363、原501及已冻结 BQ 通知候选保留不改。

本轮唯一源码改动是相邻 `gauge-notify-immediate-candidate` 的 BQ 单函数增量；构建版本由501改为502。仍是原 release `7.3.0-rc6-rmx1931-samurai-k363+`、原 CONFIG／公共 header、user／host 和 `Tue Oct 20 03:03:47 UTC 2026` 可复现时间戳。实际执行 UTC 独立记录，不能把内核显示的复现日期称为本次执行日期。瞬时模式仍默认 false，现有启动载体中的 opt-in 参数不在本叶改动范围。

## 执行与核对

`run-502.py` 从已冻结501 runner 独立派生，所有实际差异在 `runner-vs-501.diff`。`prepare-runner.py` 对原 runner 和替换点逐字核对后生成新件，没有改旧脚本。metadata helper 只将比较身份从363→501改为501→502；它只读取和比较 ELF，不回填产物字节。

默认不调用 storage、compiler 或设备：

```text
python -B reference/charging-ui-audit-20261023/gauge-image502-notify-candidate/run-502.py --check-local
```

实际执行需显式 `--execute-502`。原 Ubuntu/root kernel284 helper 验证／恢复原32GiB卷；在 OEM 与 session 最后私有对象均真实终态交回后才进入。独立复制501 build／source354／input-initramfs363，验证内容、属性和没有交叉硬链接；新 mount namespace 全部递归 private，并在该 namespace 内绑定原 canonical 路径，复用已证明的编译输入和命令。父 namespace／mountinfo 与共享关键输入前后核对。无 SDK、Git、设备、boot 载体、DTB、模块或安装目标。

仅执行原 W=1 的 `bq27xxx_battery.o`→`Image`。严格与实际501比较：3247个 archive 叶只允许 BQ 与 version 叶变化，其余3245叶、32个 libstub 及成员次序保持；全部 `.o` 只允许这两个叶、version-timestamp 与链接派生的 vmlinux／两个 kallsyms。两个 version ELF 必须整体精确等于 `#501`→`#502` 身份串替换，可执行 section 不变。CPIO／gzip／usr对象保持原三个 SHA，396项 initramfs 输入属性／数据保持。

15097个导出的实际 ELF 名字及完整 symvers 行、原 Module.symvers、release／CONFIG／公共 header 均须与501相等，才复用原501 ABI 与 CCI provider 补充收据；不重扫778个模块，也不冒称新类型 ABI 或模块实装通过。新 BQ 仍核默认 opt-in 变量为零初始化 BSS。编译诊断有任何 warning／error 均拒绝 passed。

## 状态

实际唯一执行已通过：原 native exec22677 终态0，WSL parent805、namespace worker1573均结束；BQ目标5.07秒／Image43.37秒，各终态0。编译诊断为空，父进程最终再次核对501三树、363关键原件、shared关键输入、父 namespace 和 mountinfo 均保持；无存活构建／guard过程，未卸卷。详细终态在 `build-result.json`／`execution-receipt.json`，ABI精确比较和原收据复用在 `abi-reuse-result.json`。

新 Image 为59243008B，SHA `085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955`；vmlinux为190304168B，SHA `8a7065fb414f7578191622a732a59699554efe1d8fd0bfe87050547b544d6222`。真实文件在上述私有输出下 `build/arch/arm64/boot/Image` 和 `build/vmlinux`。新 BQ对象为 `b30ea227…ab6e6d4`；单对象验证用了另一 source／output 路径和保存命令，两者没有做逐section差异归因，不能混作同一物理产物。公共交付只包含源和收据，不带二进制。

实际叶差异恰为 BQ和version，余3245叶／32stub及顺序保持。所有对象差异恰为 BQ、version、version-timestamp、vmlinux和两个kallsyms；两个version ELF逐字仅 `#501`→`#502`，不是手工热补。15097个导出名字及整行symvers均精确相等，CONFIG／release／公共header与原initramfs也保持。因此复用501与精确CCI provider补充的静态范围，不额外宣称类型ABI或实机通过。

旧基线、旧失败和本次原件保留，不自动重试。未制作新的启动载体，未部署，也没有新的物理拔插延迟验收。Phosh／UPower／新增桌面提示路线已取消，本叶不恢复该分支。
