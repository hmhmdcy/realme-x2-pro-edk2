# 298：公共黑电平映射与暗绿硬件对照

2026-10-19。现机 **#298 / 7.3.0-rc6-rmx1931-samurai-k298+**，维护树干净分支 `samurai-blc298`、提交 `c5e118faec21a6c4bd2e7d5b86b3b21ad9dc2117`。BLS 已实现并通过真实 CSI→VFE175 FULL 图像验证；广角临时 BLS／白平衡／增益组合改善暗绿。**遮光暗场标定、正式模组调校及 libcamera 硬件 pipeline／IPA 尚未完成，产品应用仍走 RAW＋CPU ISP。**

## 分层实现

只改两个 SoC 驱动文件，55增／2删，一个本地提交。[补丁](blc-candidate.patch)、[源码收据](source-validation.json)。

- 复用现有 `camss_params_wb_gain` 的相等 `g_sub/b_sub/r_sub`，把归一化 U16 按最近整数映射到 U14 BLS offset。BLS scale 固定 Q11 unity=2048，保持“先减黑、再乘 WB gain”的接口语义，没有隐式拉伸范围。
- 复核固定 Titan17x BLS12、生成寄存器头与 XSD：配置0x6b0、阈值0x6b4／0x6b8、lens enable bit11。阈值置零，保留非本模块位；没有假设 WB offset 寄存器的符号位。[固定来源与数值](blc-protocol-validation.json)
- 不相等的减偏移、非零加偏移继续拒绝。WB DISABLE 同时旁路 BLS，旁路中可缓存更新，ENABLE 恢复；图像重开默认减黑0，停流和已有错误回收路径关闭 BLS。
- 板级 DT、接线、sensor 模式、固件、公共 UAPI 和产品包未改。模组数据／曝光与白平衡算法不进入 SoC 驱动。

本机保存的 Sunny／Qtech IMX319 模组与 sensor XML 已重新解析并固定哈希；现有1632×1224模式来源延续235。它们没有提供本轮可用的黑电平标定字段，也不能凭 sensor ID 认定个体供应商。没有写 EEPROM／OTP，未套用其它手机校准。[模组资料边界](module-evidence-validation.json)

## 实机结果

| 检查 | 结果 |
| --- | --- |
| 长焦 BLS 定量 | S5K3M5 GRBG10 2104×1560、sensor pattern2、CSID pattern0，126图像／111有效统计／128标准SOF。11阶段对照291独立 RDI RAW：减偏移 U16 0／4096／8192／16384、旁路／缓存／重启及联合 WB，最大通道误差1.337以内。[像素](blc-pixel-validation.json) |
| 参数帧关联 | 六次可观察变化的首个图像与参数回执完全一致；禁用期间相同图像不用于证明首个生效帧。[帧关联](blc-frame-association-validation.json) |
| 统计与图像 | 110组按共同SOF配对，无缺事件、重复身份或提前完成；五次ROI对应，断粮恢复保留7帧间隔，晚启动首包SOF19／人口2。[SOF回归](sof-association-validation.json) |
| 广角独立RAW | IMX319 RGGB10 1632×1224，18帧，曝光500→3000→500、模拟增益code512=2×。三份保存RAW的 Python 解码均值与原生解码一致；均值约74.389→126.554→74.390。六倍曝光拟合的 R／Gr／Gb／B 截距中位数均64 DN，**只是场景估计**。[RAW分析](raw-analysis-validation.json) |
| 广角硬件实景 | 126硬件图像／111统计。3000行曝光、2×模拟增益：不减黑 Y98.199；只减黑 Y65.927；加入场景估计 WB 后 Y76.229；升至4×模拟增益 Y106.833。减黑后绿色相对红蓝均值比1.493→1.019，4×时1.014。已实际查看前后私人预览，结构可辨，绿色倾向降低。[硬件测量](scene-analysis-validation.json)、[复查](optical-review.json) |
| 产品回归 | 四摄现有 libcamera RAW＋CPU ISP 路径18段233帧通过，含主摄 SIGINT29帧后重开12帧。[回归](four-camera-regression-validation.json) |

