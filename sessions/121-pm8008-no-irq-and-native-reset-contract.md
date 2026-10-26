# 阶段121：PM8008无IRQ支持与本机复位契约

2026-10-12。阶段121完成PM8008无IRQ regulator-only驱动和配套绑定、实际C probe 18场景、schema 2正例/7反例、完整#121 Image/770模块/DTB及匹配模块包，均离线未部署。原厂双PMIC复位/地址恢复及0x950 chip-enable已核对，四组输入和冷启动地址仍待证实，未建立假供电节点。手机仍#118/taint0/原Phosh/Phoc PID/DPU2/GPU1，完整系统goal active。

## 已完成的驱动基础

E盘20GiB隔离ext4卷同进程ensure，复制完整camera120到camera121，initramfs路径改为候选自己的目录。120 Image SHA 0ec2560bdb332ead8a0bea7636f4fd3d80e041f7ac370f71d20e1f80df183bf9保持。没有向C增加大源码树。PM8008 MFD/regulator原来已配置=m，本轮不是新打开它们。

[9月8日最小MFD补丁](https://lkml.iu.edu/hypermail/linux/kernel/2609.1/01450.html)下载保存原HTML、提取diff并SHA固定，2777字节bf4bca515e4cf45a51b67c80a5a1ca890133e2a9fd331859be2c926a35521b7d；git apply --check干净后仅在121应用。无IRQ跳过domain/IRQ chip，仅注册pm8008-regulator；有IRQ保持稳压器、温度告警、GPIO三cell及domain。检索发现作者当天[撤回系列，因重复更完整的工作](https://lkml.iu.edu/hypermail/linux/kernel/2609.1/01771.html)，因此这里只是项目本地适配，不称上游合入或沿用其他机型测试结论。[9月18日独立PM8010系列](https://lkml.iu.edu/2609.2/08686.html)仍包括缺IRQ处理，未引入PM8010身份/电压表，Realme仍PM8008契约。

[optional IRQ绑定参考](https://lkml.iu.edu/2609.2/08693.html)只移除IRQ三项required，GPIO/thermal仍必需，与只发布稳压器不匹配。本地绑定进一步把GPIO/thermal移出全局required，增加IRQ cells/controller相互依赖、GPIO各属性配套、GPIO/thermal须有IRQ。五组input supplies全部仍强制必需，缺输入必须失败。公有pm8008-no-irq-7.3.patch SHA 4c8e00b7c5ab2f2a68cb6509085f1dbdaaf59e238e47b736fb51aadeae71a546。不添加实际PMIC board nodes，不用synthetic supply修硬件DT。

下载器初次错误认为归档正文是pre，实际MHonArc正文是br并保留原换行；断言失败后改为提取X-Body-of-Message并HTML实体解码，不额外加换行，hunk数量校验/git apply通过。

## 自动校验与产物

直接提取120/121实际C cell数组、release callback及probe，没有重写被测逻辑。硬件API以受约束stub替换，只在主机运行，gcc Wall/Wextra/Werror及address/undefined sanitizers。原probe irq0故障确实复现；候选18场景覆盖irq0/IRQ460成功及dummy/secondary regmap/attach/primary regmap/reset GPIO/name/fwnode/action/irqchip/MFD注册失败返回，成功cell/domain集合、secondary先attach、default最后attach、地址+1及错误action cleanup检查通过。测试只证明控制流程，不是芯片电气验收。

固定dt-schema2026.9复用120 E盘venv，dt-doc-validate、dt-mk-schema无诊断。离线synthetic DTS两正例（regulator-only、完整IRQ）无诊断；七反例（缺input、孤立IRQ cells/controller、无IRQ GPIO、无IRQ thermal、孤立GPIO cells、不支持fallback）均有目标PMIC诊断。反例首次全换compatible导致schema selector跳过，空输出触发断言；改为保留合法selector再添错误fallback。原未被检查fixture私有保留，不将其空输出认作通过。所有诊断exit0，所以判断实际诊断内容。并非全板级schema或真机PMIC验证。

完整Image/modules/DTB build通过，#121 banner，770 ko。Image 46a49619786e11cbb230da8a4aea204c5ee0ab3d743c4c9846c297e9ecb2c0c8，DTB 31a9f7f0e49d22b5ea5173a5f4916c176ecd7f9e610fef5649a702c1c08e4548仍与120相同。CCI、CAMSS、IPA TX修正、118 DPU final read保持；PM8008 regulator电压驱动逐字节保持，未改电压步进/范围。匹配module包7065464字节SHA a0d778b79be5f453fb65d0d906e6d23b45197415346be0a56f16920e21971484，System.map depmod -e无诊断，770 module依赖引用全在包内，无symlink；Image/DTB copy hash吻合。没有把121模块装入118，release文本一致不能替代全套配置/模块匹配。

## 本机复位、地址与输入缺口

检查实际own AndroidR drivers/regulator/qcom_pm8008-regulator.c（文件名underscore），19781 sm8150-mtp.dtsi与先前已SHA验证stock overlay0。PM8150L GPIO1/4 pinctrl均output-high、normal、push-pull、power-source0；native恢复先两GPIO物理0，延迟10ms，第二芯片GPIO4物理1，再对g_reset_regmap的0x0644写1、读回，最后第一芯片GPIO1物理1。因此deassert高有源依据；当前mainline GPIOD_OUT_LOW用逻辑0解除复位，若加入reset-gpios须GPIO_ACTIVE_LOW，不能机械复制原stock flags0。尚未建立该node，也未写GPIO。

此函数是恢复路径，不能断言每次冷启动都执行。全局g_reset_regmap来自首个符合19781/19696条件的chip probe，顺序是否总为预期、0x0644字段定义、cold boot默认地址/strap/loader状态未证明。原厂地址8/9、4/5与mainline primary+1仅构成资源契约，不能直接认为两个独立probe安全。当前i2c4共享双功放，禁止整总线reset/i2cdetect或盲写重映射。

原厂chip-enable定义MISC_BASE0x900+0x50=**0x950 bit0**，供每LDO pm8008_en-supply引用，当前主线MFD/regulator没有管理这一全芯片enable。记录器一度假设字面0x944，断言停止，随后按实际宏计算更正；不存在向手机写该地址的动作。仍须确认冷启动chip-enable状态和主线正确管理方式，不能照抄vendor recovery连双功放reset的流程。

两个vdd_l1_l2→S8C=PM8150L S8 1.352V有源DTS和compiled DTBO交叉证据。vdd_l3_l4/l5/l6/l7均未证明输入来源；源DTS未声明parent时vendor可无parent，但这不证明VBAT/BOB/任意固定供电。当前主线dropout约束和每路可达电压也需结合真实输入。按用户要求留档长难项，下一轮先完成匹配121软件rootfs/启动产物，再推进CAMSS设备树/C-PHY/DMA/ICC/QoS；供电来源与冷启动地址继续有界寻找本机compiled base/loader/硬件资料，暂不启用实际sensor。

## 当前运行与继续约束

本轮手机仅SSH只读：same boot guard118、taint0、Phosh3492/Phoc3190原PID、DPU2/GPU1、PCM closed、双功放powered0 muted1、SLPI offline vdd/vddio0、NV6/source4/vendor1共11 checksum保持。无桌面重启/负载/boot/logdump/userdata/GPT/persist/NV写入。GPU1真实失败仍开放，不能由taint0认定稳定。

121源码在/home/cy122/pmos-samurai-kernel118/camera121，private kernel121/Image-k121-private、DTB及modules-k121-private.tar.gz；每次WSL读E源码同进程ensure118卷。prepare/port/package为一次性脚本，勿重跑覆盖候选。当前手机boot guard仍private119。下一部署依旧当前boot GUI/fbcon/audio/radio完整排空、成功sync/fsfreeze、前置WSL debugfs/usbmon及单次F1回执，不能套旧115守卫。

软件rootfs115 fixed936包/764模块已验但未全量刷，是118兼容基线；**121完整rootfs尚未生成**。完整系统尚未可用，goal保持active；不要求人工画面/触摸/听音检查，不发送呼叫/消息，不push公开仓库，私有原始数据不公开。

本轮结束已sync并卸载E盘新建ext4构建卷，只读e2fsck -f -n返回0；没有检查/修复原WSL VHD。C剩余约2.00GiB，不向C增加大源码/对象/镜像。公开717文件审计无private值，15组硬件保留；3 shell/11 Python语法通过。下一次源码操作同进程ensure118卷。
