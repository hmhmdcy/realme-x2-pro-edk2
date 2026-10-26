320更新：[本机HAL分组规则](../kernel320/README.md)已解释此前4个零节点：每51点需额外跳过1字节，修正解码后均非零；没有补造或写回数据。原文中的零节点结论为当时错误候选布局的历史记录。

# 317：原厂镜头阴影表、校准合成与硬件编码

2026-10-19。仅离线分析与主机构建，手机保持316已部署的r25/config-r20＋314 CAMSS。用户已关灯休息；继续可独立完成的源码、原厂数据和内部图案工作，正常照明下的颜色／均匀场光学校准留待方便时。完整目标active、未完成。

## 已取得的可用结果

从本机原厂Sunny IMX319调校BIN导出全部7个IFE LSC根：7个golden区域、75个基础调校区域，每区四通道各221点。原厂ParameterParser和自行实现的类型表解码器按5位小数归一化后逐表一致；浮点数组为32位，每个221元素数组补齐到8字节边界。原始BIN、模式树和payload保持不变，仅分析副本投影未选模块的版本元数据。

[解码结果](factory-lsc-decode-validation.json)、[直接解码器](decode-factory-lsc.py)。导出XML与数值保存在私有kernel317，不放进设备调校包。7个根包含Default、Sensor0/1/2/3及Preview/Feature1.12分支；尚未重建本机Android运行时的完整选择规则。

已优先读取固定版本的[原厂LSC插值实现](https://github.com/comprehensive9/vendor_qcom_proprietary/blob/36fc163a534963a5b3af52186af5efcc63401ad2/camx/src/hwl/iqinterpolation/lsc34interpolation.cpp)、[Titan17x打包](https://github.com/comprehensive9/vendor_qcom_proprietary/blob/36fc163a534963a5b3af52186af5efcc63401ad2/camx/src/hwl/isphwsetting/titan17x/camxifelsc34titan17x.cpp)和设置／XSD定义。[来源](lsc-primary-sources.json)。该硬件类明确支持Titan175；不能因此声称整个公开CamX版本与本机HAL完全一致。

正确合成关系是：基础调校增益乘以插值后的golden响应／个体响应；之后GR与GB取均值。EEPROM原始值不是可直接送硬件的增益。Titan17x采用17×13网格、13位无符号Q10，unity1024、最大8191；GRR字为R低13位／GR高13位，GBB字为B低13位／GB高13位。DMI两组bank选择为14/15及18/19。

已实现可移入libipa的[通用合成与编码器](libipa/lens_shading.cpp)，不含摄像头地址、板级参数或MMIO。主机Werror构建、非对称通道向量、绿色均衡、量化边界及异常节点检查通过；75个真实基础表共33,150个编码字与独立表达逐字一致。[编码结果](lsc-hardware-packing-validation.json)。尚未接入产品IPA、ARM构建、内核参数块或实际DMI编程；裁剪／缩放到传感器模式的网格重采样仍未实现。

## 个体数据的新问题

304标成五光源的LSC描述实际全部指向同一物理存储表；WB对应三组不同地址映射。五个逻辑光源不是五份独立标定数据。

按当前候选布局，884个LSC通道样本有4个零值。已只为非零节点计算私有golden／unit候选，未补造、未应用。Sunny与Qtech模组描述的LSC均为相同208～1312地址范围、5字节步进，并在同一现有读回中得到相同4个零节点，不能仅换供应商名字就认定修复。[描述对照](module-layout-comparison.json)。仍需确认实际模组绑定、原厂有效性处理以及这些零值究竟来自布局还是原始数据。

现有两版公开EEPROM XSD均含原BIN没有的MemoryInfo signedness等差异；完整203字根结构仍未匹配。类型表可独立定位WB／LSC数组，不能把错位的完整XML当作依据。[结构检查](module-layout-inspection.json)、[schema对照](schema-comparison.json)。这些schema未定义通用checksum字段，不等于证明本机数据无需校验；也不凭空套用其它机型的CRC算法。

## 下一步

先利用已固定的Titan175寄存器／DMI协议，在公共CAMSS驱动增加可选择的LSC参数支持，复用现有参数队列和SOF生效机制；用内部图案验证unity及已知非均匀表，不依赖室内灯光。网格几何和调校留在用户空间，板级DT不承载颜色或个体值。继续追查实际模组／有效标志、golden模式和个体数据，之后再接真实模式重采样与正式光学校准。

316默认系统与其回退材料均保持；没有新手机操作、没有写EEPROM／OTP／NV或persist，没有加载原厂HAL。所有本轮导出和主机构建已结束。