两个成功硬件探针合计252图像／222统计，另有18独立RAW；产品233帧单列。10非法参数拒绝、8参数完成分别在两硬件探针验证；广角实景流程不作为独立图案色彩精度证明。临时 WB 来自本场景灰世界估计 R≈2.22／B≈1.90，实验减黑约64 DN；不是原厂调校、遮光暗场、灰卡或跨光源标定。全图均值接近中性不代表色彩准确，没有把这些值写入正式调校包。

主机实际公共 parser／PIX callbacks 的 ASan／UBSan 覆盖全部65536个减偏移、32768个合法增益、非法输入、仅header禁用、缓存、非本模块位、RDI隔离和停流／重开。旧回调负对照在接受合法公共减偏移处失败。[修后](blc-fixed-host-validation.json)、[负对照](blc-parent-host-validation.json)

## 部署与保留问题

完整 Image／778独立模块构建158.45秒，五阶段诊断0，40CAMSS组件Werror；三嵌入BT模块与安装树匹配。实际只刷logdump，一次Linux→fastboot→新内核切换；boot276和DTB保持。分区尺寸预检曾因阶段号替换误改预期数值而拒绝，**发生在刷写请求之前**；保留日志并修正后重新核对设备与尺寸，执行一次刷写。14脚本非阶段数值和无关哈希审计通过。[过程](preparation-notes.json)、[脚本审计](workflow-adaptation-validation.json)

最终sensor／lens／CCI／CAMSS均suspended，九相机rails及共享IO关闭、MCLK／CCI clocks0；fault0／taint0／pstore0、无CCI错误。SSC／桌面／SensorProxy默认成功，modem／adsp／slpi运行，Wi-Fi／HCI存在。961包／50相机载荷及libcamera r24／config-r19保持。[最终检查](final-health-validation.json)

`checked_runtime_healthy=true`限定已列检查；GPU默认故障、旧modem watchdog、SSC偶发EPERM根因和整机长稳仍开放，`whole_system_healthy=false`。严重IRQ延迟、多次未观测SOF合并、多参数／Request API、其它模式和主／前摄硬件成像仍未验收。`statistics_ready_for_automatic_exposure=false`、完整IQ／硬件IPA未完成。

## 后续收敛

先补遮光暗场与多增益／曝光／温度样本，匹配模组后将有效黑电平及噪声数据放入用户空间调校；再完成受控中性色／多光源AWB与颜色验证。用户选择先做正常场景对照、暂不遮光，没有把实景截距升级为暗场标定。

随后按[硬件pipeline／IPA接入约定](HARDWARE-IPA.md)复用 libcamera 的媒体设备、V4L2队列、sensor helper、延迟控制及IPA传输。现有 BHIST 为线性Y统计，不能据此虚构RGB AWB统计。当前只有实验工具连接硬件参数／统计，不声称 libcamera 产品硬件 pipeline 已接入。

维护树相对7.3rc6为55本地提交／177改动文件，libcamera配方28补丁含发行版既有，PipeWire6项目补丁，三个ignore_unused仍在。局部改动小且无新UAPI不代表已上游；跨新内核／软件包更新的零补丁或最小补丁尚无保证。[更新审计](layering-validation.json)

稳定回退仍#290及其独立778模块。297六产物私下保存，旧内核／模块树与工厂资料保留；全部构建与采集已终态，勿盲目重放切换。私人数据根 `E:/edk2-samurai-out/kernel298`，公开仓库不保存像素、密钥、完整厂商参考载荷或个体校准。

本轮进一步只读提取并核验原厂 `com.qti.tuned.sunny_imx319.bin`（15389568字节），识别14195符号及IFE/BPS BLS、CC12和AWB段；布局／单位／模式选择与独立解码仍需交叉验证，数值尚未装入调校。[提取事实与哈希](oem-tuning-source-validation.json)
