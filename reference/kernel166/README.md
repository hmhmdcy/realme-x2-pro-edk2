# 166：音频 PM/DMA 错误回收候选，实机拒收

2026-10-14。核对当前kernel163及164旧失败档案，首次失败明确为NGD DOWN、QMI handle存在、TX channel为空，先出现唤醒失败，再发生917次prepare失败及WCD efuse WARN。旧档案没有休眠拒绝日志，不能将此次故障归因于QMI拒绝休眠。[历史证据](historical-evidence-validation.json)

本轮正常停止旧kernel163的ADSP时，新增70次prepare失败，诊断同样为DOWN/channel0，taint仍0；第一次现场确认了停止路径复现。[停止证据](baseline-shutdown-validation.json)

候选修复PM错误返回、DMA初始化与部分初始化回收、coherent缓冲区释放、休眠失败保留DMA、QMI readiness以及WCD初始化错误处理。39项抽取真实函数的宿主检查与100次DMA回收通过；硬件/PM原语为桩，未证明真实并发。三个音频对象W=1、checkpatch通过。完整构建有一条未改动EUD源码unused-function警告；770模块除两项build-id外字节一致，沿用现用modules132。[补丁](audio-lifecycle.patch)、[宿主验证](host-tests-validation.json)、[构建包](build-package-validation.json)

只刷logdump后，真实kernel166首启失败：声卡缺失，TX timeout1，WCD设备回调Oops及IDA重复释放WARN1，taint640。DMA prepare0不构成通过。候选拒收，日志及镜像留私人目录。[实机失败](runtime-validation.json)

后续167回退原字节kernel163。失败166停机时fbcon blank返回EBUSY，DRM无用户态client而扫描输出仍激活；按该失败boot单独记录后退出，不计作正常关屏通过。下一候选168继续修SLIMbus服务生命周期、master worker设备引用、重复注册和服务器completion。

原始启动日志、身份、镜像与录音均在独立私人输出目录。166补丁保留供审查，不作为已验收修复。
