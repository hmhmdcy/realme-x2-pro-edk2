# 309：四摄硬件AWB与CSI接收时钟修复

2026-10-19。主摄、前摄、广角和长焦当前模式已运行硬件RGB统计、IPA及AWB回写。广角／长焦进一步联合运行AE与AWB，在当前场景达到0.16亮度目标附近。公共CAMSS修复已安装，产品libcamera仍使用RAW＋CPU ISP；完整校准与适配目标继续推进。

## 底层修复及实际部署

主摄首次启动硬件统计流失败，报Pixel clock is too high for VFE。原CAMSS把传感器阵列的1.92GHz像素率作为CSI接收吞吐率。修复在公共CAMSS层从链路频率、通道数、PHY类型和输入位深计算接收像素率，供VFE时钟选择和检查使用；保留阵列像素率供曝光／帧时序计算。

主摄499.2MHz、三组C-PHY、10bit对应接收像素率684617142 pixel/s，计算式为link_freq × 2 × lanes × 16 / (7 × bpp)。没有提高时钟表上限、钳制速率或改写传感器时序。阵列像素率与CSI像素率的区分依据[Linux CSI-2驱动文档](https://www.kernel.org/doc/html/v6.10/driver-api/media/tx-rx.html#pixel-rate)。

[补丁](receiver-pixel-rate.patch)只改camss.c、camss.h、camss-vfe.c。基于307的RGB统计源码，当前树/home/cy122/x2pro-linux/camera309-link-kernel，分支samurai-link309，提交f7ee1b4735a217e2aebdcae1cd385ed8823fc710，干净、未推送。[源码状态](source-state.json)、[Werror构建](kernel-build-validation.json)。

当前手机保持#298 Image、boot276与305长焦模块，只永久更新qcom-camss.ko：

- SHA256：09eaf871562f79431009df0b6f3adda026b2da9cd57a1d76dfdf3b284d123eae。
- 加载note与安装文件一致、intree=Y、taint0；原模块备份保留在/var/lib/samurai/k309-module-install-r1/qcom-camss-before.ko。
- 安装后前摄4帧产品RAW检查通过，PW/WP恢复。之后直接复用已部署模块，保持桌面服务运行完成联合AE/AWB采集。

[安装结果](install-validation.json)、[当前部署锁](../../linux-port/camera/deployment-lock.json)。未改Image、DTB、传感器驱动、板级供电和系统libcamera包；其它模块和软件包沿用未变更基线，没有重复全量扫描。

## 当前模式实测

| 相机 | 当前模式 | 修复后硬件AWB帧数 | AWB参数更新 | 帧周期中位数 |
| --- | --- | ---: | ---: | ---: |
| S5KGW1 主摄 | 4608×3456 SGBRG10 | 38 | 14 | 33272µs |
| IMX471 前摄 | 2304×1728 RGGB10 | 40 | 15 | 33333µs |
| IMX319 广角 | 1632×1224 RGGB10 | 38 | 14 | 33335µs |
| S5K3M5 长焦 | 2104×1560 GRBG10 | 38 | 14 | 33293µs |

上表为r3，共154帧；四路均达到连续8帧AWB算法锁定，随后各4帧产品RAW＋CPU ISP检查通过。主摄实测帧周期支持现有阵列行长／像素率比例；这不证明曝光／增益控制的生效延迟。前摄日志记录的2124是最小帧长，当前4250帧长对应约30fps。

r1保留主摄0帧失败记录和前摄42帧成功记录。r2广角40帧／长焦45帧联合AE/AWB：暗场下接近33ms、16倍增益上限，亮度仅0.0524／0.0166，未达到0.16目标。

r4使用已安装模块、PW/WP进程不变，广角38帧／长焦36帧联合AE/AWB，各3次AE提议，末端亮度0.15815／0.15804，目标为0.16。末端曝光／增益约33.140ms×6.095、33.192ms×5.094，两路AWB也达到连续8帧锁定。场景亮度已变化，因此此结果与r2暗场边界分别保留。

309成功采集总计355硬件帧、130次AWB参数更新，其中159帧联合AE/AWB。量化WB元数据与确认SOF一致；曝光／增益元数据符合各传感器当前时序模型。[逐次结果](capture-validation.json)。模型一致不代替主／前摄尚未测量的控制延迟；广角和长焦沿用302／306已测的两帧延迟。

全部实验和安装worker已终态。末次CAMSS／两CCI休眠，九路相机供电关闭且用户0，PW/WP各一进程，无采集worker残留，所检查故障无增量、taint0。[收尾](final-health-validation.json)。旧GPU／modem／SSC问题仍开放，不能据此称整机全部健康。

## 原厂参考与调校范围

只读提取主摄Qtech／Sunny和前摄Sunny三份原厂调校，复用306已验证的BLS12类型结构解码。主摄两供应商合计21个IFE区域、前摄5个区域，均启用且offset=960 U14、四通道threshold=0。独立原厂解析器未重复运行，实际模组供应商绑定未确认。[来源](factory-source-validation.json)、[解码](factory-bls-validation.json)。

主／前摄实验BLS使用3840 U16、归一化1.06201171875。主摄统计残余设0并提高最低信号门槛；前摄残余64 U14沿用现有helper的输入黑电平参考。广角、长焦沿用308参考并接入既有AE模式配置。这些都是实验参考，不是个体暗场、白点、CCM、LSC或完整原厂调校。304 EEPROM仍缺完整校验、绑定及几何确认，未应用个体值。

## 后续使用

SDK目录/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline仍为308源码，构建用308/build-candidate.py。309/prepare-runtime.py只编译现有camera-smoke.cpp并打包当前profile，不再覆盖已编辑源码／调校。修正后的双平面NV12与全范围BT.601读取已用于309采集。

后续普通采集复用当前驱动，参考native-current.py／launch-current.py；不再默认切换模块或停止桌面服务。现有k309-cameras-r1～r4和k309-module-install-r1均已终态，不重放已提交事务；源码生成／提交／安装脚本保留为已执行记录。

下一步测主／前摄曝光和增益的实际生效延迟，扩展联合AE/AWB及其它模式；继续正式黑电平、颜色、阴影、模组绑定与产品硬件路径。运行中手动WB／AWB模式请求及双WM恢复也未完成。验证按变更范围开展；用户延期的纯色／遮光项目不阻塞其它工作。
