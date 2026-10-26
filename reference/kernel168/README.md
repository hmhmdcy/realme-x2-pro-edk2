# 168：SLIMbus服务生命周期与原生音频恢复

2026-10-14，继166拒收与167回退复现后，只改NGD、messaging及WCD934x三个源文件。最终候选以163为基线，保留显示、DTB、配置、boot164、现用modules/software132和Mesa149。

NGD将客户端通知移到控制器注册完成之后；DOWN先断开QMI、排空master worker，再删除客户端，在SSR锁内完成DMA释放，并用tx_lock等待现有发送退出。登记状态避免重复register/unregister；QMI连接与服务器completion保持就绪直到断开。PM唤醒与DMA初始化错误向上传递，messaging在PM get失败时平衡引用并退出；休眠失败保留DMA和状态，释放通道后回收coherent队列。WCD在总线DOWN时延迟探测，初始化/efuse/版本读取失败时返回错误，版本读取成功后才分配Class-H状态。[合并补丁](audio-lifecycle.patch)、[源码收据](source-validation.json)

宿主抽取实际驱动函数，13项PM、12项codec及14项事务检查通过；另做100轮DMA释放与100轮UP/DOWN。旧驱动休眠失败破坏DMA和重复UP重新注册均有负对照。硬件原语为桩，不等于真实调度并发或物理DMA验证。[宿主检查](host-tests-validation.json)

三个音频对象W=1和463行checkpatch均0警告；完整构建保留未改动EUD源码的1条unused-function警告。770个模块仅两处build-id差异，代码/数据/重定位/符号/modinfo均一致，沿用modules132。FAT Image/DTB精确读回，实际logdump168和boot164分区哈希匹配，回退163原字节保留。[构建与包](build-package-validation.json)

首次真实kernel168启动声卡恢复、WCD版本0x411、桌面存在，taint0，DMA prepare/TX timeout/queue full/resume failure/WARN/GPU及显示超时均0。[首启](runtime-validation.json)

三次2秒原生低幅立体声播放，PCM运行及双功放开启/关闭均观察到。DMIC0/DEC5、DMIC1/DEC7、DMIC2/DEC5分别3秒/144000帧，后2.5秒有非零样本、满幅削波0；桌面PulseAudio播放返回0，mixer恢复、PCM关闭、双功放关闭静音、全boot故障计数0。初次桌面测试因root私人目录权限失败，保存原错误，改用标准输入传递自生成测试音后补验；不重跑已通过的原生采样。[音频结果](audio-validation.json)

169保持相同镜像做另一次独立启动及音频复测。实际听音、已知声源拾音质量、耳机插拔、冷启动/休眠和长稳仍未验收；用户本轮明确暂不方便现场配合，先完成软件验证。有限采样与PCM返回0不能代替这些项目。
