# 当前 IRQ／97c 基线的 PM 启动调度

本叶把当前冷 stage、启动设备门和单logdump operator接起来，沿用原IRQ activation host R2。源仍为实际502/bootedd/logdumpace2/USB7cb/charger97c/保护7848/manifest18e8；stage仅把磁盘USB/manifest改成d046/34ead，原驻留实例保持。目标为504/4453，bootedd只读。

默认 `controller.py`、`remote.py`、`supervisor.py` 只做本地来源检查，不绑定运行身份、创建事务或访问手机。显式接口仍为 `bind → prepare → quiesce → fetch → inspect → restart`；bind接实际当前stage目录和一次原fetch目录，全部来源审查先于创建owner或guard。没有把测试fixture或未来boot填写为实际身份。

绑定使用本次真实IRQ adoption＋完成的97c热更新所证明的18e8来源，经当前stage-proof完整审核，再生成独立 `irq-native-usb-pm-activate-...` 事务。guard源版本精确502，目标504；原IRQ adopted guard三字段、17份stage原件、当前输入/保护/INHIBIT及相机门由设备另行核对。旧pointer5fca不当作当前磁盘清单。

23个主机函数、10个remote函数和完整quiesce supervisor逐字复用。原R2的durable once意图、实际Popen、stdin EOF、同child wait及独立finalization保留；临时断线、未知结果或超时只查原事务，不重发。原strict key和端点保持，SSH仅增加固定压缩 `-C`。没有新刷写器、模块卸载、AUTO或充电控制路径。

新common的只读预检还会持有MAC缓存fd。remote在派发worker前分别释放自己持有的MAC fd和服务锁fd；一个关闭失败仍尝试另一个，并阻止继续派发。原健康异常作为主异常保留，关闭错误附在异常中。实际worker独立取得同一服务锁，不继承预检资源。

`host-context-private.json`保持原七份收拢/派发原件与既有restart claim/dispatch schema，使用新的 `samurai-irq-native-usb-pm-fastboot-context-v1`，增加准确的 `source_review_inputs`。SSH255按255保留，不等于RESTART2成功；原终态已留存时，在下次网络查询前导出context。后续必须由独立operator重新确认唯一fastboot设备并核分区几何；本调度器不执行fastboot。

六项新实际函数组合通过：当前guard/端点绑定与重审、缺失/旧来源/改变端点在mkdir前拒绝、原未知意图不重复派发、两个预检fd成功/健康失败/关闭失败的释放、当前export与实际单logdump context核验相接，以及旧23/10函数和supervisor字节复用。最后一项export保留模拟原SSH255，仍为syscall结果未知。设备、stage和进程边界均明确使用临时模型；旧R1十二项/R2三项及其它旧矩阵未重跑。三个默认入口原child wait0，无实际运行绑定、SSH、USB、收拢、重启或刷写。

**完整实机准备仍待完成。** 首先补504/4453与原502/ace2两个启动分支的两文件冷回退，再接新boot只读采集/adoption。新采用可能推进全局pointer；当前forward stage-proof要求原pointer仍为5fca，不能在pointer推进后把forward context当作通用恢复入口。回退来源审核需使用留存的实际adoption/update/stage原件，而不是要求全局pointer回到旧值或伪造新采用。新boot回退还不能依赖“整套postboot已经通过”，否则会丢失启动部分失败时的恢复路径。完整回退仍是USB7cb＋manifest18e8＋logdumpace2，并正常重启；单载体回退不代表全部恢复。
