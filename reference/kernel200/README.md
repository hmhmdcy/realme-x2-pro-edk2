# 阶段200：静态MMCX设备树与CAMSS成对启动，前摄跨启动取流

静态四电源域设备树和CAMSS运行时MMCX修复已成对部署到真机。新启动kernel183上，两次实体前摄会话共四轮、12帧1928×1088 RAW10；自身MMCX请求活动384、暂停0，原频率表保持，无外部性能helper。803.82秒最终检查taint0，WARNING/Oops/GPU/SLPI fatal/蓝牙重组均0。完整外设goal继续；摄像头尚未成为正常启动即用的完整用户态功能。

## 成对部署与回退

UEFI把板级DT嵌在boot内，Linux Image仍从logdump183加载。基于准确boot172构建，固件模块仅DTB改变，908节点中只有CAMSS的power-domains与power-domain-names两属性改变；其余固件代码、shim、ramdisk、Android头、compat DTB、分区尾部保持。构建诊断仍为原有30条、无新模板。[构建比对](build-package-validation.json)

- 新boot：5109097b…，100663296字节；内嵌静态DTB2e2f8e64…，108410字节。
- 安装CAMSS：82cbc052…；新启动ELF build-id与安装文件逐字匹配。hci_uart185/fastrpc189也核对loaded build-id，784个模块树文件保持准确预期。
- logdump183 e73754c7…、Image183 bfa72dd9…保持；persist/NV核对保持，没有写这些分区。
- 回退boot172 77e1a272…已另存主机kernel200/boot-rollback-k172-private.img；旧CAMSS e9b73f4c…在手机k200-baseline与k200-deploy中、主机完整私人归档中。实际回退须重新核对设备身份，将旧boot与旧模块配套恢复，保留logdump183。

旧启动已有193内核WARN1与199 OF属性警告2，taint512均据实保留于归档；新启动没有这些事件。只提交一次Linux RESTART2与一次fastboot reboot。[刷写](flash-validation.json)、[新启动读回](runtime-validation.json)、[最终健康](native-health-validation.json)

停机第一版保留Wi-Fi/NetworkManager时，MM被D-Bus重新拉起，两次检查退出且未发重启。改为切断管理网络后，在已归档的独立进程中停MM、Wi-Fi、所有remoteproc、显示/音频，核对、冻结文件系统，再单次RESTART2。重启后的完整停机收据已回读验证。首次fastboot调用使用WSL路径，Windows工具本地打开文件失败、尚未发送数据；保留该失败，改Windows路径并重新核验fastboot身份/geometry后，成功传输与写入一次。没有对未知切换盲目重复。[部署准备](pre-transition-validation.json)

## 新启动的VIO状态与实体前摄

RPMH regulator驱动把enabled初始化为-EINVAL，在首次正常enable之前公开state unknown；这不是已证明关闭的电源。195开发VIO helper的“必须disabled”条件因此拒绝，本次r1准备完整撤销。200 helper仍只做OF精确引用和只读查询，限定PM8150L RPMH父节点，允许0或该provider的初始-EINVAL，拒绝enabled及其它错误。模块加载前后VIO均unknown/1.8V/users0，没有电源写入；标准sensor首轮使用后变为已知disabled。[源码](samurai-vio-phandle.c)、[构建](vio-helper-build-validation.json)

该helper仅用于开发，不替换安装模块；新源5b7aad11…、模块5325464e…，已卸载。W=1、checkpatch及导入符号核对通过，Image/config/canonical DTB/符号表/模块顺序保持，原14个其它修改源及199 CAMSS/DTS/binding保持。[源码收据](source-final-validation.json)

静态四域已存在，不再热替换CAMSS域属性。sensor-only overlay通过新启动重读的phandle编译；普通IMX471在CCI1 master1地址0x10绑定，pattern0的真实媒体链路采集，CAMSS只unbind/rebind刷新notifier，没有替换或卸载其永久模块。四轮均3帧，序号/时间戳递增、>99.9% DMA覆盖变化，活动VFE约847MHz/CSID600MHz，自己的MMCX384，暂停0。四张私人RAW10已解码，行/像素变化且各图不同。[原生验证](front-native-validation.json)

第一会话6帧及资源撤销通过，但GPIO15 CTL从新boot原始1变0，末尾精确恢复断言失败。原sleep bias-disable清掉了初始下拉。标准GPIOv2 bias请求被接受但硬件无变化；该MSM GPIO chip未挂set_config。确认MCLK关闭、GPIO15无owner且input低后，对north CTL0x0390f000的pull掩码3做一次0→1原值恢复，读回/电平检查通过。保留失败摘要与单独恢复记录。

随后只把MCLK sleep状态改为bias-pull-down。第二会话又完成两轮共6帧，全部三个CTL与原值1/1/1、低电平、七Q LDO采样和P0/Q1精确恢复，未需额外寄存器恢复。VDIG/VANA退出恢复关闭状态原VSET，VIO最终disabled/1.8V/users0，S8C1.352V/users3保持。[最终overlay](front-probe-overlay.dtso)、[构建](overlay-build-validation.json)

## 外设回归与开放项

新boot早期74秒SLPI尚offline，随后按既有启动门控运行；最终ADSP/SLPI/modem均running，三项SensorProxy Has true，标准加速度/亮度/接近Claim/Release通过。蓝牙只扫描8秒，发现10个设备，结束停止扫描、恢复原Powered，新增重组/内核故障0。没有配对、连接或振动动作。Wi-Fi启动后connected，早期旧端点两次超时不是最终关联失败。新boot通过新发现USB peer与原严格SSH公钥管理，约6MB归档完整传输并核对；不能将这一个启动窗口称作NCM长期缺陷已修复。[外设回归](peripheral-regression-validation.json)

MM191文件保持，新boot仍可发现XTRA/3服务器、location capabilities103，GPS关闭。MM State−1/PowerState1，旧191的DMS online状态未跨本次重启保持；没有再次盲目online或reset。真实SIM注册/数据/通话/SMS及GNSS fix仍未验收，新boot轨道有效期尚未查询。

168份原生证据逐成员核对，包含四张实体RAW；原图、统计、相关指纹和网络/设备身份均只存E:/edk2-samurai-out/kernel200。[归档收据](evidence-export-validation.json)

下一步继续常规板级相机资源/持久化用户态接入，核对四路PLDO实际输入与双PMIC冷启动，或推进新boot的GNSS-only GeoClue/辅助加载与modem电源策略。其它镜头/模式、曝光色彩方向、完整冷启与长稳、BT phase5历史重组、Wi-Fi/USB PM、FastRPC普通信号/共享池/SSR等仍开放。详见[检查点](../../NEXT-SESSION.md)与[硬件清单](../../linux-port/docs/HARDWARE-STATUS.md)。
