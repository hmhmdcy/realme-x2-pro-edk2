# APSD接入当前USB IRQ／PM源码

2026-10-25。把[最终传输边界](../apsd-final-transfer-candidate/README.md)合入实际USB13f41模块对应的源码1ad0c168，保留当前IRQ、native供电依赖、通知和唤醒引用。默认`apsd_backend=false`；未编译ko/Image、未安装或启用，缺少路由授权的原owner仍拒绝全部APSD命令。

使用原`event_dev`作为真实source device，只添加计数与注册状态。probe在PSY/清理动作就绪、解除paused并释放input锁后才注册。prepare先发布`pm_prepared`，锁外withdraw/join检测任务；真实backend在prepared期间直接拒绝读/命令。stop先发布paused、锁外withdraw，再join原poll。resume仅恢复原预算和IRQ；complete发布正常通知、释放input锁后才重新注册，避免在挂起/早期恢复阶段重新启动检测。失败挂起和无suspend的prepare取消也在complete恢复注册。

原sample serial、已尝试epoch及owner物理历史跨重新注册保持，不清原生预算或保护来制造测试条件。只有resume原本已有的native失效保持原样。注册仍在所有input/IRQ/组件锁外，join不会等待一个持有input锁的回调。原devres停止→wake清理→PSY→IRQ顺序保持。

[十组实际传输测试](transfer-test-result.json)覆盖前版九组及当前prepare期间零I/O拒绝。[十五组IRQ/PM测试](pm-test-result.json)执行真实十四个当前回调与start/withdraw，包括原十组IRQ错误恢复、新完整PM、prepare取消、失败挂起、shutdown和注册前置状态；owner注册/join和IRQ API为模型，ASan/UBSan/Werror通过。真实USB物理唤醒仍未验。

[唯一新增input对象](build-result.json)沿原编译命令W1/Werror零诊断，复用已冻结owner/PD/PHY对象进行内部relocatable检查，无内部未决。二十二个当前函数逐字相同，包括budget、IRQ、wake、native-link和resume；四个改动函数为stop/prepare/complete/probe。共享source/config/build保持，未用SDK、未重建未变owner。最初挂载器hash抄写错误在构建前拒绝，修正为原值后编译；没有修改挂载器或跳过校验。

`current-usb.patch`只对当前USB13f对应C应用；同目录新include/API与前版owner须成套接入。后续仍需可信EUD-off路由supplier及其撤销、实际Type-C设备/同Image builtin配置和真实新连接周期。当前m配置及已安装USB13f保持，离线对象检查不构成可直接热装模块或完整APSD/PD/快充验收。
