from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel123'
build=json.loads((ref/'kernel-build-validation.json').read_text());schema=json.loads((ref/'camss-schema-validation.json').read_text());tests=json.loads((ref/'dma-clock-validation.json').read_text());package=json.loads((ref/'package-validation.json').read_text());health=json.loads((ref/'runtime-health-validation.json').read_text())
assert build['full_image_modules_dtb_build_pass'] and schema['negative_count']==7 and tests['asan_ubsan_pass'] and package['module_archive_count']==770 and health['nv6_source4_vendor1_hash_pass']
session='sessions/123-camss-dt-dma-interconnect-and-strict-disabled-validation.md'
summary='阶段123完成本机CAMSS寄存器/IRQ/SMMU资源交叉核对及隔离设备树、31bit保守DMA上限、4条ICC路径与双VFE HF AXI桥时钟请求；#123完整Image/770模块/DTB和模块包通过，严格disabled节点schema及7反例、实际C DMA 12场景通过。尚未部署，摄像头未stream，供电模型/C-PHY/QoS/IOVA下界仍待完成；最新完整软件rootfs仍122匹配121。手机保持118/DPU2/GPU1和11来源校验，完整goal active。'
doc=f'''# 阶段123：CAMSS DT、DMA/ICC与严格disabled节点校验

2026-10-12。{summary}

## 本机资源与固定参考

读取本机AndroidR源19781/sm8150-camera.dtsi，交叉核对八组资源：CSID0/1 acb3000/acba000、CSIPHY0..3 ac65000/ac66000/ac67000/ac68000，VFE0/1 acaf000/acb6000；对应IRQ464/466/477/478/479/448/465/467。尺寸分别前六0x1000、后两0x4000。IFE SMMU流ID840/860/a40/a60/c40/c60/e40/e60、每个mask620，与本机源码完全一致，不引入foreign board GPIO/sensor/固件或校准。

互联网再次读取[固定Hotdog commit47087509c4289c2580c54f5433e55366b2e00445](https://github.com/Sr-0w/hotdog-linux-bringup/tree/47087509c4289c2580c54f5433e55366b2e00445)的0055/0056/0066/0067/0075/0076，remote字节与已缓存patch逐一一致，URL/SHA见source-contract-validation.json。这里是外部作者的本地bring-up工作，不宣称它们均已合入主线。只复用经本机源核对的SoC资源及API方案，借用实机证据不等于本机通过。

新候选在E24GiB卷/home/cy122/pmos-samurai-rootfs122/camera123隔离复制121/kernel和initramfs，stage122 rootfs/tools与已验完整镜像均保留。原20GiB卷有多个候选，未再向C或其剩余空间硬塞一份kernel。访问候选同进程ensure122，schema工具仍E118/camera120/schema-venv，因此运行它之前必须先ensure118；出现一次先调用未挂载卷里的interpreter失败，已加schema-wrapper.py先挂载再exec。没有把缺失目录误判为构建数据损失。

## 设备树和数据通路改动

sm8150.dtsi增加disabled CAMSS节点：八组reg/IRQ、31个clock、IFE0/1/top三个power domain、八SMMU流和空ports。CCI保持120/121的两个disabled节点和100kHz基础，无sensor和PMIC启用。新本地qcom,sm8150-camss.yaml约束该full-IFE子集，不覆盖lite IFE/ICP。

原厂IFE IOVA从0x07400000长0xd8c00000，结束exclusive0xe0000000。参考0066的31bit DMA mask把上界收紧到0x7fffffff，本机范围证据支持这一保守上界。**DMA mask不编码0x07400000下界**，仍须核对IOMMU保留窗口/分配器；不宣称它完整表达原厂窗口，也不宣称已经解决本机无数据DMA。其他SoC原mask0xffffffff保持。

添加四条ICC：CPU→CAMERA_CFG、CAMNOC_HF0→DDR、CAMNOC_SF→DDR和内部HF0_UNCOMP→CAMNOC_UNCOMP。当前7.3 providers/IDs都存在；参考带两个interconnect参数的当前DTS格式。资源表四路径与DT名字一致，带宽采用参考bring-up表76800/2097152等kB/s，尚非本机所有分辨率/帧率的功耗调优结论。

本机CPAS确实请求GCC_CAMERA_HF_AXI_CLK。两full VFE的clock数组新增gcc_camera_axi，同时clock_rate数组增加相应零项，避免只增加名字却把后续速率错位。八套CSIPHY/CSID/VFE时钟数组长度与速率项一一匹配，所有clock名字均在经过schema校验的实际DT中。完整build通过。

## 发现校验器会掩盖disabled节点缺项

dt-doc-validate/dt-mk-schema/实际DTB dt-validate均无诊断。随后missing-icc反例却被CLI放过，主动断言阻止false-pass。读本地dtschema2026.9/dtb_validate.py，check_node明确忽略disabled节点的required/unevaluatedProperties错误，且仍exit0。这是工具既有行为，不能用退出0或空CLI日志证明disabled节点完整。

补充DTValidator.decode_dtb+iter_errors直接严格检查目标node，不走CLI的disabled过滤，并核对节点compatible防vacuous selector。实际候选严格零错误；七反例：启用缺供电、错误clock-name、缺ICC、缺一个SMMU流、缺reg、错IRQ名、多未知属性，全部严格检出。CLI因disabled规则压掉missing-icc的缺项诊断，报告明确记录；不是把这个反例改成通过。没有更改或system安装dtschema。

## 真实构建/模块与C代码验证

#123 Image SHA {build['artifacts'][0]['sha256']}，DTB SHA {build['artifacts'][1]['sha256']}，CAMSS ko SHA {build['artifacts'][2]['sha256']}。Image约59.5MB，770ko完整build，无error；vmlinux含带时间与不带时间的两个同#123 identity，记录器最初误要求唯一，已改为核对所有匹配版本均#123，不回避版本验证。

modules-k123-private.tar.gz {package['archive_bytes']}字节 SHA {package['archive_sha256']}，depmod -e -F System.map无诊断，770模块/no symlink/全部依赖在archive。与121的已验stripped模块对比，仅drivers/media/platform/qcom/camss/qcom-camss.ko变化；其余769字节相同，IPA bdd85687...保持。**这些CAMSS配置模块没有装进当前118**，即使release字符串相同也不据此认定运行兼容。

DMA测试直接抽取实际camss.c的if/else C语句，不重新实现被测逻辑；模拟4种版本×成功/-5/-12返回，共12场景，gcc Wall/Wextra/Werror+ASan/UBSan通过，原硬件DMA API用stub，仅证明分支/上界/错误返回和其他SoC行为。CAMSS没有sensor capture或真实buffer写入验收。

完整rootfs最新仍阶段122匹配**kernel121** device-fixed.simg，936包/770模块/21,134条目反向零差异及启动bundle保持。阶段123仅Image/DTB/modules候选，不把122镜像冒充123匹配rootfs。后续确定硬件可用候选后更新模块/rootfs并重复完整编码内容验收。

## 不能盲移植的供电和QoS缺口

本机四CSIPHY节点明确mipi-csi-vdd-supply=&pm8150l_l3、csi-vdd-voltage1200000，先前SM8150参考表却继承SDM845 CSID的vdda-phy/vdda-pll双供电。需要核对实际7.3驱动的regulator enable所属子模块、映射本机L3及shared供电生命周期，不能直接拿SDM845两路名字/电压填入本机板DT。当前SoC节点disabled，binding在status缺省/非disabled时要求当前资源表供电，两者均未伪造board phandle；供电模型未解决前不得enable。

QoS参考0074自行声明早期手工观测未在一致状态重现，仅有界诊断；它直接ioremap硬编码ac42000并写v175_101表。虽然本机CAMNOC MMIO有对应，但本机硬件CPAS revision/表选择、resource管理和上电时序尚未交叉证明。本轮没有盲搬该诊断。下轮查本机cam_cpas_hw.c及cpastop_v175_100/101版本选择/实际寄存器表，确认后采用device resource生命周期。C-PHY参考0089也未本轮移植，继续核对本机v1.1三相表和当前7.3接口。

PM8008四组input和冷启动地址/0x950全局enable长难项保留121记录，未猜电源/传感器寄存器。本轮按用户第4条先推进另一条实际数据通路，下一轮有界核对供电/PHY/QoS；长期资料卡住再转15组其他可自动验收项，不重复offline build来冒充硬件验收。

## 当前手机与下一轮

同boot只读SSH：#118、taint0、Phosh3492/Phoc3190原PID、DPU累计2/GPU累计1，无新增；PCM closed，双amp powered0 muted1 failed0；SLPI offline vdd/vddio0；NV6/source4/vendor1共11SHA保持。健康记录最初错误假定amp字符串格式，改为核对实际powered/muted/failed字段，原始状态并无变化。没有phone I2C/GPIO/供电事务、桌面重启、load/replay、NV/GPT/persist/分区/module写入。

保留当前118和115完整回退。下一优先修正CAMSS native analog供电模型、v1.1 C-PHY与CPAS/QoS版本表，必要时走标准内核CSID TPG验证DMA，要求真实buffer模式变化/无SMMUfault/可恢复guard；当前不得提前运行。GPU CCU翻译fault未根因解决，不能再做重负载或手工reset。user目标完整系统15组全部保持，新增C/WSL清理已在122完成实际7.26GiB回收、C约14.35GiB，无原VHD fsck/resize。继续自动flywheel，不要求人工检查、不外发消息/呼叫、不push。goal active。
'''
(root/session).write_text(doc)
for name in ['README.md','FLYWHEEL.md']:
    p=root/name;t=p.read_text();t=t.replace('[阶段122]',f'[阶段123]({session})，[阶段122]',1);t=t.replace('\n阶段122完成','\n'+summary+'\n\n阶段122完成',1);p.write_text(t)
