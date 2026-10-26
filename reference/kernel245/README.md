# 245：GPS锁对照、DIAG重连边界与MEMSHARE实测

2026-10-17。保持244启动、boot235/Image183和当前Linux；本阶段没有重启、刷Android或修改分区。用户接收位置仍为**室内开窗窗边**，其它手机能收到GPS作为环境参考。本阶段所有UTC准备检查均成功，但**仍无正SNR、TRACK或真实定位，goal保持active**。

## 已完成的判别

| 原生90秒会话 | 有效SNR字段 | 正值 / TRACK | 缺SV列表事件 |
| --- | ---: | --- | ---: |
| 标准MT锁基线 | 800 | 0 / 0 | 60 |
| 标准API解除为NONE，读回确认 | 746 | 0 / 0 | 60 |
| 复用原DIAG端口及缓存状态 | 746 | 0 / 0 | 61 |
| 再发送原DIAG feature交集 | 746 | 0 / 0 | 60 |
| MEMSHARE请求观察期间 | 746 | 0 / 0 | 60 |

累计3784个有效字段均0/SEARCH；普通/扩展格式可重复报告，不是3784颗唯一卫星。缺列表不计零值，位置status4不是成功fix。每个会话Stop确认、CID释放和close成功。NONE测试后已恢复MT并再次读回；原NV源哈希前后保持。[锁对照](poll-lock-test-validation.json)、[重连基线](poll-resume-r3-validation.json)、[feature重发](poll-resume-r4-validation.json)、[MEMSHARE](poll-memshare-validation.json)

这个结果降低了“仅因MT锁阻止本机定位”的可能性，没有证明某个RF/LNA器件故障。

## DIAG：命令回复恢复，日志通道仍未恢复

从244真实首次启动报文提取原AP四个端口，重新绑定成功；当前modem广告的CMD端点对两次VERSION均返回55字节。没有新feature消息，不能称为新握手。[固定端口探针](probe-fixed-reconnect-validation.json)

首次重连脚本只用被query标注的VERSION作候选，并要求两个等待窗口各收到一份。实际244原始RX有两个不同VERSION变体，query只标注其中一个；当前两份与另一个原始变体完全相同。前两次验证因此过早退出，均未发控制报文、未启动GNSS。修订后保留全部原始RX候选并按实际匹配报文计数，回归覆盖这两个问题；失败记录保留。[诊断](inspect-resume-failure-validation.json)、[回归](resume-r3-regression-validation.json)

同boot、MPSS仅启动一次、原控制peer未见删除，并核两份VERSION后，r3恢复缓存协商状态，发送临时实时模式和十项日志mask。r4另重发原始受支持feature交集。两轮GNSS都正常运行，**诊断日志包均为0**。这只证明CMD查询可恢复，尚未证明旧控制端点/日志数据通道有效；不能把0包解释为RF关闭或这些日志不受支持。

十项ID由已锁定Qualcomm共享头核对：GPS1477、Clock1478、PRX147e、DRX147f、GLO1480、Config1516、IMD Jammer1596、Spectrum1635、BDS1756、GAL1886。位图仅这十位，原始接收上限24MiB/32768记录。[库验证](resume-library-validation.json)

实际采集库明确记录临时实时模式包含上游sleep vote，结束发送释放请求；旧244派生库的“no sleep votes”注释不准确，不能当作协议事实。所有本轮端点已关闭，日志mask清零及实时模式释放请求已发送；没有原mask读回或撤销ACK，不声称精确恢复原位图。244首次启动取得的270份无SV测量仍有效，本轮没有新增可解释RF/时钟日志。

## MEMSHARE：从源码疑点推进到实际请求观察

