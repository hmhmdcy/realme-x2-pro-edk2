# 阶段104：数字麦克风恢复采样，首次无线崩溃仍待修

2026-10-11，真实Linux #103已刷boot/logdump；全硬件目标继续，未完成。用户蓝牙不配对连接、振动机械确认暂缓、NFC只验证控制器。

手机已部署Linux #103（阶段104），原生声卡/WCD934x/正确双MAX98937继续绑定，2秒-48.16dBFS有限播放返回0；功放start1/stop1、空闲global00/amp80/failed0，实际声音仍无人确认。
数字麦克风已补齐原生DMIC Pin、偏置1/3和MCLK路由。DMIC0/1/2分别5.04秒/241920帧，非零样本229767/229686/222432，SLIM启动停止均ret0，期间电源/主时钟On、结束Off；去掉前0.5秒后无满幅样本。采样通路通过，实际拾音/质量和启动瞬态仍待验。
APR三个查询包头已初始化，新增真实回复日志；首次GET_FWK/legacy都收到basic status22，未取得版本，22不是本机头文件的ENOTREADY(10)/EUNSUPPORTED(3)，含义未确认。一次正常core重绑后无回复：源代码证实APR remove删除服务IDR，而probe不重新登记，这次重试不能证明DSP持续拒绝；不再重复重绑。
首次MPSS44.773303秒up、84.759034秒fatal，39.985731秒后失败，自动worker1；先保存失败，随后一次有界恢复。恢复后5GHz认证/DHCP/DNS/HTTP和网关3/3通过，但首轮启动可靠性、2.4GHz reason7/删除等待/冷启动/休眠仍未修复。蓝牙保持停止，不配对连接；振动starts0/standby，机械确认暂缓。
174文件检查点/九个原包/nested SHA/80块新备份/完整boot与logdump读回/真实运行FDT/NV/persist及stock DTBO保留通过；原CPIO/模块/无线/显示源码不变，DTB真实重建EDK2。检查点uptime406.05，双DSP running、taint0，首轮MPSS fatal1/ADSP fatal0，显示超时3、BT phase2错误1。
下一轮优先首次MPSS可靠性，并修APR服务登记/版本错误处理，随后继续15组硬件与音频质量验收。保留Android/data/GPT/NV/persist/SSH/rootfs01/F2FS/旧显示，私密固件/日志/凭据/音频/二进制留本机，不提交推送；全硬件goal active。

## 修改与来源

