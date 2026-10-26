from pathlib import Path
import json
r=Path('/mnt/e/RealmeX2Pro edk2')
ref=r/'reference/kernel135'
load=lambda name:json.loads((ref/name).read_text())
failure=load('failed-runtime-validation.json')
rollback=load('rollback-runtime-validation.json')
health=load('rollback-health-validation.json')
bundle=load('complete-bundle-validation.json')
stable=load('stable-rollback-bundle-validation.json')
host=load('host-volume-validation.json')
assert failure['candidate_rejected'] and rollback['kernel_build']==132 and rollback['taint']==0
assert health['fault_increments_zero'] and stable['matching_stable_four_artifact_hashes_fresh_verified']
assert host['all_four_private_volumes_unmounted_and_offline_readonly_fsck_zero']
session='135-mdss-reset-candidate-rejected-and-stable132-rollback.md'
assert not (r/'sessions'/session).exists()
summary=('阶段135完成MDSS reset候选的909节点单属性静态/schema验证、UEFI仅DT替换及真实双分区部署；实际新boot虽无原CTL/KMS失败，却WCD934x告警、DSI两处clock告警、682次codec ENOSPC、taint512且无Phosh，候选拒绝，根因未证明。'
         '已自动回退#132并逐项验核boot/logdump/live DT/GPT18/persist/770模块/11来源；原配置Phosh/Phoc与BlueZ/5180MHz自主恢复、taint0，无需面板重绑或greetd标记恢复。'
         '42.512秒8次被动守卫同PID/供电0/BlueZ/Wi-Fi及故障计数保持，boot累计DPU2/UART4/GPU0；CRTC active0，持续显示和GPU131迟发fault仍未验收。'
         '当前匹配完整镜像为rootfs132；最新候选rootfs134及770模块原字节复用/四件套重新完整hash和encoded UID10000读写通过，候选135不能作为稳定基线，userdata未全量刷入。'
         '134 USB额度驱动在当前132回退内核暂不存在，历史CDP1.5A证据保留；MP2650只读观测仍自动注册，实际充电控制继续待办。'
         '找到当前缺失的上游WCD934x regmap/irqchip清理补丁，下一项独立源码补丁/构建/实际部署，不能据此宣称efuse/ENOSPC根因已证实。15组硬件与完整系统goal active。')