再次查证两组已成功的Linux手机案例：[MSM8916原作者PR158](https://github.com/msm8916-mainline/linux/pull/158)、[pmaports2039](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/2039)记录添加QMI memshare后多机型GPS成功；[MSM8953 MR5132](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/5132)也明确归因于该驱动。另有[PinePhone MR494](https://gitlab.com/postmarketOS/pmaports/-/merge_requests/494)通过modem/gpsd配置获得冷/暖定位的测试。前两组属于特定固件的内存服务缺口，不能直接把2MiB保留区移植到SM8150；后者外置USB modem接入也不等同本机QRTR。

本机缺少memshare驱动早在234/235已记录，并非本次才发现。原厂R GPL固定提交的[服务头](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/soc/qcom/memshare/msm_memshare.h)定义service52/version1/instance1、GPS client0；[IDL](https://github.com/realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source/blob/23172a1571bd91156032cc9fef16284a82b63d2c/drivers/soc/qcom/memshare/heap_mem_ext_v01.c)给出alloc0x22各字段。四份原厂源码已下载并锁SHA。本轮复核当前主线树也没有该实现。

本轮先查没有既有service52，再临时公布原厂同号服务，观察约113秒，含标准90秒搜星。实现仅允许GPS初始size查询返回原板的0；若收到分配请求只返回NO_MEMORY，绝不返回物理地址。**实际收到modem请求0、发送QMI回复0、物理分配0、SCM/DMA所有权变更0。** 四个原始接收记录均为namespace通知，服务器撤销并关闭。

因此没有支持“当前运行中modem正在等待GPS memshare分配”的阳性证据，尚不能排除只在首次modem启动阶段发起的请求。未盲加保留内存、映射地址或修改厂商NV。[实现](native-memshare-observe.py)、[报文边界回归](memshare-wire-validation.json)、[实机结果](poll-memshare-validation.json)

## 244启动后的实际active MCFG再核对

当前qmicli没有`--pdc-get-selected-config`选项，两次CLI尝试均在主机参数解析阶段失败，不是固件不支持。随后按[libqmi原始IDL](https://github.com/linux-mobile-broadband/libqmi/blob/main/data/qmi-service-pdc.json)，直接在广告的PDC QRTR端点发GET_SELECTED_CONFIG0x22及GET_CONFIG_INFO0x28。ACK、token匹配的完成指示均成功，未发SET/LOAD/SELECT/ACTIVATE/RESET。

| 类型 | 运行中描述 | 大小 | version |
| --- | --- | ---: | ---: |
| platform | SR_DSDS-LA-7+7_mode-SM8150 | 12636 | 134224128 |
| software | Common-Commercial | 35524 | 134285321 |

两类均有active ID、无pending。分别与原机Android modem备份的`mcfg_hw/generic/common/sm8150/la/7+7_mode/sr_dsds/mcfg_hw.mbn`、`mcfg_sw/generic/oppo_exp/common/commerci/mcfg_sw.mbn`比较：各自唯一同大小候选包含同描述，**其完整文件SHA1等于当前20字节active ID**，且SHA256仍匹配242服务源清单。这比仅按长度/描述匹配更强，但不是把modem RAM中的全部生效NV读回，也不能证明Android当时选用的配置和RF状态完全相同。[当前selected](read-selected-pdc-validation.json)、[metadata](read-active-pdc-info-validation.json)、[文件比较](active-mcfg-comparison-validation.json)

## 当前状态与续作

81项原生归档逐成员验证大小/SHA256；原始NMEA、DIAG、PDC ID、boot ID和完整快照仅在`E:/edk2-samurai-out/kernel245`。[导出](evidence-export-validation.json)

全部worker和LOC子进程退出；两次预检失败符合记录，后续两轮DIAG及MEMSHARE正常清理。本地4097/52服务0、锁MT、MM位置Enabled0/Signalsfalse/rate30、power1、watch running但active=false/time_prepared=true/数据worker0。三DSP running、Wi-Fi connected，当前boot WARN/Oops/GPU/DSP fatal0、taint0，原NV源哈希保持。[最终健康](final-health-validation.json)

下一步优先恢复**首次modem启动时的持续DIAG日志采集**：复用244已成功顺序，提前发布十类日志端点并保持跨会话，UTC准备后再搜星及online对照。当前重连负结果要求把CMD与控制/数据通道分别验收。若继续MEMSHARE，则须在首次启动阶段观察实际请求，再决定是否实现有明确大小和内存所有权的真服务；当前0请求不支持盲分配。

当前仍用244 guard和[244运输](../kernel244/host.py)，没有新boot身份。其余外设沿用240验收；本轮不把RF/LNA、XO或GPS根因写成已定位。
