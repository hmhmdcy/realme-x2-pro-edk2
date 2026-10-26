# 阶段117：解析边界与同启动恢复桌面

2026-10-12。完整系统goal active；继续无人值守，无人工画面/触摸/听音要求。

阶段117在同一次#115启动中恢复DRM、Phosh/Phoc与FD640 GLES2：只对已失败/无owner的本机面板做一次有界重新探测，然后重触发现有greetd initial_session；没有重启、刷分区或改登录配置。taint0，45秒窗口无新增DPU/GPU故障，累计仍有1次DPU超时；PCM closed/双功放静音、SLPI offline/供电0、trace off、NV6/source4/vendor/persist保持。启动RCU/CTL reset回归与GMU重复探测EBUSY仍开放，不认定永久显示修复。

## 摄像头二进制解析：有界失败后转项

在阶段116本机五sensor.so/六sensormodule BIN来源基础上，网络找到[BANG QTI结构解析器](https://github.com/armijnhemel/binaryanalysis-ng/tree/master/src/bang/parsers/misc/qti_chromatix)及[CamxChi](https://github.com/bjzhou/CamxChi)的公开工具/XSD。GitHub API遇403 rate limit，改用公开浅克隆/固定commit/raw文件，没有使用账户凭据。BANG固定96370e4f07fa0173f32c049b9523d03c98f748d2，只校验header，不声称能解完整寄存器。CamxChi固定9f17f1b568626b393e785b369c5dc94543774d7a，ParameterParser ELF未strip并包含BinaryFileFormat符号、x命令可用-b从BIN生成XML，输入需要创建BIN时的XSD。

工具V2.0.0依赖libxml2.so.2，当前主机仅libxml2.so.16。使用[GNOME官方2.9.14源码](https://download.gnome.org/sources/libxml2/2.9/)，下载hash核验，非root构建到/home/cy122/x2pro-linux/parser-k117/runtime，通过私有LD_LIBRARY_PATH启动工具；没有全局安装或替换系统库。源码/schema/tool及log均保持私有。现有BIN标记Parameter Parser V1.3.2，工具是否能完整兼容尚未验证。

第一轮30秒未生成XML。8秒strace显示读取sensorDriverData时持续分配，且扁平XSD路径造成flashdriver ../sensor include失败；修正为原api/sensor布局后include已全部解析，仍在sensorDriverData处达到8秒CPU限制，0个XML。配置256MiB地址空间、8秒CPU、32MiB输出上限，并终止/等待独立进程组；没有遗留parser进程。没有对未完成输出做roundtrip或声称已获得寄存器/供电序列。

本机只读探查libcamxgenerated*.so无匹配；保留camx库metadata，卸载vendor，没有盲目复制其它大库。对应生成代码可能静态链接到HAL，但尚未证实；后续可以读取实际HAL ELF符号或寻找同版本schema。当前这条解析路线先记录转项，不能向传感器写猜测字段。只读SoC CAMSS/CCI参考0056/0057已固定同Hotdog commit，外国板级补丁未应用。

## 同一次启动恢复DRM和桌面

阶段115第三启动因启动CTL_SW_RESET超时(-22)无/dev/dri。当前boot身份、#115/taint0、无Phosh/Phoc、无DRM、未绑定面板、OF_COMPATIBLE=samsung,sofef03f-m及bind路径核验后，执行一次20秒有界panel-samsung-sofef03f bind。返回0，card0/renderD128、面板driver和GMU firmware加载恢复，DRM初始化通过。没有reset/重启/刷机，也没有绕过IOMMU前quiescence guard。

greetd restart先只到Phrog登录界面/Phoc；既有initial_session之前失败后/run/greetd.run标记保留。读取实际/etc/greetd/samurai-phosh.toml，确认现有cy122 initial_session和wrapper；停止greeter、确认Phoc退出、备份空marker/原配置，只删除该runtime marker，启动greetd。原initial_session正常启动Phosh/Phoc，配置hash前后一致，不新建登录策略或改密码。Phoc最新log为Mesa/freedreno/FD640。

恢复时有一次enc35 frame done timeout；之后45秒观察窗口无新增DPU超时/无GPU fault、taint0。累计仍1次DPU超时，不能认定稳定性修复。重复component bind还记录GMU资源0x0b290000 EBUSY，虽继续加载firmware/硬件GLES2，仍需审查失败bind的资源生命周期，不安装无条件自动循环reprobe服务。

全成员hash校验通过：panel归档26726dceabd52a488de3a16a99655040f0f46f282ca34dc9a5743c175691d4f1；session归档36d554669258dab792859f8e21e228d97cb252d0e30ba2f0b25abc61bb4c3590；最终45秒健康归档e70624486b789264a218e4d3cf215e2fca949a8f74f339255a09bcee5b3f7fa7。三份身份一致，boot/logdump/persist hash保持，NV6/source4通过，PCM closed/双功放powered0 muted1，SLPI offline/sensor-power0、display/radio trace0，Wi-Fi up、zram、ModemManager sim-missing保持。最后额外vendor原hash复核通过，桌面进程仍存在。

## 显示源码新证据和下一步

当前dpu_hw_ctl_poll_reset_status每轮先读SW_RESET，再usleep_range(20,50)，然后检查2,000us期限；期限到期后返回睡眠前读到的status，没有最后一次读取。如果线程实际睡眠跨过期限，而硬件期间已完成reset，就可能误报超时。重新探测时没有再出现boot CTL清空日志且初始化通过，说明到那时继承状态已清空；这支持有延迟完成的方向，但不证明睡眠前旧值是所有回归根因。

准备下一隔离候选只修正poll结束后读取真实reset bit，仍在bit1未清时返回错误，保留全部IOMMU前quiescence/stalled-mask检查。不能增加无条件成功或删除warning。候选需完整build、115基线/DTB/模块ABI核验，再用当前已恢复第三启动的新排空/freeze/F1守卫部署；当前rootfs115 fixed与kernel116未部署CAMSS候选保持。

15组状态、GNSS真实fix、完整传感器、摄像头、指纹、蜂窝数据/通话、充电、休眠和長稳继续开放。rootfs115软件镜像已校验，未全量刷入。所有身份/固件/BIN/原始日志保持私有，未发送消息/呼叫，无GPT/NV/persist写入，无erase、无文档push。
