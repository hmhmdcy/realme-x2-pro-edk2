# 275：标准镜头与 libcamera 生命周期部署，定位共享 I/O 依赖

2026-10-18。此页记录 boot275 当时的部署及失败；当前部署已推进到[276](../kernel276/README.md)。完整多摄及骁龙 ISP 目标保持 active。

本阶段增加 Image183 匹配的 LC898219XI 标准 V4L2 模块，并将板级 VAF 唯一消费者移至 lens、建立 sensor `lens-focus`。boot275 SHA `5f023faa698c1c7c84c04c5c40a341e7c212becde97e7d53d49c59944ae13d42`（[构建收据](build-package-validation.json)）；Image183 与其余原模块保持。本阶段实机 776 模块/961 包。

## 用户空间的通用修复

[0026 补丁](0026-simple-lens-stream-lifetime.patch)为 CameraLens 增加幂等 open/close，保留其它 pipeline 的原 init 行为；Simple 枚举后关闭镜头，取流时在 video streamOn 后打开，停止时释放。没有机型、地址或应用条件，也没有实现 AF 算法或距离映射。[逐文件来源](lifecycle-source-validation.json)

libcamera r22/config-r17 通过正常 abuild 构建完整 13 个签名 APK，保留既有 25 个补丁及发行版功能目标。原214工作区2254项和r21缓存2273项复核保持；五IPA签名、AArch64 ELF、工具/Qt/Python等主机QA通过。主机模拟不等于实机相机测试。[构建](r22-package-build-validation.json)、[完整功能](r22-full-feature-configuration-validation.json)、[QA](complete-host-qa-validation.json)

实机一次原生升级七个包，其余954包记录不变；49载荷核验通过，七包精确旧版本降级模拟通过。实际回退往返未执行。[安装](packages-install-validation.json)

## 保留的实机失败与定位

boot275 四摄能枚举，但独立打开镜头遇 CCI master0 queue0 超时，libcamera 报 lens disabled。**四摄枚举不是镜头接入通过的证据。** 当时共享 1.8V I/O rail 空闲关闭。

- 通过标准 runtime PM 暂时保持 IMX319 上电后，主摄仍 suspended，镜头可标准打开；结束恢复 auto，所有设备回收。[有共享 I/O 时](lens-shared-io-validation.json)
- 只保持 CCI 控制器电源域与时钟、所有 sensor suspended，镜头仍超时；恢复 auto。[仅控制器时](lens-cci-held-validation.json)
- SoC 已有正确 TITAN_TOP_GDSC 描述。结果支持公共 CCI 总线 I/O 电源依赖，不能据此把其它 sensor 常驻上电作为产品修复。

主摄 RAW/RGB 各12帧通过，说明移除 sensor 的 VAF 消费后传感器本体仍工作；当时枚举期间镜头初始化失败，不能把取流通过记为镜头通过。[取流](main-capture-validation.json)

默认 SSC/SensorProxy/greetd 此次正常启动，没有使用 nodeps 恢复；boot273 EPERM 的根因未证明修复，物理旋转未重测。[启动硬件](postboot-hardware-validation.json)、[服务](services-validation.json)

## 回退与方法限制

手机及 PC 双份回退 26120859 字节，SHA `7fadb874f21e3f73c877c804af962005aa339ffe53e969f0728c0c2e1b81eadb`，含实际 boot273、七个旧签名 r21/r16 包和依赖/配置备份；未实际往返。[回退核验](rollback-validation.json)

准备脚本第一次替换缓存路径断言失败发生在构建之前，改用明确占位符后完成一次实际构建；离线输出目录已存在的准备失败保留并处理。私人原件、软件包及设备身份存放在 `E:/edk2-samurai-out/kernel275`，不进入公开文档镜像。镜头供电问题的实际修复与生命周期验收见276。
