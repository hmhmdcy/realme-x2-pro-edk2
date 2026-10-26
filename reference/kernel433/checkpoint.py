"""Keep the full camera goal and distinguish built ACK hooks from live proof."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
for n in ['transport','driver','source','intree-build']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed']
archive=ROOT/'archive/NEXT-SESSION-through432-2026-10-22.md'
if not archive.exists():archive.write_bytes((ROOT/'NEXT-SESSION.md').read_bytes())
(ROOT/'NEXT-SESSION.md').write_text('''# 当前检查点：433（IFE GTM typed参数、PIX ACK与SOF回执驱动候选）

完整多摄／ISP目标active。先读WORKING-BOUNDARIES、reference/kernel433/README.md；432数学、431实拍证据继承。433完成原厂提交契约/驱动候选/实际函数离线检查/匹配模块构建，未访问手机、未加载候选、未新增实拍、未接生产IPA。不能把ACK回调代码当硬件生效证明。

## 当前源码与产物

kernel source354 HEAD04f8c5a3c815e2fa4244564da108227561a0321b，branch samurai-vfe175-gtm-ack433，parent431 52127e55，clean。10文件patch，SoC GTM新c/h+UAPI+pixel+17x+vfe+video buffer/Makefile，板级DT/传感器/电源不变。r1构建后补整包重复GTM拒绝，r2才是最终候选：十匹配模块W1/Werror诊断0，共享outputs/config/symvers恢复。

private kernel433 qcom-camss-intree-r2.ko2934680B SHA88e7c6ae9cd1e4bb81c807fecc584a2dfba1e671400e0418622d45fcd1f51c17。core439608B/d391fa24和m2m141624B/e6828a0c与431相同。source-validation查真实GTM/ACK符号、hash、patch零fuzz/offset、build恢复。新UAPI/缓冲结构要用匹配CAMSS候选，不混未核模块。

## GTM提交和驱动

原IFEGTM Create31f7f0/Execute31fc00完整执行7次：3更新、hold、锁定、前摄禁用、显式注入DMI失败。成功GTMCFG794/DMIcfgc24/selectors24→25→24/LUT512B/offset56，全部LUT等于432原数学。enable颜色bit2。失败原HAL仍切“下次bank”但未发布enable，不把失败算生效。原选中对象fixture、transport recorder，平台fixture，未送硬件。

复用296生成头+官方Realme GPL CDM commit9668fcdc，原cam_cdm_util_swd_dmi_write实执行确认CPU DMI64低字c30→高字c2c，不用HW-CDM word swap。GTM LUT bank与IPE DC平均值表bank不同。

新实验参数type9/536B：flags0/cookie非零/enabled0或1/reserved0/64段unsigned18base+signed26slope；disable也全payload。非法整包拒绝，重复GTM块拒绝。填非活动bank，显式index，恢复DMI config/address/CGC，发布bank/enable。状态在真实PIX REG_UPDATE ACK才active并增generation；新实验统计type3/32B cookie/generation/status/bank来自每缓冲SOF快照，晚完成不读当前状态。无GTM配置旧调用不加统计块。

参数DQ仅写入提交，不称生效。首个含GTM及随后tracked参数若旧PIX RUP未退则保留原队列；ACK清旧更新/提交armed状态/取下一参数并发新RUP。新cookie不冒认旧ACK。17x IRQ原顺序ACK先于SOF。stop清GTM状态，迟到ACK不跨开流。

实际gtm驱动、vfe_params_apply_next、17x reg_update/clear/ACK/SOF函数在host ASAN/UBSAN与ARM64各9原厂LUT夹具通过；每LUT200非法字段/flags/短包检查。64项inactive bank、共享状态、官方GPL DMI全trace、旧ACK、未armed、排队、late stats旧snapshot、disable ACK、stop等通过。IRQ/MMIO是模拟，未物理验证。官方oracle原signed-bitfield warning仅该外部函数局部屏蔽，内核Werror不屏蔽。

## 继承证据

432：45GTM roots/45叶子/26字段90标量，独立BIN→OEM XML→本机HAL Parse2085f0逐字节一致，464B序列化→360B运行时，192B类+88为payload。原完整TMC11四摄12调用，后三摄9有效GTM，前摄保持禁用。portable model2主机/ARM64各27例零差异，另12 native selector/swap/bank组合。private axes/coeff/ASM。未全移植legacy/manual/v2/TMC10。

生产用户候选仍/mnt/samurai-full282/libcamera431-pd10-auto/src/libcamera-v0.7.2 build7/IPA4未改。最近实拍431 r4普通/隔离主摄各24，48自动双遍48最终历史提交+旁路/DC切换4job，正式模块/服务/媒体图/资源恢复，无新fault、taint0，worker/client终态。正式420r31/r26、419core/adapter、Image363/DT389，未永久安装；432/433未刷新健康。

DC RT type2→context0→bank0，粗级DC1/IP0/sumclear1，全尺寸DC0/IP1/clear0同bank；430/431调度修复、重复性与真实PD10功能消费保留。片内整表未读回，a7 scratch不是统计。429曾自加越界readl Oops已删除诊断，用户硬重启后四摄恢复；危险429build2 core da4591...禁止加载，不猜新MMIO地址。

## 下一步

准备当前typedGTM/统计回执的有界手机probe，验证真实LUT功能影响、两个bank、CPU低高字顺序、真实RUP ACK→SOF→对应图像/统计，停流及正式环境恢复。优先复用428/430/431 reversible worker、原guard、图恢复fixture；不要无故重跑全矩阵或重建未改组件。

然后生产IPA原厂选择/数学→IFE下发→实际回执cookie绑定immutable TMC/ADRC→对应图像IPE/LTM→最终成功history。统计N只改后续IFE，不能M统计逆因果称M上游已生效；IFE已ACK物理状态与IPE成功历史分开，IPE失败不能伪回滚IFE。保持非零GTM份额、前摄禁用/缺统计hold/失败历史。其它摄像头/尺寸/视频/第五2MP/光学/多摄同步仍363清单，画质仍雾感偏色未验收。

WSL每次source/build/ext4先root storage284.mounted_build，原32GiB盘不重建。Unicorn PYTHONPATH14，host433继承429新guard与原key/known_hosts。当前本地build/exec终态，无远端worker。本轮原件仅private kernel433；public_module导出/scoped本地commit，保留mirror无关index和3处工作树，不push。此前详细状态在archive through432及431/432README。
''')
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从433继续完整多摄/ISP目标：GTM type9/536B、DMI64 canonical低c30→高c2c、真实PIX ACK+每缓冲SOF快照回执type3/32B已接驱动候选。kernel HEAD04f8c5a3c clean/branch samurai-vfe175-gtm-ack433，r2匹配十模块W1/Werror0，CAMSS88e7c6ae…，core/m2m同431；未加载、未访问手机、未新增实拍、未接生产IPA。下一步有界实机验证LUT/bank/ACK/SOF/对应图像统计与恢复，再生产IPA真实cookie绑定immutable TMC/ADRC和最终history。原IFE完整Execute7例，actual驱动/queue/arm/ACK/SOF host/ARM各9原厂LUT+200非法/例，均离线，不得称硬件通过。432原厂45 roots及model2数学host/ARM各27例保留；431真实PD10自动双遍48实拍48提交仍最新实机证据，正式环境已恢复、当时taint0。原GTM非零份额不清零，IFE已ACK物理版本与IPE成功历史分开，不能M统计倒称M上游已生效。先读NEXT/433README/WORKING-BOUNDARIES；storage284先挂原盘、429新guard、原件私存、不猜MMIO、scoped提交。\n')
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
 p=ROOT/rel;d=json.loads(p.read_text());d.update(stage=433,latest_work_stage=433,latest_work_phone_accessed=False,last_live_hardware_evidence_stage=431,ipe_gtm_typed_ife_driver_candidate=True,ipe_gtm_pix_ack_sof_driver_candidate=True,ipe_gtm_driver_hardware_verified=False,ipe_gtm_model2_production_ipa_integrated=False,ipe_gtm_hardware_application_verified=False,ipe_gtm_applied_version_math_history_association_verified=False,ipe_full_factory_tone_pipeline_complete=False,in_progress_installed=False)
 if '/kernel/' in rel:d.update(maintained_branch='samurai-vfe175-gtm-ack433',maintained_commit='04f8c5a3c815e2fa4244564da108227561a0321b')
 p.write_text(json.dumps(d,indent=2)+'\n')
note='433当前：原厂IFE GTM提交契约已执行验证，typed GTM与PIX更新ACK/SOF快照接入驱动候选，匹配模块及主机/ARM64实际函数检查通过。候选尚未加载、未接生产IPA、本轮无实拍；最新实机仍431真实PD10自动双遍48帧48提交。'
for rel,link in [('linux-port/camera/README.md','../../reference/kernel433/README.md'),('linux-port/camera/kernel/README.md','../../../reference/kernel433/README.md'),('linux-port/docs/HARDWARE-STATUS.md','../../reference/kernel433/README.md')]:
 p=ROOT/rel;first,rest=p.read_text().split('\n\n',1);assert first.startswith(('432当前：','433当前：'));p.write_text(note+'[433证据]('+link+')。以下为历史。\n\n'+rest)
p=ROOT/'DOCS-INDEX.md';t=p.read_text();old='[432 原厂GTM与TMC11数值链路](reference/kernel432/README.md)';new='[433 IFE GTM与ACK/SOF驱动候选](reference/kernel433/README.md)';assert old in t or new in t;p.write_text(t.replace(old,new))
print(json.dumps(dict(stage=433,next_bytes=(ROOT/'NEXT-SESSION.md').stat().st_size,full_goal_complete=False,passed=True)))
