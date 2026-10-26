# FLOAT +合法native额度的最小候选

本目录独占、纯离线。未访问手机/SDK/PMIC，未改main、共享内核、现有provider或加载器；没有执行模块卸载/加载、重启或写寄存器。这里只交源码候选、受影响测试与准确来源。

## 解决的实际样本

根会话连续三次只读确认：原生raw额度100000有效、UDC configured、保护Good、无锁存，但PMIC为 `apsd=0x21 result=0x10 plugin=0x10 cc=8 attached=0x23 misc=0x2b legacy=6`。旧decoder把exact FLOAT保持Unknown/ENODATA，即使native回调已有效，因此charger waiting_source。这里的configured单独不授权；候选还必须用已有provider保存的合法valid native回调。

已冻结候选 `samurai-usb-input-decode.h` SHA256：

`a17caa2cbeb2352da249474e0265fa96745f544d96a29d0ebe8f14c656d548fd`

补丁 `float-only.patch` SHA256：

`a91b9eef154b882483272d977b9bc393456959ac1cb617aab0eca0463fef8f8a`

基准header为55a947826821267c4e90d8291ded852ce34dba1658e3d4e8f487f41373fc25b0；provider C的b712764fbd4ab24475ae1ba030ee4c26c7eb048a6038488a5435b44ef7eb7098原样，详见manifest.json。patch只针对header，不能覆盖其它版本而不先核hash。

## 有依据的原厂行为和限制

同机原厂 [smb5-lib.c](https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source/blob/9668fcdc6ec15be7a10d66f7b93c347829e0fdb6/drivers/power/supply/qcom/smb5-lib.c) 固定9668fcdc6ec15be7a10d66f7b93c347829e0fdb6，缓存SHA5203488026f12fddc65ca899f16c8eb461e0da08dc151c4c5be18501204342a8，已与本地bare git show对象逐hash核实。

- SMB5寄存器头225–244：APSD DONE=bit0，QC_CHARGER=bit1，QC_AUTH_DONE=bit2，VADP_CHANGE_DONE_AFTER_AUTH=bit3，ENUMERATION_DONE=bit4，SLOW_PLUGIN_TIMEOUT=bit5；result FLOAT=bit4（0x10）、QC2/3为bit5/6。故本次0x21是DONE+slow-plugin timeout，不能因其数值含0x20就误当QC结果位。
- `smblib_handle_usb_current`4031–4087：real type为USB_FLOAT时，USB栈给出的普通请求电流会转real_charger_type=USB，投USB_PSY_VOTER，取消SW_ICL_MAX。4116–4141的`smblib_set_prop_sdp_current_max`入口只在非PD且USB present时调用该处理；PD active走独立分支。
- 5888–5900明确FLOAT在USB stack检测完成前以100mA为边界，不随Rp变化直接增流。候选采用更严格的无valid native则ENODATA/停充；不自行给默认100。
- 必须保留原厂条件：APSD表582–590的VENDOR_EDIT分支实际上把FLOAT映射DCP，而非USB_FLOAT；因此不能声称上述USB_FLOAT分支在原厂vendor编译必经，也不把这种DCP高额度映射搬来。这里复用的是USB栈可消解FLOAT歧义、按其额度工作的机制，而非字面复制全部vendor策略。
- OEM还包含`usb_current == -ETIMEDOUT`时按float_cfg设USB500或按Rp/DCP增流的路径；候选**不采用**这些兜底，也不写FORCE_FLOAT_SDP配置或任何PMIC位。

这份原厂来源是同机早期下游固定提交，与AndroidR23172…充电策略来源分开记载。

## 最小实现

1. 在enum尾追加仅内部的FLOAT标识，旧枚举值不动；provider的USB类型转换已有default Unknown，无需改provider C。
2. 保留全部原有效域/附着/水或角色/异常CC/QC拒绝。对**完整raw result恰为0x10**、DONE且没有reserved/QC-auth相关状态的样本先输出FLOAT、额度ENODATA；其分支在Type-C Rp额度前，避免FLOAT先被1.5/3A覆盖。SLOW_PLUGIN_TIMEOUT不单独当错误，实际0x21可用。
3. apply_udc只把online FLOAT在已有valid且0≤native≤500000时转为SDP，额度逐值照用；0和2000保持0/2mA，charger原有50mA最低工作门槛会停充。无valid、负数、500001或900000等保持不可用。普通未知、多重result、QC均不会凭native额度转正。
4. 非FLOAT的SDP/CDP/DCP/Type-C行为不改；尤其CDP仍1500000，未被native100压低。

独立PD状态的边界必须说清：当前七字段结构没有pd_active，不能声称它能识别任意“旧APSD FLOAT、PD已另行active”的组合。候选不识别或授予PD合同、不引入PD高额度，沿用当前无PD适配契约及合法DWC≤500mA条件。若上层已独立知道PD active，必须继续拒绝该路径；本次不扩PD字段、不增加硬件读取。QC bit/result/auth/未知raw的可观察拒绝已测试。

## 验证

test-result.json：12,768项候选核心断言、14项原厂完整函数fake边界，均以ASan/UBSan和-Wall/-Wextra/-Werror通过；私有原header副本patch --dry-run通过。

覆盖实际0x21/0x10+native100解析、0/2mA、全部APSD byte与result byte、CC域、输入错误/附着异常、非法native范围、无native、FLOAT不走Rp高额度以及原SDP/CDP/DCP回归。`oem-functions.inc`为4031与4116两个完整实函数抽取，vote/USB-present读仅fake；证明原厂控制流，未执行PMIC写入。原厂timeout升级分支仅在fake中展示并明确不移植。

这是软件验证，不能代替新boot后的真实source/充电/拔插验收；当前三次现场状态是根会话证据，本代理未接触设备。

## provider生命周期及加载路径

当前provider 226–245因boot DT的native DWC消费而`__module_get(THIS_MODULE)`；DWC3持有其power_supply引用和callback至控制器生命周期结束。模块自持和供电对象引用共同决定不能正常热卸。没有发现可靠现成的provider replacement/reprobe流程：即使不rmmod，只unbind provider也会拆除被DWC使用的供电对象/私有数据，并非合法替换捷径。不能强卸、改内存、建立同名重复provider或新增永驻shim。

根会话选择的合法路径是：独立增量构建USB ko，将**磁盘USB ko与相应manifest**两文件受控更新，保留原Image，协调一次正常重启让旧引用自然终结；随后重建新boot guard及四服务/相机基线。所有设备/重启/加载器工作由根会话另行执行，本目录未做。这里的manifest.json仅记录源码候选hash，不能冒充实际ko部署manifest。

## udc_valid暂态清除是另一个问题

provider C67–83在paused或任何ret/!online时清udc_valid；EAGAIN/临时传输错误也会丢先前回调，若以后没有新native事件可能持续等源。resume也主动清标志。该竞争需要独立设计新鲜度、真实detach及PM次序，不能靠本FLOAT修正悄悄保留旧额度。**本候选完全没有改这些语句、锁或生命周期。**

当前FLOAT旧分支本身返回0且online=1，所以仅修该已证分类缺口不要求顺手改暂态竞争；若新boot后出现ret导致valid丢失，须按独立问题取证和处理。
