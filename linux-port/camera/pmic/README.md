# RMX1931 双 PM8008 实验部署源码

**本目录233实验源现为历史/回退资料，不用于新构建。** 267已在手机撤掉独立lab供电模块、板级reset provider及实验loader配置。当前使用[公共MFD](../../../reference/kernel267/qcom-pm8008.c)、[公共regulator](../../../reference/kernel267/qcom-pm8008-regulator.c)和[RMX1931 DTS](../../../reference/kernel267/sm8150-samurai.dts)，已同步维护内核分支。GPIO、电压和地址依赖从DT提供；原生cam及Snapshot前后摄预览/切换/拍照通过。[267供电验证](../../../reference/kernel267/README.md)、[268应用验证](../../../reference/kernel268/README.md)。以下模块参数和加载配置仅描述旧实验，不再部署。

阶段233实际运行的复位/地址组件完整源码及锁定信息。P目前只验证身份，不创建regulator/MFD子设备；后摄尚未出图，产品供电schema、VIN父网和完整kernel/rootfs整合仍未完成。

`qcom-pm8008.c`替代195版MFD，`reset-realme-rmx1931-pm8008.c`为独立板级provider；`Kconfig.fragment`/`Makefile.fragment`用于drivers/reset接入。`experimental-p-identity-only.dts`从实际部署219板源生成，启用P实验身份；保守的`product-p-disabled.dts`禁用P。不能与旧MFD混搭后声称依赖已验收。[原生部署证据](../../../reference/kernel233/README.md)、[复位契约](../../../reference/kernel232/RESET-CONTRACT.md)

与当前183兼容环境中的实际编译使用两个树内目标及 `CONFIG_RESET_REALME_RMX1931_PM8008=m` 命令行覆盖，未伪造MODULE_INFO。当前canonical配置/全局产物仍保留after228；这里不是完整内核重建完成的声明。精确临时构建、备份恢复和符号检查见[构建器](../../../reference/kernel232/build-modules.py)。

模块加载前配置：

```conf
options qcom_pm8008 experimental_p_address_only=1
softdep qcom_pm8008 pre: reset_realme_rmx1931_pm8008
```

实际udev自动加载早于OpenRC modules服务，模块依赖需要覆盖该路径。模块/DTB/boot、参数和源代码锁在[source-lock.json](source-lock.json)。233回退资料在设备k233-baseline及k233-module-stage，boot219在私人219；使用时核当前启动身份，配套恢复文件与模块元数据/配置。可正常清理重启，或在停流、释放并移除children/消费者后评估卸载；当前操作规则见[边界](../../../WORKING-BOUNDARIES.md)。

GPIO逻辑读取及trace可能来自SPMI软件缓存，不称管脚物理读回。P缺参数在解除复位前拒绝；合法实验P成功后在dummy/regmap/IRQ及MFD注册前返回。Q旧GPIO ASIS、暖检测、冷迁址及失败回收保持。完整P供电将另行收敛，不能把七路统一配置为相机2.8V：OEM源码已有L7P给指纹3.3V的事实。