同机原厂[19781音频拓扑](https://raw.githubusercontent.com/realme-kernel-opensource/realmeX2Pro-kernel-source/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/arch/arm64/boot/dts/19781/sm8150-oppo-audio-overlay.dtsi)与只读本机mixer_paths私有归档互证：handset走DMIC0/DEC5/TX5，第二路DMIC1/DEC7/TX7，speaker-mic中DMIC2用偏置3。原生WCD934x把输入Pin与DMIC ADC分开，必须补DMIC Pin至麦克风widget、DMIC至偏置供电及MCLK；电压/时钟保持原厂1.8V/9.6MHz。只新增三路已核对的输入，不移植原厂整个拓扑。

三个q6core栈上APR包完整初始化，原apr_send_pkt仅填domain/service，不能留下任意port/token。增加本机有限速率的opcode/payload长度/port/token/basic status与合法版本条目计数日志。WCD SLIM trigger传播prepare/enable/disable/unprepare错误，enable失败时正常回收准备状态。没有新增绕过SMMU、直接I2C或GPIO探针，也未修改功放增益。

初始版本查询在18.512秒发送20字节、port0/token0，FWK与legacy都有8字节basic回复、status22，均无合法版本条目。22在同机GPL头文件中是ADSP_ERR_MAX边界，不等于ENOTREADY=10或EUNSUPPORTED=3，当前固件含义未知。254.218638秒唯一core重绑后只有send、没有reply；静态核对drivers/soc/qcom/apr.c发现apr_device_remove从svcs_idr删除服务，而apr_device_probe不回填。这个重试本身破坏回复路由，不能将其当作“缓存不是原因”或“DSP持续拒绝”的证据。AFE/ASM/ADM仍登记，播放录音通过；ADSP未重启。下一轮必须先修登记生命周期，再修缓存/超时/basic错误语义，不能反复重绑。

## 实机验收

| 路径 | 帧/时长 | 非零样本 | 去掉首0.5秒后的范围/RMS | 电源/传输 |
|---|---|---|---|---|
| DMIC0/DEC5/TX5 | 241920/5.04秒 | 229767 | -45至38 / 8.783648 | MIC BIAS1/MCLK On；SLIM启停0；结束Off |
| DMIC1/DEC7/TX7 | 241920/5.04秒 | 229686 | -37至39 / 8.662093 | MIC BIAS1/MCLK On；SLIM启停0；结束Off |
| DMIC2/DEC5/TX5 | 241920/5.04秒 | 222432 | -24至22 / 4.937010 | MIC BIAS3/MCLK On；SLIM启停0；结束Off |

均48kHz/mono/S16、960帧×4 period，DMA live RUNNING，exit0/空stderr；每路只有对应DMIC开启，结束PCM closed。最初0.5秒内有满幅瞬态，后段满幅0；尚无已知声源响应/人声质量/物理声音确认，不能宣称完整音频验收。录音原件仅私有目录，不公开播放。

2秒双通道低幅自生成测试音重测通过；双功放start1/stop1，global00/amp80/failed0，未做DSM、校准、持续大音量或耳机测试。

首次MPSS up44.773303、fatal84.759034（差39.985731秒），自动无线worker1；九包保留首次runtime、first-boot-failure与原无线/蓝牙/QRTR/只读服务日志。仅一次手动stop/start MPSS，原tftp/rmtfs服务PID及命令行验证、NV RAM COW保持；ADSP唯一完整OF与真实firmware路径核对。原boot-finished=1不改。恢复后5GHz5180认证/DHCP/网关3发3收/DNS/577字节HTTP通过，蓝牙未启动。

## 构建、部署与完整性

配置不变，W=1两处C目标无警告，DT仅原来两个addr-size警告；只改samurai DTS、q6core、WCD934x，其它tracked/untracked源和initramfs文件/模块保持。Image `443be2516c8a0aa150c6aea1e24d5ce4796e81beb31db7c2796629c1592c681a`，DTB `2a9e3cac62e7f6b8eb767230b630ddbeee546535acf9eec225bf3591dd623cbb`，CPIO `71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7`。真实EDK2 DTB FFS/container变化，其他可执行字节/shim/compat/ramdisk/EUD/F1来源不变。

新80×2MiB备份全SHA通过，原boot full `0de0d9d1dc7069f6d28ec68c62e6e2d83f1c029febcf86ca1105936df738f577`、logdump `244130230b6aa495aa82b8110071594d72dbce67bd002ad271cee4aa38ce0050`。仅两分区flash，boot 6684672字节 `7a6b670cc8636ea04f8ff30e2d17ef21bbdec2686de2a248453f9b7353349ecd`，logdump `717eb4341bcc2a89c3687dc880b3b72c2f50cbe949a5e07dd999776c0716c675`；完整读回、运行FDT仅合法UEFI chosen差异、六NV/persist/stock DTBO及部署服务/模块哈希通过。

检查点九个原包逐字节及嵌套manifest绑定，共174个文件，SHA `c33ee2cace7ad42c5921f619b87ca4498174f92e5cb3912eb2123e53e6e0aa5b`，uptime406.05、恢复MPSS持续92.6875秒。所有原日志/固件/OEM XML/录音/身份/凭据/镜像在私人kernel104；公共目录仅自写/修改GPL代码、脚本与脱敏记录。usbipd保持Running，EUD detached，自有宿主helpers为0。

## 保留的失败与下一步

首编译日志的payload长度格式警告与镜像全部保留first-format后修复；split工具旧#101 guard在创建分块前阻止运行，改#102后新分块；恢复工具首次ADSP firmware路径guard拒绝、未创建恢复目录，核对实际qcom/sm8150/realme/samurai/adsp.mdt后才唯一恢复。F1 receipt后设备消失EIO是重启边界，已finally释放USB；未知hrdevmon提示保留，没有force-bind。所有guard/错误原件私人保存，不替换成成功记录。

优先获取首次MPSS40秒崩溃的有限SMEM/QRTR/rmtfs请求链证据，不盲增delay或循环DSP恢复；5GHz只有一次恢复后的有限联网通过。2.4GHz reason7、删除等待、冷启动/休眠、显示超时、BT传输、USB稳定性继续。音频采样已前进，但已知声源/首次瞬态、耳机插拔、版本服务登记仍需修验。摄像头、SLPI传感器、指纹、蜂窝、GNSS等仍在15组目标内。
