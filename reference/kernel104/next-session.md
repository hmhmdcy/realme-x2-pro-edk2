> 当前后续见[阶段105](../../sessions/105-apr-rebind-and-first-modem-crash-smem-diagnostics.md)与[最新交接](../kernel105/next-session.md)。下文保留104历史，APR登记已由105修复，首轮MPSS失败仍保留。

# 下一阶段：优先首次MPSS可靠性，修APR登记并继续音频验收

当前真实Linux #103/逻辑阶段104，详见[session104](../../sessions/104-native-digital-microphones-and-first-boot-radio-failure.md)和[15组状态](../../linux-port/docs/HARDWARE-STATUS.md)。全硬件goal active，无token预算，尚未完成。

手机已部署Linux #103（阶段104），原生声卡/WCD934x/正确双MAX98937继续绑定，2秒-48.16dBFS有限播放返回0；功放start1/stop1、空闲global00/amp80/failed0，实际声音仍无人确认。
数字麦克风已补齐原生DMIC Pin、偏置1/3和MCLK路由。DMIC0/1/2分别5.04秒/241920帧，非零样本229767/229686/222432，SLIM启动停止均ret0，期间电源/主时钟On、结束Off；去掉前0.5秒后无满幅样本。采样通路通过，实际拾音/质量和启动瞬态仍待验。
APR三个查询包头已初始化，新增真实回复日志；首次GET_FWK/legacy都收到basic status22，未取得版本，22不是本机头文件的ENOTREADY(10)/EUNSUPPORTED(3)，含义未确认。一次正常core重绑后无回复：源代码证实APR remove删除服务IDR，而probe不重新登记，这次重试不能证明DSP持续拒绝；不再重复重绑。
首次MPSS44.773303秒up、84.759034秒fatal，39.985731秒后失败，自动worker1；先保存失败，随后一次有界恢复。恢复后5GHz认证/DHCP/DNS/HTTP和网关3/3通过，但首轮启动可靠性、2.4GHz reason7/删除等待/冷启动/休眠仍未修复。蓝牙保持停止，不配对连接；振动starts0/standby，机械确认暂缓。
174文件检查点/九个原包/nested SHA/80块新备份/完整boot与logdump读回/真实运行FDT/NV/persist及stock DTBO保留通过；原CPIO/模块/无线/显示源码不变，DTB真实重建EDK2。检查点uptime406.05，双DSP running、taint0，首轮MPSS fatal1/ADSP fatal0，显示超时3、BT phase2错误1。
下一轮优先首次MPSS可靠性，并修APR服务登记/版本错误处理，随后继续15组硬件与音频质量验收。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，私密固件/日志/凭据/音频/二进制留本机，不提交推送；全硬件goal active。

下一轮kernel105/全新PID与输出prefix，先核对实机boot ID、实际源码/镜像/进程/owner，不重放已有guard目录。私人kernel104/runtime-boot-id-after-private.txt是真实当前boot ID；checkpoint.tar SHA `c33ee2cace7ad42c5921f619b87ca4498174f92e5cb3912eb2123e53e6e0aa5b`，tests-validation/checkpoint-validation.json绑定九个原包及174文件。

优先首次MPSS40秒fatal，自动boot-finished1与first-boot-failure完整保留，一次恢复后当前5GHz通过；首次up44.773303/fatal84.759034，恢复up313.3625，检查点uptime406.05。采集SMEM reason返回值/长度及请求链证据，不能无界恢复或只延长固定delay。NV RAM COW、原NV/persist不写；当前服务tftp/rmtfs自有PID守卫，不能重复启动它们。

APR查询当前不能可信恢复：初始FWK/legacy各basic status22，22含义未确认，与ENOTREADY10/EUNSUPPORTED3不同；一次core解绑重绑从svcs_idr删服务但probe不回填，随后没有reply。因此不能用这次重绑作为有效重试，更不能再反复重绑。先修drivers/soc/qcom/apr.c正常driver生命周期登记（严格同svc指针/ID、加锁与失败回收），再记录真实opcode/header/domain/service/status、修缓存仅合法版本成功与超时/未知basic错误传播。当前AFE/ASM/ADM仍绑定，未重启ADSP；不要强制DSP crash。旧#101真实API7/ASM2只保留历史。

数字DMIC0/1/2板级bias/MCLK已补，三个5.04秒非零采样通过、SLIM启停ret0、结束Off；最初0.5秒存在满幅瞬态，后段0满幅，实际已知声源/人声质量待验。当前Handset Mic已是DMIC0，不再按AMIC1采。路由DMIC0/DEC5/TX5、DMIC1/DEC7/TX7、DMIC2/DEC5/TX5，开各自Handset/Secondary/Speaker Mic Switch；960帧×4 period，capture card0/device1。私人四个tinyalsa v2.0.0静态工具kernel104，tinymix -D 0 contents/set/get；物理扬声器声音仍未确认，2秒-48.16dBFS有限播放各功放start1stop1/global00/amp80。

实际内核/home/cy122/x2pro-linux/linux HEAD e42788e，EDK2/home/cy122/edk2-samurai/repo HEAD f23a9f8。当前DTS对应reference/kernel104/sm8150-samurai.dts.after，native q6core/WCD sources对应q6core.c.after/wcd934x.c.after；正确MAX98937和samurai machine源保持kernel103版本。linux-port/dts早期镜像故意不覆盖。当前CPIO `71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7`、Image `443be2516c8a0aa150c6aea1e24d5ce4796e81beb31db7c2796629c1592c681a`、DTB `2a9e3cac62e7f6b8eb767230b630ddbeee546535acf9eec225bf3591dd623cbb`、boot `7a6b670cc8636ea04f8ff30e2d17ef21bbdec2686de2a248453f9b7353349ecd`；配置/模块不变。

MPSS用/usr/sbin/samurai-modem-remoteproc，ADSP真实固件qcom/sm8150/realme/samurai/adsp.mdt、完整OF remoteproc@17300000；不能凭remoteproc编号。amps1-0039/1-003a，motor2-005a，touch4-0020；haptics helper唯一driver/89c000完整OF。GPIO148/37归功放驱动，空闲物理高解除复位但global00；不重跑旧I2C/GPIO ID工具。WCD143/QUP4 GPIO51/52/QUAT137–139/触屏54保持，SID1b21 strict0/NGD1b46 strict0，不旁路SMMU。

固定原厂9668fcdc/19781拓扑与同机private mixer XML互证；已知DMIC0/1 BIAS1、DMIC2 BIAS3，未移植全部其它DMIC。OEMAPR/GPL q6core参考在私人kernel104/oem-*.c/h/dtsi，公共来源链接见session。首次failed guard/格式警告/错误路径均保留，不能据host报错误判新boot ID/熵或整机panic。

下次完整boot/logdump新备份、实际EDK2 DTB重建、F1后独立fastboot/分区大小/源SHA审计，只刷boot/logdump。保留Android/data/userdata/GPT/NV/persist/SSH/显示85–88/rootfs01所有文件和F2FS段落。充电收尾，不重跑OEM充电/NV/OTP/unseal/FET/OTG/MCU/I2C_FORCE探针。蓝牙停止、不配对连接；振动机械确认暂缓、不重放脉冲；NFC无标签只控制器。固件/原日志/配置/身份/凭据/音频/镜像/二进制私人、不提交推送。摄像头/传感器/指纹/蜂窝/GNSS及所有15组功能仍需推进。
