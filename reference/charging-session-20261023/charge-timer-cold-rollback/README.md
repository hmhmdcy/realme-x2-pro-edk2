# 停充计时R2：当前两文件逆向与恢复检查

2026-10-24。用户暂不方便现场，本轮全部在电脑完成；没有SSH、手机探测、租约、停充、文件恢复、重启或新boot验收。手机最近实装仍为504/USB13f41/charger97c/保护f6bef/服务83469/manifest5ef4，已有RTC结果只属于该组合。[正向入口](../charge-timer-cold-update/README.md)及[计时修正](../charge-timer-hold-r2-candidate/README.md)尚未部署。

逆向包c72589只恢复charger97c与manifest5ef4，保持USB13f41、保护f6bef、服务83469、Image504和两个启动载体。本入口支持两个明确分支：同一源boot仍驻留旧97c；或另一次504启动已驻留新版bef4。后者即使未通过完整新boot验收，也可在新鲜独立电气保护和原服务INHIBIT成立后恢复磁盘。不会用失败的整套验收阻止必要回退。

`prepare.py`复用原逆向worker的13个函数/类、BaseDevice全部20方法和当前Device的7个方法；原恢复体仅改结果schema。新增当前组合/17份源事务材料认证与只读probe。源事务须为当前正向stage、原同child终态0，包含实际before/stopped/after、旧两文件备份及准确源boot。不能凭目录名、旧pointer或新boot中的复用PID推定事务成功。缓存只接受原schema2/profile1的完整0/0或1/1事实，不重查MAC、不重新授权TCA。

[十个逆向场景](test-result.json)已执行实际stage/atomic/Device文件操作、真实七个安装文件和原service verify/inhibit/command；手机身份、进程、硬件、采样和时钟边界为模型。两种分支、四种源证据篡改拒绝、Full保持、既有fault/timeout保持、Full丢失拒绝、第二次rename失败保留已知partial及查询进行中拒绝均通过。恢复始终保持INHIBIT，不AUTO、不热卸、不修改载体。partial/unknown须检查原事务，禁止自动重放。

[主机接线](host-test-result.json)在真实传输边界前截获：准确逆向包、restore入口和原同child supervisor匹配。只读probe用现有共享锁、夹取实际身份/notes/缓存和完整载体，成功后才在电脑保存未来请求和previous pointer；该probe本轮未运行，也未制造现场身份。

[恢复启动检查](recovery-contract-result.json)：两分支共16个实际只读重启门场景、10个恢复验收请求场景、2个实际本地adoption/CAS场景通过。错误驻留、错误磁盘、恢复结果变更、原boot冒作新boot均拒绝。adoption取逆向final_files中的旧manifest，并清除当前PM、物理USB唤醒、计时候选已加载/已验证等标记；历史证据另存。传输和设备执行明确为模型，未修改真实pointer。首次测试仅因临时BASE映射未保留collector来源而失败，修正fixture后通过，未改变设备算法。

[原十二项检查模板](postboot-local-result.json)接受缓存的旧97c实装材料、拒绝新bef驻留note。`restart.py`沿原完整硬件收拢和EUD-off正常重启尾，无刷写；当前两分支动态核驻留note。新版已驻留时须正常重启才能实际恢复旧驱动；同boot旧驱动仍驻留时无需为了磁盘恢复强制重启。执行器不会自行重新启充。

电脑材料在 `E:/edk2-samurai-out/charging-management-20261023/charge-timer-cold-rollback-live-20261024-01/`。目前仅worker、逆向包、重启源码模板与postboot模板；没有request-private、实际preflight、launch或原worker运行目录。`host.py`默认check；未来按实际情况依次preflight、launch、fetch，核原worker终态0和all_original_fsynced。需冷启动时再用restart quiesce/restart及原fastboot正常reboot，之后postboot run/adopt。每步要求前序真实结果，已结束事务不重放。

这补齐了计时R2的可执行回退路径；不代表真实待机USB唤醒、新计时状态转换、10小时循环、温界、低电预充/Full再充、精确2719/TCA语义或快充已经验收。桌面未改，无子代理。
