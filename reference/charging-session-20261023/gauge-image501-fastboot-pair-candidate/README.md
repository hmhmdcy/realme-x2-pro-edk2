# Image501 双载体执行器：未执行

从冻结的 `eud-fastboot-operator-r2` 复用真实子进程等待、PID/startticks、独占动作、未知结果和显式回退控制流。本叶不修改旧事务。

候选为 boot `97811cc4…67f695` + logdump `7e5de5b4…76cbf9`；回退为当前 boot `4126a297…bbfcf` + ACA logdump `aca01bc2…de8da`。两个分区分别为96MiB/64MiB。默认 `check-local` 只读本地四个完整文件及相关凭据，不访问USB。`activation-pins.json` 绑定新激活合同与移除EUD退役后的重启脚本。

真实动作必须提供新 `samurai-image501-fastboot-context-v1` 七份原件上下文及显式执行/窗口参数。旧EUD上下文不能用于本轮。每个动作重新识别唯一原机serial、msmnile和两个分区尺寸。写前核对完整pair，再依次写logdump、boot，原件每次派发前重核。写动作不会自动重启。

`reboot-candidate` 仅接受最近一次完整、成功、终态的候选pair；`reboot-original` 仅接受最近一次完整原件pair。部分失败后必须另行明确执行完整回退；未知子进程或丢失终态时仅查询原动作。无自动重放、超时杀进程、混合pair启动或其它分区操作。fastboot成功还需新系统只读分区回读与状态检查。

本轮6组真实pair/文件/持久动作边界测试及7组新上下文测试已通过；仅fastboot调用为夹具。旧未变函数与既有测试收据直接复用。独立审查见 `../../charging-ui-audit-20261023/image501-tools-independent-review/`。未刷写、重启或声明实机通过。
