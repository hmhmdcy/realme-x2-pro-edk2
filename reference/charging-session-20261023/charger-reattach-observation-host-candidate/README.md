# 当前IRQ状态下的单charger更新主机入口

本叶接入已实际采用的#502 IRQ启动、当前500mA预算及[两文件增量包](../charger-reattach-observation-payload-candidate/README.md)，不再沿用已结束的R7/R8身份。默认只核源码，实际命令通过WSL Linux运行。`bind`必须先重审原IRQ完整postboot与fresh adoption，再生成唯一请求；没有真实完成的原件不能创建绑定。

`preflight`把同一冻结worker的只读入口经原严格key、固定`-C`发送到stdin，不在手机创建目录、租约或worker。只有健康Managed才可更新。健康Full会返回`passed=true, eligible=false, reason=full_state_not_restorable`；`launch`在这时不进入启动意图或远端流程，设备worker也在停充前重核同一门。这里没有新增“恢复Full”的内核参数，也没有用AUTO清除Full历史。

实际更新只允许charger10ec/manifest5fca到charger97c/manifest18e8；原USB7cb和保护7848的驻留note、持有的kernfs属性FD、已经消耗的MAC原缓存、实际源预算、相机闲置及桌面服务前后保持。原全局boot-adoption pointer保留为原IRQ采用记录；热更新若真实成功，另以运行时证明供[后续采集](../icon-capture-irq-reattach-runtime-candidate/README.md)审核，不能假装创建了新boot。当前Full预检不能晋升成成功更新或新采集身份。

进程机制直接复用R2 `transfer()`原体，仅SSH argv添加`-C`。远端仅替换已有capture remote的事务前缀、schema和`device-update`输出目录；supervisor逐字复用，继续持有同一个worker Popen直到真实wait终态。`status/fetch`只读原事务，结果未知时不能重新launch。SSH原stdout/stderr、发送源码、child和终态均保存；取回原件不等于运行验收。根当前独占手机且相机继续暂停，`--window-confirmed`由已持有窗口的协调者提供，不能替代真实设备检查。

主机侧六组受影响检查已覆盖请求/包tuple、Full与显式窗口门、实际复用transfer的-C/owned stdin close与wait/重复launch拒绝、预检响应身份、原请求/worker篡改及status/fetch不重审可变pointer。原Windows首次运行四组通过；两组分别因Linux-only `fcntl`导入和fixture遗漏`subprocess.PIPE`失败，失败源码和结果保留。只修fixture的PIPE并在目标WSL重跑这两组，均通过，另外四个函数AST未变并复用原成功记录。没有重跑旧R2矩阵，也没有把fake Popen当真实手机收据。

实际唯一绑定、只读预检或现场更新结果记在充电当前入口；本叶源码/测试不能证明已经安装、保护同实例运行验收、真实提速或USB/PM恢复。
