# GATT清理P1离线修复

修改[phone-gatt-peer.py](../../bluetooth-le-peer-20261023/phone-gatt-peer.py)的异常清理链。旧`096d01f8…f8694ff`版本在`stopping=True`后写日志，write/flush失败会跳过注销和恢复；旧run.finally又因stopping为真而跳过补救。本轮没有手机、SSH、WinRT、SDK、HCI socket或实际D-Bus连接，没有重建其它组件。

新源码SHA256：`a1f7c44c8e863bf1fcec9e9e507c4e9d621b0410b17e38b9750f76cae33c9004`。旧原字节保存在私有输出的`phone-gatt-peer-096d01f8-before-cleanup.py`；旧r2实机、ssv及其它历史验证摘要保持原版本，不改写成新代码验证。speaker和联动器的固定摘要由父线统一更新，本线没有修改这两个脚本。

清理现在分别记录stopping、cleanup_in_progress和cleanup_complete。stopping先关闭数据访问；重入返回而不重复动作；外层finally按cleanup_complete决定是否仍有清理工作。每项动作独立捕获异常并记录已尝试状态，日志失败不再把已成功的资源动作改成失败，也不截断后续动作。原生monitor的socket close失败仍尝试限时join；应用子对象撤除失败仍撤除其它对象和root。btmon的poll/signal/wait失败后继续对自己拥有的子进程kill/reap，捕获日志、control bus、events文件和loop.quit分别执行。

D-Bus清理共享首次建立的30秒monotonic截止时间，每调用最多3秒，重复stop不重置预算或重发已尝试动作。btmon等待最多3+2秒，原生reader join最多1秒。保留原身份与owner门禁：首次身份未通过时不做adapter恢复/peer Disconnect；owner查询异常或更换时不向未确认owner发状态写，但仍撤本地对象、关闭注册bus/捕获/control并尝试退出loop，明确报告恢复未完成和非零退出。所有BlueZ代理仍固定原unique owner，不激活新daemon。

[check-cleanup.py](check-cleanup.py)直接执行实际修复后的PeerRun.stop/run/cleanup_call、Application.remove_all及NativeMonitorCapture.close；用本地模拟对象注入错误，不以复制的清理算法代替被测方法。[validation.json](validation.json)记录29项通过：

- 重现旧096d日志write失败后未关闭capture/未quit的缺陷，再核新正常路径。
- events write/flush、summary写、stdout写、owner异常/替换，以及组合故障。
- 注册代理、单项注销、Disconnect、单项adapter恢复、应用子对象移除失败后仍执行其它独立步骤。
- private bus、native capture、control、events close及loop.quit异常均保留错误；后续可执行步骤仍被调用，故障退出为1。
- btmon正常、poll/signal异常、wait超时、capture日志close故障；验证owned-child终态与必要kill/reap。
- 先前stopping但未完成、实际run.finally补救、嵌套stop、共享预算已耗尽及重复stop不重发。
- 实际NativeMonitorCapture.close在socket close异常后仍尝试join。

测试原件在私有`bluetooth-static-fixes-20261023/gatt/regression-r2`。本报告证明局部异常隔离和有界调用安排；不能证明真实设备恢复、底层close/quit必定成功、不可中断I/O不卡死或实际协议/音频通过。底层动作自身失败会保留失败状态；summary本身写失败时依靠内存错误和非零退出，不能宣称已保存完整报告。
