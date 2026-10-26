# 当前两文件冷回退后的恢复主机接线

2026-10-24。连接[已验证的恢复设备检查](../irq-native-usb-pm-rollback-restart-device-candidate/README.md)与当前C5 owner、当前单logdump工具。仅离线完成，尚无实际request、lease、SSH、USB、收拢、重启或刷写。

`controller.py` 沿原R2的实际进程调度方法；修改模块变量不会改变Python函数已绑定的默认目录，所以新增薄 `run` 入口，始终显式传入本适配器PRIVATE。六文件request、同child监督、35秒pending、unknown只查询/取回、原启动传输回执均复用；不重复运行旧owner矩阵。

后置 `probe` 先审核已成功两文件回退的原件，才创建新私有输出，调用原固定压缩严格密钥 `send_readonly`，再按本次request/result/binding复核。probe路径只准本PRIVATE的 `probe-[a-z0-9-]{8,48}` 新目录；失败保留原输出，同目录不重试。需要明确执行及当前窗口标记，默认不发送。

`bind` 使用当前三profile/14原件/同实例cache/后置probe派生独立恢复guard，原C5 owner接prepare、quiesce、status、fetch、inspect和restart。`common.py`、`proof.py`、两个硬件脚本逐字复制冻结22cf设备叶，supervisor逐字复用。remote采用已经验证的当前C5 preflight：自身MAC fd与service flock各自释放，关闭一个失败仍关闭另一个，并保留原检查错误。

`export_context` 生成七份实际原件引用。附带的 `fastboot-operator.py` 使用当前单logdump operator，限制为inspect、rollback-original和reboot-original；每次沿原local_inputs验证现成材料，再仅保留original/logdump ace2，bootedd只读。命令、原子claim、原Popen等待与worker函数保持。SSH255只证明原传输终态，不证明已进引导器或重启成功。

实际CLI支持默认check-local、probe、bind和上述owner动作。主机子进程 `_ssh-worker`、工具 `--_worker` 均继续委派原owner函数；新owner源hash/目录属于本适配器，不调用旧会话的owner。还原两文件以及恢复重启命令返回都不能关闭runtime_pending，仍须新的boot502/ace2与旧USB7cb/保留97c/7848的实际驻留、充电保护/USB/相机核验。

## 定向验证

六组及三个改变的默认入口通过，原本地child均实际wait0：

1. 当前设备文件与原supervisor逐字相等；C5七项关键调度函数保持；固定-C、original-only logdump材料和候选方向拒绝。
2. 实际 `review_completed` 接本次后置probe及原R2固定压缩回执审核，早于还原完成的probe拒绝。
3. 实际bind/新bound、六文件allowlist/临时设备安装，薄run不显式传private参数也进入本次目录；同事务pending不重派。
4. 当前preflight的两fd关闭与原错误保留，包括第一个关闭失败的组合。
5. 七文件export直接由当前operator消费；原worker inspect函数使用模型命令输出，旧schema拒绝、SSH255不当启动成功。
6. 后置probe只读接口、部分输出保留/不重试，以及两种原worker dispatch接线。

来源、设备、进程与传输IO边界建模；固定逆向包、当前profile、安全检查与原回执审核为实际函数。没有真实fastboot命令、手机原件、新boot、USB恢复或硬件重启证明。原设备六组及旧调度矩阵按未变源码复用，不重复执行。

下一步接当前504/4453正向与502/ace2回退的新boot核验/adoption，之后确认真实手机状态和串行现场窗口。最近确认的手机仍502/edd/ace2、7cb/97c/7848/18e8，桌面与相机481/468保持。
