# 阶段120：CCI设备树及本机摄像头PMIC契约

2026-10-12。上一轮119实际部署正常boot和GPU反例/离线解码是progress；本轮转摄像头资源，继续完整系统goal active，无人工检查。

阶段120完成隔离#120 CCI设备树及完整Image/770模块/DTB构建，绑定/真实DTB定向schema和故意坏DTB反例检查通过，匹配模块包depmod无诊断；未部署。当前手机仍#118，Phosh/Phoc原PID、taint0、DPU2/GPU1、PCM关闭、双功放静音、SLPI供电0，NV6/source4/vendor1保持。摄像头尚无传感器识别/stream，PM8008输入与无IRQ支持是下一实际缺口，goal继续active。

## 隔离候选与CCI移植

118的E盘20GiB私有ext4卷先同进程ensure挂载，复制116完整源码/对象及initramfs到/home/cy122/pmos-samurai-kernel118/camera120，4.2GiB，不向C复制新树。116 Image仍7ad5e8ffc60c2635649977d1100574574853708a4f6bc39090964a456554f275，118 Image仍57a375cac03605f4d91099ca9994e234ef9dcd043564e1adbc66b4df3ccfa2ab。精确应用118最终CTL read修正，CAMSS116源码保持，IPA v4.1 TX delay修正保持，board sm8150-samurai.dts与118逐字节相同。initramfs路径改到候选自己的E目录，CCI=m、CAMSS=m。

