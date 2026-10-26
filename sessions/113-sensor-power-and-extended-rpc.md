# 阶段113：本机传感器供电与扩展FastRPC

2026-10-12最新状态：本轮已按用户要求更新文档并收尾。手机仍运行Linux #113和已有userdata F2FS/Phosh；boot15累计9次DPU帧完成超时、1次GPU故障，内核taint512。显示花屏的永久修复尚未完成，完整postmarketOS rootfs新镜像尚未交付。用户此前确认会话恢复后画面稳定，这条确认不涵盖后续时序/缓冲试验。

当前Phosh/Phoc进程及greetd运行，F2FS根为rw；原Phosh启动脚本和00121 SLPI选择已恢复，idle-delay恢复60秒，SLPI offline、传感器VDD/VDDIO引用均0、双PCM closed、双功放供电0/静音1，NV6/source4哈希保持。五个诊断trace实例和事件全部关闭，原显示快照哈希保持。fbcon仍为运行时bind=0；taint512及该运行时设置留给下一次有守卫的正常重启处理，本轮未再重启或刷机。详见[最终收尾核验](../reference/kernel113/wrap-up15-validation.json)和[继续检查点](../NEXT-SESSION.md)。

后续只做自动化调试和互联网/源码仓库/本机反汇编取证，人工画面、触摸、遮挡、转动及听音检查暂缓。长时间没有可验证进展的问题保存证据后转向下一项。下面的早期记录保留各自启动和试验范围；最新boot15结果在文末，旧bootID/taint0脚本不能直接重放。

阶段113最初部署Linux #113及匹配的boot内嵌DTB时，只写boot/logdump。已有userdata F2FS、Phosh和用户文件保留；用户确认首次供电试验后画面稳定，能解锁并打开应用。完整硬件适配目标尚未完成。

供电依据来自[Realme官方本机Android R内核](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source)，commit `23172a1571bd91156032cc9fef16284a82b63d2c` 的19781设备树及`drivers/sensors/sensors_ssc.c`。原厂SSC依次开启PM8150L C组L7、延时10ms、开启L8。113添加受SLPI锁保护的手动消费者，默认关闭，只在remoteproc offline时允许切换；关闭/失败回滚保留实际引用状态，禁止运行中断电。AP引用不等同于物理电压测量。

供电顺序实际共享代码的ASan/UBSan失败组合与回滚测试通过，W=1驱动编译通过。内核配置只改initramfs来源路径并增加手动消费者；initramfs字节、FastRPC/PAS/PD mapper/面板驱动保持112。DTB只有新增sensor-power节点和必要phandle，原节点属性保持。EDK2候选只有内嵌DTB模块变化，实际111设备boot的其它模块字节也核对保持；规范109源码/固件产物已恢复。

刷机前私有档案核验GPT18、boot111/logdump112、persist、NV6与来源4。完整回退镜像保存。当前F2FS停止桌面与无线/MPSS、sync、成功freeze后收到F1，再独立fastboot识别及分区大小验证。113 boot/logdump写入成功，首次完整runtime确认新boot、taint0、F2FS rw、live DT原属性及EFI新增属性、供电0引用和SLPI offline。首次HTTPS校时前证书错误原档案保留；NTP正常后新前缀重测通过，不跳过TLS验证。

RAM v5与新boot v6都实际完成供电开启、370字节监听补取与342字节RAM写入，收尾SLPI offline/供电0/taint0，NV6/来源4保持。两次短窗没有112的I2C fatal，但加速度查询254且无样本。v6诊断证明daemon约10.13秒即退出，listener ret1/result14、wire31/sc1f030000；上游main忽略listener错误而返回0，不能据此称DSP健康或供电问题已修复。