body=f'''# 阶段135：MDSS复位候选拒绝、真实回退及音频新线索

2026-10-12。上一goal轮实际搜索并核对同Adreno640的CCU故障记录，没有产生新设备改动；本轮形成独立DT候选、真实部署、失败证据和已验证回退，为progress。所有工作自动完成，无人工检查步骤，完整系统目标未完成。

{summary}

## 候选与实际失败

当前134源码已有 native msm_mdss_reset：optional exclusive reset在MDSS初始化前assert/20ms/deassert。实际SM8150 provider是dispcc-sm8250.c，两份header CORE_BCR=0、map0x2000、#reset-cells=1；binding已允许单个MDSS_CORE reset。互联网主线源码/SDM630原作者补丁与原厂固定提交核对见[检索记录](../reference/kernel135/display-internet-findings.md)。

只增加 `&mdss {{ resets = <&dispcc DISP_CC_MDSS_CORE_BCR>; }};`，完整909节点仅一个属性变化，前后schema零诊断；隔离生成DT，原134源/Image/DTB/modules保持。UEFI其余执行模块与实际134逐字节相同，canonical原源码和build FV/FD/boot全部恢复。

新鲜134前置GPT18/11来源/persist/模块/当前boot通过。停GUI/无线/ADSP/trace、DRM空闲，冻结后仅一次F1转换，原生fastboot核对identity/product/geometry后写boot/logdump均OKAY。软件banner仍134，DT变体135，不能伪称新kernel135。新boot完整DT与分区读回证明候选真实生效。

候选新boot：CTL shutdown/KMS init错误0，但WCD934x efuse probe WARN1、DSI provider注册clock disable WARN1/unprepare WARN1、codec ENOSPC682，taint512；connector connected/card1/renderD128，但Phosh/Phoc缺失，DPU timeout2。完整失败归档SHA {failure['archive_sha256']}，全成员校验、NV/GPT/persist、770模块和GUI三配置保持。原CTL故障本次未出现不能证明缺reset是根因，候选拒绝，没有加startup重绑循环或删日志。

## 回退与验证边界

按该失败boot身份和taint512专用守卫停止全部GUI/无线/ADSP、amp idle、SLPI offline/供电0、trace0、DRM clients0/CRTC inactive，归档验核后再冻结；一个新F1转换写回保留132的boot/logdump，旧132模块完整校验。没有重放此前F1/flash步骤或擦userdata。

132新boot自动恢复原Phosh/Phoc/BlueZ/5180MHz，taint0、codec/clock/WARN为0；全live DT、boot/logdump SHA、GPT18/persist、11来源、匹配770模块/console5:1 root0600通过。首份采集较早，后续自主启动到齐再取final，未服务重启、panel bind或greetd标记操作。final CRTC active0、inactive4，DPU累计2/GPU0，因此保留原active gate失败日志，回退报告仅验进程/源码/分区/无新增WARN恢复，明确full display acceptance=false；不能把这次回退称为永久显示修复。

42.512秒8份Wi-Fi/PID/taint/BlueZ/SLPI供电守卫和前后dmesg证明各类故障增量0，累计UART reassembly4、DPU2、GPU0。未施加GPU负载，不关闭GPU131迟发故障。健康脚本仅最后大文件source hash的10秒观察上限失败，原现场保留；只补未完成checksum/finalize阶段（90秒上限），不重跑采样。8次ADC值当时在内存而未持久化，故不编造电压/电流序列；仅保存1份最终MP2650标准uevent/ONLINE1和11来源校验。

## 完整rootfs、存储及下一项

候选135复用同软件代134的完整936包/770模块rootfs：其boot目录无独立Image/DTB，核对encoded export的root0:0/0755、UID10000降权create/read/write/unlink、原无线profile/BlueZ，并对四件套全文件重新SHA；兼容性完整不等于失败boot可部署为稳定系统。rootfs134仍1817957988字节/SHAa7d3b11b17d83e72361937dcb8ce2daf3078e52beb4d86f2bc603a9d260bb2ff，21,137项metadata/双fsck历史证据和新fresh hash相互对应。

当前运行132的匹配完整四件套也逐个fresh SHA通过（stable-rollback-bundle-validation.json）。最新候选rootfs134保存，当前132不含新134只读USB source额度驱动，旧CDP1.5A测试不等于本boot有此接口；后续恢复该功能必须形成新候选并实测。MP2650输入观测保持，完整充电控制、保护/NTC/失联仍待补；0x2719为电量计扩展标识。

本轮C/E空间重新检查，四个E私有卷sync/卸载/离线只读fsck均0，稳定126卷保持未挂载，原WSL VHD不resize/compact。134已证明旧对象/重复raw和exports的清理成果保留，本轮未删除仍需解释的135失败证据或稳定源码/镜像。

web搜索服务两次连接失败后用Exa继续实际检索WCD934x efuse/SLIMbus/ENOSPC。找到[原作者资源清理补丁](https://lkml.rescloud.iu.edu/hypermail/linux/kernel/2603.1/03387.html)，本地MFD还用devm irqchip、失败不清理regmap、DOWN仅移除children；固定4源文件和邮件SHA已存next-audio-source-validation。下一项是该真实缺口的独立补丁/构建/部署与启动/stop-start守卫，仍须核对SLIM TX slot/transaction泄漏与首个DMA错误，不能仅隐藏WARN或将cleanup当作本次efuse根因。

GPU稳定、持续显示、物理camera/PM8008/HAL、GNSS真实fix、SIM通话/数据、指纹/IMU/休眠、蓝牙配对/传输等15组边界保持。私有身份/UUID/地址/凭据/完整日志/源码镜像仅E:/edk2-samurai-out或phone /var/lib/samurai。

所有一次性prepare/build/collect/quiesce/freeze/F1/flash/rollback/health/resume/close已终态，禁止重放。capture-postflash-eud在endpoint尚未枚举时guard退出，未attach/OUT/reset；后SSH自主恢复，不重发com-up。第一次新boot collector因/tmp被重启清空而未执行，重新传入脚本后只执行一次真正采集；首次SCP rollback archive路径拼写错误也未改变设备。
'''
(r/'sessions'/session).write_text(body)
for name in ['README.md','FLYWHEEL.md']:
    p=r/name
    first,rest=p.read_text().split('\n',1)
    p.write_text(first+'\n\n'+summary+'\n\n[阶段135](sessions/'+session+')。以下更早内容是历史，以当前132回退与135失败边界为准。\n'+rest)
