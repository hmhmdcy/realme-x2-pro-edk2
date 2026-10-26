# 停充计时R2：当前组合的冷更新入口

2026-10-25，**已完成真实冷暂存、正常重启、fresh采用和本组合RTC恢复**。用户已授权睡眠期间操作手机和刷入，无法人工拔插；唯一根会话操作，相机暂停，无子代理。[实际结果](../../charging-management-20261023/charger-timer-activation-result.json)保留全部失败及重试范围。

手机当前504/Y、bootedd/载体4453、USB13f41、chargerbef4、保护f6bef、服务83469、manifestf15ecc，bootbc612，已采用。原stage worker终态0、all_new_fsynced，Full保留至正常重启；未写启动载体。原重启派发SSH断开返回unknown，先查到唯一fastboot设备后只正常reboot一次，原key/NCM自动恢复；未重放派发。首次启动采集因保护driver尚未绑定失败，保留；第二次只读采集和fresh采用十二门通过。`postboot.py`已修为从实际成功的postboot-r2取缓存hash，原文件归档、定向adoption/CAS测试通过。[本组合RTC](../../charging-management-20261023/charger-timer-rtc001-result.json)15.439秒、success+1/fail0及前后十二门通过，500/250mA/整包8.725V、原key/NCM恢复和清理均正常。旧4e325/97c的15.019秒仅为历史。

冷更新沿已实测成功的USB冷暂存执行器，只将目标文件改为charger及manifest。原子写入、停止、Full/故障/预算保护与所有Device方法保持；`derivation.json`记录变量重命名、精确manifest差异和两处长度/阶段标签变更。只执行原服务的同步INHIBIT，不热卸、不AUTO、不加载新模块；旧驻留驱动、逻辑Full和周期状态一直保留到正常重启。当前Full不应使用旧charger热更新工具。

安装前已离线验证以下新组合边界，原结果范围保持：

- [五个冷暂存/恢复场景](test-result.json)：成功、charger和manifest重命名失败、完整新清单验证失败、目标已写后保护证据变化。使用真实七个安装文件、真实service `verify`/ELF note检查及实际stage/atomic/Device.replace；只有手机身份、硬件与实时状态为模型。普通写入失败精确还原旧两文件并保持INHIBIT；保护证据变化则保留已知partial并停止继续动作。
- [主机派发接线](host-test-result.json)：实际前向包和c72589逆向包、原同child supervisor完整进入原传输封装，边界处截获，无真实传输或租约。
- [八个重启前只读门](restart-contract-result.json)：两个原owner的正常模型、错误驻留charger、错误磁盘charger和stage结果变化，均在任何收拢/重启尾之前判断。原完整相机/音频/DSP/显示/NV/EUD-off尾保持，新增旧charger note门；无载体写入。
- [启动模板](postboot-local-result.json)：保留十二项检查，明确要求bef4/1df0新charger；缓存的当前97c实机数据被拒绝，修改安装字段的模型通过。没有制造新boot、guard或运行验收。PM和物理USB观察器沿原一次mem、RTC回退及独占trace，只按未来新boot重新准备。

电脑端材料位于 `E:/edk2-samurai-out/charging-management-20261023/charge-timer-cold-update-live-20261024-01/`。已保存当前pointer、请求、源码、两份restart模板及postboot模板。`host.py`默认只核本地；原子stage代码、主机、重启、postboot、PM入口都要求各自前序真实结果。先前旧物理USB窗口属于4e325，若采用新驱动则必须重新绑定新boot，不能复用旧窗口。

上述`preflight`、`launch/fetch`、`quiesce/restart`、实际fastboot reboot、`postboot`和`pm`均已有原事务终态；**不可重放**。当前[有界自然放电/回充观察](../charge-timer-hold-live/README.md)独占服务锁，须先查原worker终态与清理。物理USB窗口尚未启动；旧4e325窗口不能覆盖本boot。partial/unknown先查原事务，不能重放或直接重启。

精确逆向包c72589仅恢复charger97c/manifest5ef4，USB13f41、保护f6bef和服务834保持。[同boot旧驻留/新boot新版驻留两分支的逆向入口](../charge-timer-cold-rollback/README.md)十个恢复场景及恢复后启动/本地adoption检查离线通过，实际逆向未执行。计时切换和真实回充正在观察；十小时、真实USB唤醒、温界、低电预充到Full完整循环仍未验收。

本轮另定向检索了DeviceType2719/完整固件指纹及GaugingStatus长度，未取得足以确认本机TCA位语义的精确原厂描述；没有据此更改保护分类、扩大白名单或重新查询电池。