[上游扩展方法实现](https://github.com/z3ntu/hexagonrpc/commit/8fd3b22)说明wire31的首DWORD携带实际MID；原守护进程按stat固定缓冲布局处理而拒绝本机的三个输入/零个输出请求。已增加有边界校验的扩展分派和方法33真实RAM rename。rename两边父目录用openat2固定在私有tmpfs内，只接受普通文件，拒绝源/目的符号链接、目录、越界或其它只读树，绝不改原厂分区。实际handler/stat/rename、覆盖、别名、内容读回、非法输入与ASan/UBSan通过。静态hexagonrpcd-v5仅私有暂存，无系统包替换或自动启动；新boot RAM v7有界90秒和第二次采样，最终数据见[聚合核验](../reference/kernel113/checkpoint-validation.json)。

113完整无线清理正常重启已恢复新内核。EFI关机运行时异常仍有记录，不能与重启卡死划等号。历史prefix碰撞被目录存在守卫拒绝，改为跨阶段唯一前缀后继续，不能重放旧启动ID或F1记录。

v7/v8各自新启动实测90.07/150.11秒，真实RAM写入240次、rename204次、完成大输入100次，扩展MID31/33；daemon最终按有界TERM退出143，无I2C fatal，均收尾SLPI offline/供电0/taint0、NV6/来源4保持。v8首次查询延至60秒，第二次加速度和光线/磁力计仍254、无SUID；接近查询0并识别Sensortek STK3331，真实报告1个FAR样本，正常禁用。记录见[接近采样核验](../reference/kernel113/proximity-v8-validation.json)，尚未验证遮挡NEAR/FAR变化。

已核验三次113正常重启及v8后桌面回归；当前phone checkpoint为k113-reboot-radio-clean-3，SLPI offline、供电0。v8后六LUN几何与GPT18同刷机前逐字节一致，boot/logdump匹配113候选，persist/NV6/来源4保持，userdata继续rw。最新DPU超时2、GPU故障0/taint0；用户物理确认仍仅涵盖113首轮v5之后，不能替代最新显示验收。

第四次113正常重启核验通过。RAM v9运行240.24秒，240次写入/204次rename，前置守卫在触发DSP转储前退出1，未生成转储；保留失败原档案，不称捕获成功。试验仍完整收尾SLPI offline/供电0/taint0、NV6/来源4保持。接近传感器120秒实测37样本、36次NEAR/FAR变化，起止FAR；用户完成遮挡/移开并确认画面操作正常，[接近实机核验](../reference/kernel113/proximity-v9-validation.json)通过。v9后桌面/网络/音频空闲核验通过，DPU/GPU故障0。加速度/光线/磁力计仍254；v10改为文件服务仍在运行时捕获，并保存每个前置条件的实际值。

第五次正常重启回到Phosh但出现WCD934x efuse WARN/taint512；SLIMbus DMA准备31次失败，后续682个寄存器ENOSPC、DPU超时2，不能记音频或完整重启验收。启动日志完整私有保存，boot/logdump/DTB、NV6/来源4/persist仍匹配，用户确认已显示Phosh。停止GUI和用户音频进程、PCM关闭/功放静音、ADSP与无线离线及sync后，第六次正常重启恢复taint0/DPU0/GPU0，[慢启动核验](../reference/kernel113/slow-boot-validation.json)和[恢复启动核验](../reference/kernel113/reboot-audio-clean-6-validation.json)分别保留。资源排空的长期效果仍需重复验证；v10只在第六次新启动进行。

v10的转储前守卫失败原因已经确定：现存devcd1来自DPU显示控制器，不能用所有设备转储为空来判断SLPI是否可捕获。已保存152,277字节真实DPU文本快照，校验其XR24/1080x2400活动扫描输出；两次DPU超时仍保留，不算花屏永久修复。v10完整收尾offline/供电0/taint0。

重复排空用户音频、停止ADSP和无线后，第七次正常重启taint0、DPU超时1、GPU故障0，分区/DTB与NV/source保持。v11按failing_device筛选SLPI，实际取得20,871,615字节ELF；20个段与本机原厂MDT完全对应、19个128字节代码块匹配，51个有效ULog解码，详细日志仍私有。SPI初始化报npa客户端创建失败；早期NPA记录已滚出，不能据此直接判定传感器失效原因。原始转储SHA256与地址映射核验见[ULog核验](../reference/kernel113/ulog-v11-validation.json)。

v11主动debug crash用于复制转储；内核恢复后SLPI确实再次running、累计两次now up，没有power up超时，最后正常停止/供电归零。daemon收到EPIPE后返回0属于上游退出行为，不能记文件服务长期健康。桌面/网络/NTP/音频空闲检查通过；用户确认这次解锁后显示正常，未再次确认应用，并要求减少重复画面询问。后续优先自动核对，出现新故障或需要实物操作时再询问。v12准备在下一次新启动daemon运行3秒、无SSC查询时获取早期NPA记录。

第八次完整音频/ADSP清理后正常重启taint0，启动快照DPU/GPU故障0，USB重新枚举的EUD日志已补采；采集脚本增加15秒设备出现等待及明确的读取失败检查。v12无SSC查询，daemon运行3秒后主动捕获SLPI；20,871,615字节转储、51个ULog、4,651条记录均按本机映射解码，非法/未解析记录0。早期NPA明确保留I2C_QUP_DDR和SPI_QUP_DDR在/icb/arbiter创建失败，错误码4。试验后恢复running再正常停止，供电归零/taint0/NV6/source4保持；桌面/网络/音频空闲通过，DPU超时累计2。

本机原始SLPI版本为SLPI.HY.2.2-00121，字符串中确有本机几个传感器驱动名，但不能用字符串存在来认定驱动功能。参考[同SoC适配者的固件对照试验](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-23-the-firmware-version-was-the-cause.md)形成版本匹配假设；该其它设备结果不能作为本机修复结论，也不导入其固件。正在离线检查[RMX1931维护者的Chinese C28资料包](https://github.com/alextrack2013/rmx1931-stuff/releases/tag/f14-2)，版本与段边界确认之前不部署；整包脚本不执行，原厂分区/NV/校准保持。

第九次正常重启taint0、启动快照DPU/GPU故障0。C28包CRC/设备声明检查通过，仅离线取SLPI 00098，22个MDT头/20个载入段、同链接基址和20MiB跨度核验后，在单独Linux只读目录测试；未执行整包脚本或刷原厂分区。v13采用原校准/配置的私有RAM副本，磁力计实际识别Memsic MMC5603X，50个有限三轴μT样本、48个不同向量、正常禁用。[磁力计采样核验](../reference/kernel113/magnetometer-v13-validation.json)通过，方向矩阵全0警告、实际旋转响应和准确度未验收；接近/加速度/光线254。

v13实际SLPI转储20,860,763字节，用C28自身MDT地址映射及19个代码块匹配解出51个ULog/4,813条记录，无非法/未解析记录；SPI客户端失败仍有，I2C出现3轮NACK但磁力计实际采样成功，不能将所有I2C失败泛化为所有传感器失效。试验后恢复原firmware选择，SLPI offline/供电0/taint0、NV6/source4保持；原始SLPI复制文件逐字节不变。桌面/网络/音频空闲回归通过，DPU超时1。两版各自硬件结果不能合并成一个可用系统，C28未设默认或自动服务。

第十次正常重启核验taint0、启动DPU/GPU故障0。v14 C28磁力计60秒取得302个样本、258个不同向量，方向分离最大1.5度；用户随后指出转动可能超过窗口，故不能认作旋转响应通过。试验供电/SLPI/原firmware选择收尾通过，桌面回归通过但DPU超时累计2。USB SCP中断后重新传输，归档SHA和内部逐项SHA通过；两个SSH包装器仅调用OpenSSH，没有修改主机网卡或路由。

用户明确要求重复转动。v15保持同一C28固件和本机原配置的RAM副本，延长SSC采样至180秒、外层195秒，daemon总上限300秒；使用第十一次新启动守卫。旧stdout提示仍写60_SECONDS，实际执行参数为180秒，这一标签错误保留在历史证据中。用户本次反馈完成时，独立观察确认ssccli仍运行、无采样结束文件，窗口已过77.15秒且取得385个样本；确认时机的私有收据保存。响应变化与最终清理必须以完整v15归档核验。

v15完整实测898个磁力计样本、833个不同向量，方向分离179.2度；用户操作在活动窗口内得到独立观察，达到事先设定的200样本/30度响应门槛，[窗口内转动核验](../reference/kernel113/magnetometer-v15-validation.json)通过。矩阵警告及指南针准确度仍待查，无自动桌面服务。转储使用C28自身映射核验19个代码块、51个ULog/5,199条记录，无非法/未解析记录；SPI初始化错误仍有。主动debug crash后DSP实际恢复running，然后正常收尾offline/供电0/taint0、原selector恢复；原始SLPI文件再次逐字节比较保持。桌面/网络/音频空闲核验通过。第十一次启动的初始EUD读取在32.77秒遇到USB IO reset，owner已释放，后续有界补采完成；runtime完整早期Linux日志和健康检查通过，读取失败未冒称成功。

C35同机型维护者参考包已离线核验；版本字符串与C28同为00098，但24个SLPI文件中15个不同，不能把同版本字符串当作字节相同。候选仅暂存独立只读Linux目录，尚未作为默认固件或刷入原始分区；对照保留为v16、下一轮新boot12。补充查询陀螺仪和compass：当前实际CLI为libssc 0.4.4，[上游CLI源码](https://sources.debian.org/src/libssc/0.4.4-2/src/libssc-cli.c)存在gyroscope分支，帮助文字漏列不代表入口不存在。磁力计回调直接输出固件三轴数据，未应用安装矩阵；[安装矩阵警告源码](https://sources.debian.org/src/libssc/0.4.4-2/src/libssc-sensor.c)检查整数求和为0，警告本身不独立证明九个原值均为0。

第十二次新启动核验taint0、启动DPU/GPU故障0。C35 v16磁力计50样本/49不同向量、正常停采；接近/加速度/光线/陀螺仪/compass均254、没有样本，[六项实际查询核验](../reference/kernel113/sensors-v16-validation.json)保留。C35转储按自身MDT/19代码块映射解出51个ULog/4,910条记录，无非法/未解析记录，SPI初始化客户端失败仍有；收尾offline/供电0/taint0并恢复原00121选择，原始SLPI文件逐字节保持。桌面/网络/音频空闲回归通过。重启观察器现在分别记录shutdown/startup采集完成与中断；本轮两次USB IO中断均释放owner，后续补采完成，不再用“全部捕获完成”掩盖中断。

配置参考的新方向是[同机型C38 vendor源快照](https://github.com/arnodorian-r/vendor_dump_RMX1931)，固定commit 0ef1fc05360421845f1ae905852dbfe63b26ba68。GitHub REST读取因配额403停止，改用公开Git树读取；只在私有目录读取传感器配置。发现树中JSON为Git LFS指针，不能把129字节指针当配置比较。必须取得并核验LFS真实对象SHA/长度后才做比较，不导入他人persist或校准。准备的参考采集代码及失败尝试不等于已完成配置验证。

C38真实LFS对象未取得：media连接中断，专用git-lfs读取到120秒边界退出，未用指针做配置比较。转向另一份同机型Lineage18.1源快照，固定b94e26044cb95092add5dd8026fab0fdcb61433a，10个实际配置/声明文件均按Git blob哈希验证；5个同名文件不同、5个平台文件在原来源中改为合并结构。这不能直接证明选择错误。进一步比较LSM6DS3C 14项总线/IRQ/电源配置，与原文件及实际生成RAM v7完全一致，两个SoC339筛选均匹配，[硬件参数比较](../reference/kernel113/lsm6ds3c-config-comparison.json)通过；简单SPI实例/IRQ/电源错误暂不受支持，不能称SPI错误已经修复。后续重点仍为本机旧固件版本及SPI NPA路由/ABI调查。参考只作私有离线分析，没有改本机配置或导入校准。

本机磁力计配置文件中的一个JSON字符串包含未转义TAB；严格JSON解析失败，但宽松解析可取得值。这是语法问题的证据，尚不能证明DSP解析器拒绝了文件。候选仅在私有RAM副本把TAB表示为`\t`，严格解析通过且解码对象逐项相等，不改变校准或硬件参数。

boot12关机准备在ADSP停止15秒边界退出143，日志显示约15.07秒后原生停止完成。独立检查确认SLPI/MPSS/ADSP全部offline、用户音频进程清空、功放静音、传感器供电0、taint0；原生ADSP移除了声卡和PCM状态节点。保留停止前两项closed证据与失败读取产生的空文件，未编造停止后的PCM样本，[清理最终核验](../reference/kernel113/audio-quiesce-12-validation.json)通过后才正常重启。EUD关机读取中断保留，启动采集完成并释放owner。

第十三次新启动核验F2FS rw、taint0、boot/logdump/live DTB、NV6/source4/persist保持，启动DPU/GPU计数0。v17仅测试上述RAM转义，仍使用原00121固件；接近查询0、Sensortek STK3331真实1样本并正常禁用，磁力计/加速度/光线/陀螺仪/compass均254。六项查询都有实际档案，[转义试验核验](../reference/kernel113/sensors-v17-validation.json)表明这项语法修正不足以解决枚举。实际转储按原MDT/19个代码块校验，51个ULog/5,013条记录，无非法/未解析记录，SPI NPA客户端错误仍在；有意debug crash后恢复running再停止，offline/供电0/taint0、原selector保持。SCP中断后重传并核对完整SHA；桌面/Wi-Fi/HTTPS/NTP/音频空闲/功放静音回归通过，DPU/GPU计数0。

另从[RealmeUpdater自己的更新跟踪仓库](https://github.com/RealmeUpdater/realme-updates-tracker/blob/6e0a3181b7c365b5a9d560c9abe164100b9faec3/data/archive/RMX1931.yml)取得RMX1931 A.11/A.13/A.15官方域名链接，三个链接的小范围读取均返回206。只对A.11的OZIP做主机范围读取，[Kerler格式实现](https://github.com/bkerler/oppo_ozip_decrypt/blob/eb93b3f3fb7be3564cc546c88699ab4062a04928/ozipdecrypt.py)固定版本仅作资料读取，未执行其删除/提取程序。ZIP目录找到约65MB压缩modem条目；服务器曾返回带完整长度头的空内容，长度校验拒绝，失败记录私有保留。范围请求改用独立查询地址后继续；最终CRC、固件版本/段边界及是否实际部署以新参考核验为准，不能把目录或链接可读取当成固件验收。

A.11读取调整未取得完整modem：78个范围的传输长度检查通过，但未达条目CRC验收；大区间取得21,011,704字节后120秒超时，续取返回空内容/curl18。[未完成尝试](../reference/kernel113/a11-reference-attempt.json)保留失败，SLPI未提取、未部署，包/运行v18脚本尚未生成。后续应定位SPI/NPA或选取可完整校验的同型号来源；不能直接把私有片段当固件候选。

当前boot13在2,331.23秒（约38.9分钟）处完成只读复核，完整dmesg中DPU/GPU计数仍0、taint0、Phosh进程存在，SLPI offline/供电0；[被动状态核验](../reference/kernel113/passive-after-v17-validation.json)只证明日志与进程状态，未重新询问画面或认定休眠/长稳已修复。下一轮新启动前的ADSP停止25秒时限脚本只在主机准备，尚未执行。

桌面回归逐次核验Phosh、2.4GHz Wi-Fi、HTTPS、NTP、UCM、PCM空闲关闭、双功放静音、振动starts0、供电引用0。DPU/GPU计数与物理确认范围见JSON；显示长稳及其余15组硬件未完成。原始日志、身份、固件、校准、凭据、镜像均在私有输出，未公开、提交或推送。

后续本机反汇编和运行时ICB表核对修正早期NPA归因：16表示请求字节数，即两个master/slave对；0x400客户端类型受支持。错误4对应缺少路径，但SPI记录错误后走正常函数返回，I2C的NULL句柄也与STK3331实际采样并存。[本机取证](../reference/kernel113/npa-own-firmware-validation.json)没有证明NPA错误是缺失传感器的根因，继续检查SSC注册和可用状态。

boot13关机清理采用ADSP停止25秒上限，完整通过最终三个DSP离线、声卡注销、功放静音、传感器供电0及NV/source核验。第十四次正常启动[核验通过](../reference/kernel113/reboot-audio-clean-14-validation.json)：完整早期Linux日志、F2FS rw、分区/DTB匹配、taint0、DPU/GPU0。关机EUD读取中断保留，启动读取完成，所有owner释放；SSH实际新启动和健康核验独立通过。

[libssc 0.4.4源码](https://sources.debian.org/src/libssc/0.4.4-2/src/libssc-sensor.c)请求默认实例且选第一个SUID。独立标准库客户端按已核验的SSC/QMI协议比较全量和默认请求，保留所有响应体、事件编号和空载荷；主机Google Protobuf独立验证编码和实机逐帧解码。census14每组32次请求、32个成功QMI操作结果、32个768事件，共64帧，非法帧0；accel/gyro/mag/ambient_light全量与默认均0，proximity两组均1。[全量/默认对照核验](../reference/kernel113/ssc-census14-validation.json)排除这四种数据类型因默认实例过滤而遗漏的解释，但不能认定所有匿名条目都没有物理驱动。

全量空类型目录返回13个UID，已查询类型的总并集15；这些UID的名称/类型/可用标记尚需属性请求确认，原始UID和帧保持私有。六项原CLI对照仍仅STK3331接近取得1样本，其余五项254；[六项核验](../reference/kernel113/sensors-census14-validation.json)不宣称四项硬件通过。20,871,615字节SLPI转储按原00121 MDT和19个代码块验证，51个ULog/5168条记录完整解码，非法/未解析0。主动debug crash后恢复再正常停止，原selector/offline/供电0/taint0、源4/NV6保持；桌面/网络/NTP/音频空闲回归通过，DPU/GPU0。boot14不能原地重放SLPI试验。

磁力计硬件是否存在已回答：[realme官方参数](https://www.realme.com/realme-x2-pro/specs)列出地磁传感器；本机C28 v15已取得Memsic MMC5603X的898样本，窗口内实际转动响应通过。默认00121支持和指南针准确度仍待适配。

2026-10-12，boot15属性枚举实际完成。独立QRTR客户端按已核验的协议发送10个SUID查询、15个属性查询，收到25个成功QMI ACK和15/15属性响应；属性请求ID为1、响应为128。50个QMI帧经Google Protobuf独立解码与客户端记录一致，非法帧0，[属性核验](../reference/kernel113/ssc-attributes15-validation.json)通过。原00121固件中Sensortek `stk_stk2x3x`以`wise_light`注册，physical_sensor/available均true；标准`ambient_light`查询为空不能再解释为光线硬件完全未注册。尚无真实lux采样或桌面自动亮度验收，其它13个条目为软件服务；accel/gyro/mag仍无条目。六项原CLI对照仍仅STK3331接近取得1样本，其余五项254。此次SLPI转储20,871,615字节，51个ULog/5,113条记录及19个代码块映射核验通过；试验结束恢复原selector、offline/供电0、taint0及NV6/source4保持。

用户随后报告花屏闪烁，触发条件未知。boot15初始阶段在传感器试验之前已出现1次DPU超时，原回归现场累计3次、GPU0、taint0，不能把显示问题直接归因于SLPI。真实DPU转储152,265字节与原始日志私有保存。第一次停止/重启显示会话时，fbcon仍保持输出，新增`drm_crtc_wait_one_vblank`/`drm_fb_helper_damage_work`警告，taint变为512；greetd的initial_session每boot只自动执行一次，该次曾进入Phrog。恢复原用户Phosh和运行时解绑fbcon后仍新增一次DPU超时，累计5次。软件截图为正常1080×2400锁屏，用户确认当时画面恢复稳定；截图和这条确认均不能证明永久修复。[回归](../reference/kernel113/display-regression15-validation.json)、[失败恢复](../reference/kernel113/display-reset15-validation.json)及[后续动作](../reference/kernel113/display-actions15-validation.json)各自保留。

原display trace/snapshot已只读归档并核验。首个启动超时的看门狗记录真实busy=1，83ms期限到达时TE/vblank仍继续、CTL start IRQ成功，但没有等到PP完成。现有#87看门狗竞争修复和#113 DSI burst/EOT修正已经在运行内核中，不能把它们重新当作未应用修复；现有记录也不足以认定旧计时竞争或过早到期。原厂PPS/DSC参数保持，下一步假设来自本机原厂60Hz位时钟1.107GHz与当前Linux约371MHz的差异，见[跟踪核验](../reference/kernel113/display-trace15-validation.json)。

原生DRM时序对照第一轮被残留CRTC状态守卫拒绝，退出1，没有提交测试模式；恢复Phosh新增DPU1，累计6。调整为先通过正常DRM流程关闭旧输出后，15b实际完成原速率/接近原厂速率/返回原速率三轮，每轮140次翻页，总420次，保持1080×2400@60和原DSC。实测DSI位时钟370,607,848 / 1,106,583,392 / 370,607,848Hz；跟踪窗口425次帧完成、426次看门狗arm，DPU/PP超时0。但恢复Phosh后新增2次DPU超时，累计8，因而不能接受升频作为修复。[时序核验](../reference/kernel113/display-clock15b-validation.json)保留测试窗口与整轮操作的差别。这轮仅运行用户态DRM程序，没有改内核或分区。

原生DRM使用普通XR24帧缓冲，Phosh使用QCOM压缩modifier `0x500000000000001`，形成缓冲格式假设。实际Phoc二进制包含`WLR_DRM_NO_MODIFIERS`选项；尝试向原launcher仅加入该环境变量后，试验在确认Phoc环境和线性缓冲之前退出1。不能认定选项已经有效传递，也不能据此排除压缩缓冲问题。退出清理逐字节恢复原launcher、恢复Phosh/greetd；当前仍是原QCOM modifier。失败试验/回滚新增DPU1，并记录1次GPU故障，最终累计DPU9/GPU1/taint512，[失败与回滚核验](../reference/kernel113/display-linear15-failed-validation.json)明确不验收显示稳定。

最终收尾的`wrap-up15.tar.gz`保存50个逐项SHA核验文件及清单，包括当前dmesg、原display/radio trace与snapshot、服务/供电/NV/来源/PCM/功放状态。GPU devcoredump曾在只读清点中可见323,539字节，但收集时已消失，转储二进制未取得；GPU故障日志保留，不能将其写成转储捕获成功。初次收尾核验还发现原display已耗尽的`snapshot:count=0`触发器使一个事件保留；补充`wrap-up15-trace-final.tar.gz`保存40个逐项SHA核验文件，解除该触发器，原snapshot前后及原归档SHA一致，最终五个trace实例均tracing_on=0、事件为空。整个收尾没有新增DPU/GPU故障或内核警告，见[最终收尾核验](../reference/kernel113/wrap-up15-validation.json)。

临时常亮idle-delay=0已恢复60秒，锁屏策略保持；原Phosh脚本、原00121 firmware selector恢复，SLPI offline/供电0，PCM关闭、双功放静音、NV6/source4保持。没有剩余传感器/DRM试验进程，主机EUD/fastboot/adb诊断进程已退出。fbcon bind=0为本boot运行时设置，不新增永久配置；本轮不为清除taint512追加自动重启。完整rootfs新镜像、显示/GPU长期稳定、原00121缺失传感器、摄像头、指纹、GNSS、蜂窝和休眠等继续保留为待办，15组硬件状态完整保留。本轮到此结束。