p=r/'DOCS-INDEX.md'
first,rest=p.read_text().split('\n',1)
p.write_text(first+'\n\n- [阶段135](sessions/'+session+')：MDSS复位候选实际失败与132自动回退、完整镜像复用/匹配基线、音频资源清理新线索。\n'+rest)
(r/'NEXT-SESSION.md').write_text(f'''# Realme X2 Pro继续检查点（阶段135，2026-10-12）

{summary}

先读[阶段135](sessions/{session})、failed-runtime-validation.json、rollback-runtime-validation.json、rollback-health-validation.json、stable-rollback-bundle-validation.json和next-audio-source-validation.json。完整系统goal active，自动搜索/源码/反编译/补齐rootfs与硬件；静态通过后真实部署验核，长错留档换项，无人工步骤。

当前真实内核#132，release7.3.0-rc6-rmx1931-samurai-k132+，物理DRM card1/minor1。当前boot身份只用E:/edk2-samurai-out/kernel135/embedded-boot-id-private.txt或phone k135-rollback132-final/boot-id-private.txt；135 source-boot-id是旧134，failed-boot-id是拒绝候选boot，均不是当前身份。Phosh/Phoc、BlueZ/5180MHz自主恢复、taint0，CRTC inactive/DPU2/UART4/GPU0并不证明长稳。

下一项核对当前缺失的上游WCD934x MFD regmap/irqchip cleanup，路径/固定source hash/已下载邮件见next-audio-source-validation；形成独立136源码补丁，继续核对SLIM TX ring slot与首个DMA错误，完整构建/模块/DT/rootfs后实际部署。不要将cleanup或增加MDSS reset当作已证明efuse/ENOSPC根因，也不要重复135失败DT候选。

当前匹配rootfs132四件套保留并fresh全hash通过；最新候选rootfs134为936包/770模块/21,137条目encoded检查/UID10000读写，135仅DT变体复用134软件与完整镜像。userdata未全量刷入。135 MDSS reset boot候选拒绝，不能用作稳定基线；134 USB source额度功能在当前132内核不存在，CDP1.5A历史实测保存，后续独立恢复且真实验核。MP2650只读观测在线，完整充电控制/保护继续待办。

E118/129/122/134四卷已关闭/离线fsck0，E126仍关闭。依赖操作同一WSL调用先ensure，不能依赖旧/run状态。E134 usb134/kernel原源和134 DT/Image未修改，可用于136候选；E118 power132与稳定120/121源、E129 rootfs132/134/export134及其rawpair、C128/129稳定源码保持；134已证明删除的旧.o/重复raw/exports不要重建或重放清理。

全部135一次性工具已执行且终态，72830 close已终态成功，不要重放；不要依据观察超时重启任务。公开审计覆盖135与当前15组状态。新的真实boot必须新日志目录与身份守卫，F1一次/每次boot转换、freeze前排空音频/无线/DRM与trace。私有标识/凭据/raw日志/镜像只在E:/edk2-samurai-out及phone /var/lib/samurai。

GPU131两次迟发CCU、DPU持续显示、物理camera、GNSS真实fix、蜂窝/SIM/通话、指纹/IMU/休眠等全scope保持；不重跑旧33场景或全局GPU debug。
''')
p=r/'linux-port/docs/HARDWARE-STATUS.md'
text=p.read_text()
first,rest=text.split('\n',1)
text='# RMX1931 Linux 硬件接入清单（2026-10-12，阶段135）\n\n'+summary+'\n\n[阶段135](../../sessions/'+session+')。旧轮次是历史，当前以132回退与135候选失败为准。\n'+rest
rows={
'原生显示面板': '| 原生显示面板 | 135 MDSS reset真实候选拒绝；回退#132原Phosh/Phoc自主恢复、taint0/card1，DPU2/CRTC inactive | 首次自动启动未验收到完整显示，CTL交接/持续绘制/休眠及GPU迟发fault继续；不能称永久修复 |',
'普通USB与OTG': '| 普通USB与OTG | 135候选及132回退均冻结/F1/boot+logdump实际写回；当前132 NCM/SSH/SCP与GPT/persist通过 | 134 CDP/1.5A只读接口历史通过但当前132无该驱动；OTG/USB3/休眠/冷启动/长稳待办 |',
'音频': '| 音频 | 135候选WCD efuse WARN/682 ENOSPC失败；132回退无WARN/ENOSPC、PCM closed/amps idle，历史UCM/DMIC电气证据保留 | 缺失的MFD regmap/irqchip清理上游补丁待实现验核，efuse/SLIM根因未证；音质/耳机/校准/休眠待办 |',
'电池与充电': '| 电池与充电 | 当前132 MP2650永久只读观测ONLINE1；134历史USB额度8/8 CDP1.5A，当前回退无此新驱动；135仅1份最终ADC事件持久化 | 后续恢复标准USB source额度；0x2719为电量计扩展标识，保护/NTC/失联/实际充电控制继续待办 |',
'蓝牙': '| 蓝牙 | 历史BlueZ5.87两组LE/BR/EDR/混合扫描通过；135回退132自动BlueZ running，42.5秒共存保持 | 当前boot UART reassembly累计4仍未修，配对/传输、物理冷启动/休眠/长稳待办 |'
}
lines=text.splitlines()
for i,line in enumerate(lines):
    for name,row in rows.items():
        if line.startswith('| '+name+' |'):
            lines[i]=row
p.write_text('\n'.join(lines)+'\n')
print('K135_FAILED_CANDIDATE_ACTUAL132_ROLLBACK_AND_15_GROUP_SCOPE_DOCUMENTED',flush=True)