p=root/'DOCS-INDEX.md';t=p.read_text().replace('\n',f'\n\n- [阶段123：CAMSS DT/DMA/ICC与strict disabled校验]({session})：本机资源交叉、#123离线候选、真实C12场景与schema7反例；未部署。\n',1);p.write_text(t)
p=root/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text().replace('阶段122）','阶段123）',1);t=t.replace('15组硬件保持。','15组硬件保持。 '+summary,1);t+='\n阶段123：本机CAMSS八MMIO/IRQ/SMMU匹配，disabled DT+DMA31bit上界/4ICC/HF bridge隔离候选构建验收完成，硬件摄像头仍未stream。供电模型本机L3 1.2V与借用SDM845双路模型不一致待修；C-PHY/QoS/IOVA下界保持开放。最新完整rootfs122仍匹配121，当前手机118未变。\n';p.write_text(t)
p=root/'NEXT-SESSION.md';t=p.read_text().replace('阶段122（2026-10-12）','阶段123（2026-10-12）',1);t=t.replace('完整系统goal active。','完整系统goal active。 '+summary,1);t=t.replace('先读[阶段122]',f'先读[阶段123]({session})、[阶段122]',1)
t+='\n阶段123最新：候选/source/modules在E122卷/home/cy122/pmos-samurai-rootfs122/camera123（同进程ensure122），schema interpreter在E118/camera120/schema-venv（先ensure118，使用123/schema-wrapper.py）。完整build Image2212b4fb88bca8049732fc9cb0ef80a8b50a0e9a5d786eac5a0bcefb2ce0d6ba，DTB8f36f0708a7ae2013961042ff7d908253a58a998a6231808939b0b2a1f136242，770模块包90711e72cfbde31c2baef44f3252f6e439ea8da031426d4f095c27574b85708c。仅CAMSS ko变化769其余相同，未部署/未生成rootfs123；最新完整软件bundle122匹配121继续保留。disabled CAMSS DT实际strict validator过7反例，不只CLI，因为dtschema跳过disabled missing-required；实际C DMA12场景pass仅hoststub。下一优先本机四PHY pm8150l_l3 1.2V与借用SDM845双供电差异（修正resource regulator生命周期再enable），v1.1 C-PHY表和CPAS175_100/101选择/QoS资源管理；IOVA下界0x7400000未由31bit mask编码。0074参考自己标记不可复现的诊断，不盲写QoS地址；PM8008四输入/冷启动地址仍长难留档。当前手机118/taint0/原GUI PID/DPU2/GPU1/11校验未变。不要重跑123 prepare/port/package一次性脚本或旧122writer覆盖后续记录。\n';p.write_text(t)
print('CHECKPOINT123_CAMSS_PATH_VALIDATED_OFFLINE_GOAL_ACTIVE')