[Hotdog固定commit](https://github.com/Sr-0w/hotdog-linux-bringup/tree/47087509c4289c2580c54f5433e55366b2e00445)0057仅借SoC资源，不用外国板级传感器/供电。当前[上游CCI绑定](https://raw.githubusercontent.com/torvalds/linux/master/Documentation/devicetree/bindings/i2c/qcom,i2c-cci.yaml)和[CCI驱动](https://raw.githubusercontent.com/torvalds/linux/master/drivers/i2c/busses/i2c-qcom-cci.c)采用msm8996-cci作为v2回退，旧patch的sdm845-cci回退不符合当前schema；修正，给sm8150新增六时钟格式绑定条目。

两块MMIO ac4a000/ac4b000、各0x1000、SPI IRQ460/271、引脚17/18、19/20、31/32、33/34、cci_i2c、drive2均与本机19781 camera/pinctrl交叉核对。八个active/suspend pin states，四子bus。clock37.5MHz，TITAN_TOP_GDSC，CAMCC本来已有SM8150节点。CCI全部disabled，未加传感器节点；这是待完成物理摄像头功能的控制器基础，不是最终摄像头验收。

本机CCI0/1标准时序共20参数与generic v2完全一致。400kHz两CCI的stretch=1而generic0；1MHz CCI0 stretch1、CCI1 stretch0，不能一律复制参考1MHz默认。四bus暂设100kHz，驱动时序未改，高速模式仍须有根据地解决。本机五active source slot及独立PM8008供电已从去注释源码提取，slot不是已识别sensor；六BIN仍未解析，不能猜sensor slave/chipID/mode寄存器。提取器首版混入sdmmagpie和tlmm嵌套汇总，已限定精确sm8150-pinctrl及cci0..3的active/suspend节点，最后report仅8条。

## 构建、schema和匹配模块包

完整Image/modules/DTB返回0，#120 banner；Image 0ec2560bdb332ead8a0bea7636f4fd3d80e041f7ac370f71d20e1f80df183bf9，DTB 31a9f7f0e49d22b5ea5173a5f4916c176ecd7f9e610fef5649a702c1c08e4548，770个ko。CAMSS ko仍与116逐字节相同。报告kernel-build-validation.json。

Ubuntu没有python3-dtschema包，未把安装失败算通过。按[dt-schema官方用法](https://github.com/devicetree-org/dt-schema)，E卷venv中固定实际PyPI版本2026.9；pip cache/build临时文件也在E，Ubuntu小型venv/libfdt/swig依赖约6.4MiB。dt-doc-validate、dt-mk-schema、dt-validate -l qcom,i2c-cci三步无诊断；只代表CCI绑定与两CCI节点，不声称整个板级DT全部schema通过。

libfdt实际核对两个disabled CCI、IRQ/地址范围、4x100kHz/no sensor child。两份故意坏的临时DTB，分别错回退和错clock-names，validator均输出指向CCI的诊断，**也返回0**；因此验收依据无诊断及结构检查，不能只看exit0。临时反例均私有，从未上机。

764个旧module以strip-debug/remove-build-id比较，只有atmel_mxt_ts变化；新6个为videobuf2-common/dma-sg/memops/v4l2、ir-kbd-i2c和qcom-camss，CCI本来已在118模块集里。没有旧module移除，不声称120对115/118所有模块字节相同。候选module包770个，modules.dep所有引用在包内、System.map depmod -e无诊断、无symlink，7065452字节SHA 69401e2f6f791c8906c13e4e6410af83a8b15a97652345abbd3775a6f6a70648。私有Image/DTB回拷与build相同。**不要直接把120模块装入118**，release文本相同不代表配置/依赖相同。没有生成或验收完整rootfs120。rootfs115 fixed936包/764模块仍是118对应已验候选，未改/未全量刷。

## PM8008供电契约与下一步

本机19781 pm8008.dtsi显示两颗PMIC在QUPv3 SE4/mainline i2c4，地址8/9与4/5，P/Q各7个LDO，reset分别PM8150L GPIO1/4。当前i2c4已有双功放，不能重置整个总线或拿bus编号表象误判；未i2cdetect/上电写寄存器。当前mainline PM8008合并两地址，通过primary+1占secondary，binding需要五组输入电源和IRQ；driver无条件IRQ注册。

重验102只读stock-audio-contract.tar全成员SHA及原厂DTBO hash，已保存的MTP overlay0字节一致，不再次读/写手机分区。原厂两PMIC地址与P/Q14个16位reg偏移吻合，reset局部phandle均解析为pm8150l_gpios 1/4；vdd_l1_l2外部fixup是S8C，19781 sm8150-regulator.dtsi为PM8150L S8/smpc8=1.352V，现有mainline vreg_s8c_1p3也是1.352V。其余L3-L7输入未全证明，不能补假供电。原stock primary nodes没有IRQ，但@8内部pinctrl保留旧SPMI式interrupts(0,c0,0,0)/(0,c1,0,0)，不能把内部IRQ元组当SoC外接IRQ，不能声称全树没有interrupts或物理未连接已证实。源DTS没有这一旧GPIO段，compiled DTBO优先。

stock解析首次按32位reg处理遇到实际/bits16 LDO，安全失败；支持16位后误读/__local_fixups__的reset-offset，再限定实际非/__元数据节点。完整raw DTBO和props继续私有，公开只保存选中的硬件契约及已解析symbol，不保存boot身份/NV/固件。

公开上游近期已有[PM8008无IRQ regulator-only MFD方案](https://lkml.iu.edu/hypermail/linux/kernel/2609.1/01450.html)及[optional IRQ绑定](https://lkml.iu.edu/2609.2/08693.html)。下一轮先下载固定patch/检查适配，确保无IRQ时仅注册regulator，不错误发布GPIO/温度告警；证明其余输入和复位极性后补本机两PMIC disabled nodes，构建/schema，再设计单颗只读身份和安全供电验证。此处尚未应用PM8008 patch或改其config，没有猜IRQ。其后继续CAMSS DT、C-PHY、DMA/ICC/QoS及sensor识别/stream，完整系统仍未可用。

本轮仅主机改源码/构建/解析，未重启手机、未stop/start桌面、无GPU负载、无相机供电/总线事务、无GPT/NV/persist/boot/userdata写入。SSH同boot guard复核118/taint0/Phosh3492/Phoc3190/DPU2/GPU1、PCM closed/功放0 muted1、SLPI offline vdd/vddio0，11个NV/source/vendor checksum保持。私有runtime-health-private.txt，公开runtime-health-validation.json。
