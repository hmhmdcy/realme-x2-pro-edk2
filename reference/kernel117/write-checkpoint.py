from pathlib import Path
import json
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel117';out=Path('/mnt/e/edk2-samurai-out/kernel117')
r=json.loads((ref/'display-recovery-validation.json').read_text())
assert r['phosh_running'] and r['pcm_closed'] and r['amps_idle'] and r['taint']==0
parser=dict(binary_source='same_handset_sensormodule_bins',public_parser_commit='9f17f1b568626b393e785b369c5dc94543774d7a',
 parser_version='2.0.0',bin_parser_version='1.3.2',private_libxml2_runtime_built=True,no_system_library_replacement=True,
 source_layout_include_error_corrected=True,sensor_driver_data_decode_cpu_limit_hit=True,usable_xml_files=0,
 reverse_schema_not_accepted=True,own_generated_library_not_found=True,physical_camera_not_touched=True,goal_complete=False)
(ref/'parser-boundary-validation.json').write_text(json.dumps(parser,indent=2)+'\n')
link='sessions/117-parser-boundaries-and-same-boot-desktop-recovery.md'
intro='''阶段117在同一次#115启动中恢复DRM、Phosh/Phoc与FD640 GLES2：只对已失败/无owner的本机面板做一次有界重新探测，然后重触发现有greetd initial_session；没有重启、刷分区或改登录配置。taint0，45秒窗口无新增DPU/GPU故障，累计仍有1次DPU超时；PCM closed/双功放静音、SLPI offline/供电0、trace off、NV6/source4/vendor/persist保持。启动RCU/CTL reset回归与GMU重复探测EBUSY仍开放，不认定永久显示修复。
'''
session='''# 阶段117：解析边界与同启动恢复桌面

2026-10-12。完整系统goal active；继续无人值守，无人工画面/触摸/听音要求。

'''+intro+'''
## 摄像头二进制解析：有界失败后转项

在阶段116本机五sensor.so/六sensormodule BIN来源基础上，网络找到[BANG QTI结构解析器](https://github.com/armijnhemel/binaryanalysis-ng/tree/master/src/bang/parsers/misc/qti_chromatix)及[CamxChi](https://github.com/bjzhou/CamxChi)的公开工具/XSD。GitHub API遇403 rate limit，改用公开浅克隆/固定commit/raw文件，没有使用账户凭据。BANG固定96370e4f07fa0173f32c049b9523d03c98f748d2，只校验header，不声称能解完整寄存器。CamxChi固定9f17f1b568626b393e785b369c5dc94543774d7a，ParameterParser ELF未strip并包含BinaryFileFormat符号、x命令可用-b从BIN生成XML，输入需要创建BIN时的XSD。

工具V2.0.0依赖libxml2.so.2，当前主机仅libxml2.so.16。使用[GNOME官方2.9.14源码](https://download.gnome.org/sources/libxml2/2.9/)，下载hash核验，非root构建到/home/cy122/x2pro-linux/parser-k117/runtime，通过私有LD_LIBRARY_PATH启动工具；没有全局安装或替换系统库。源码/schema/tool及log均保持私有。现有BIN标记Parameter Parser V1.3.2，工具是否能完整兼容尚未验证。

第一轮30秒未生成XML。8秒strace显示读取sensorDriverData时持续分配，且扁平XSD路径造成flashdriver ../sensor include失败；修正为原api/sensor布局后include已全部解析，仍在sensorDriverData处达到8秒CPU限制，0个XML。配置256MiB地址空间、8秒CPU、32MiB输出上限，并终止/等待独立进程组；没有遗留parser进程。没有对未完成输出做roundtrip或声称已获得寄存器/供电序列。

本机只读探查libcamxgenerated*.so无匹配；保留camx库metadata，卸载vendor，没有盲目复制其它大库。对应生成代码可能静态链接到HAL，但尚未证实；后续可以读取实际HAL ELF符号或寻找同版本schema。当前这条解析路线先记录转项，不能向传感器写猜测字段。只读SoC CAMSS/CCI参考0056/0057已固定同Hotdog commit，外国板级补丁未应用。

## 同一次启动恢复DRM和桌面

阶段115第三启动因启动CTL_SW_RESET超时(-22)无/dev/dri。当前boot身份、#115/taint0、无Phosh/Phoc、无DRM、未绑定面板、OF_COMPATIBLE=samsung,sofef03f-m及bind路径核验后，执行一次20秒有界panel-samsung-sofef03f bind。返回0，card0/renderD128、面板driver和GMU firmware加载恢复，DRM初始化通过。没有reset/重启/刷机，也没有绕过IOMMU前quiescence guard。

greetd restart先只到Phrog登录界面/Phoc；既有initial_session之前失败后/run/greetd.run标记保留。读取实际/etc/greetd/samurai-phosh.toml，确认现有cy122 initial_session和wrapper；停止greeter、确认Phoc退出、备份空marker/原配置，只删除该runtime marker，启动greetd。原initial_session正常启动Phosh/Phoc，配置hash前后一致，不新建登录策略或改密码。Phoc最新log为Mesa/freedreno/FD640。

恢复时有一次enc35 frame done timeout；之后45秒观察窗口无新增DPU超时/无GPU fault、taint0。累计仍1次DPU超时，不能认定稳定性修复。重复component bind还记录GMU资源0x0b290000 EBUSY，虽继续加载firmware/硬件GLES2，仍需审查失败bind的资源生命周期，不安装无条件自动循环reprobe服务。

全成员hash校验通过：panel归档26726dceabd52a488de3a16a99655040f0f46f282ca34dc9a5743c175691d4f1；session归档36d554669258dab792859f8e21e228d97cb252d0e30ba2f0b25abc61bb4c3590；最终45秒健康归档e70624486b789264a218e4d3cf215e2fca949a8f74f339255a09bcee5b3f7fa7。三份身份一致，boot/logdump/persist hash保持，NV6/source4通过，PCM closed/双功放powered0 muted1，SLPI offline/sensor-power0、display/radio trace0，Wi-Fi up、zram、ModemManager sim-missing保持。最后额外vendor原hash复核通过，桌面进程仍存在。

## 显示源码新证据和下一步

当前dpu_hw_ctl_poll_reset_status每轮先读SW_RESET，再usleep_range(20,50)，然后检查2,000us期限；期限到期后返回睡眠前读到的status，没有最后一次读取。如果线程实际睡眠跨过期限，而硬件期间已完成reset，就可能误报超时。重新探测时没有再出现boot CTL清空日志且初始化通过，说明到那时继承状态已清空；这支持有延迟完成的方向，但不证明睡眠前旧值是所有回归根因。

准备下一隔离候选只修正poll结束后读取真实reset bit，仍在bit1未清时返回错误，保留全部IOMMU前quiescence/stalled-mask检查。不能增加无条件成功或删除warning。候选需完整build、115基线/DTB/模块ABI核验，再用当前已恢复第三启动的新排空/freeze/F1守卫部署；当前rootfs115 fixed与kernel116未部署CAMSS候选保持。

15组状态、GNSS真实fix、完整传感器、摄像头、指纹、蜂窝数据/通话、充电、休眠和長稳继续开放。rootfs115软件镜像已校验，未全量刷入。所有身份/固件/BIN/原始日志保持私有，未发送消息/呼叫，无GPT/NV/persist写入，无erase、无文档push。
'''
(root/link).write_text(session)
for name in ['README.md','FLYWHEEL.md']:
    p=root/name;t=p.read_text();start=t.index('[阶段116]');end=t.index('\nUnofficial EDK2',start) if name=='README.md' else t.index('\n> 2026-10-08',start)
    new=f'[阶段117]({link})，[阶段116摄像头基础](sessions/116-camss-foundation-and-own-sensor-binaries.md)，[继续检查点](NEXT-SESSION.md)。\n\n'+intro
    new+='\n软件rootfs115 fixed镜像1,817,970,276字节、936包/764模块/本机IPA固件、zram/elogind修复，展开比对/双fsck通过，尚未刷入。隔离#116 CAMSS基础完整构建通过、未部署；本机sensor BIN解析在有界工具窗口未完成，不能称摄像头可用。\n'
    if name=='FLYWHEEL.md':new+='\nF1前仍要当前boot完整排空GUI/音频/功放/ADSP/无线/MPSS、NV核验、sync与fsfreeze回执。当前桌面已恢复，不能套用无GUI脚本或115旧boot守卫。不使用erase userdata的旧全量刷机脚本更新应用。\n'
    p.write_text(t[:start]+new+t[end:])
p=root/'NEXT-SESSION.md';t=p.read_text();t=t.replace('# 继续检查点：阶段116','# 继续检查点：阶段117',1)
start=t.index('先读[');end=t.index('\nSLPI offline',start)
new=f'''先读[阶段117]({link})、[阶段116](sessions/116-camss-foundation-and-own-sensor-binaries.md)、[115部署](sessions/115-own-ipa-modem-and-zram-rootfs.md)、[15组](linux-port/docs/HARDWARE-STATUS.md)，当前健康依据reference/kernel117/display-recovery-validation.json。

当前手机仍第三次#115启动，taint0，DRM/card0/renderD128、Phosh/Phoc、最新FD640 GLES2、Wi-Fi、IPA/MM(sim-missing)、zram已恢复。一次有界失败面板reprobe恢复DRM；重触发既有greetd initial_session恢复Phosh，登录配置hash不变。没有新重启或刷机。恢复后累计1次DPU超时，后续45秒无新增DPU/GPU fault。之前两次启动RCU/CTL reset -22历史仍开放，GMU重复bind EBUSY也需审查，不能认定永久显示修复或安装无条件reprobe循环。
'''
t=t[:start]+new+t[end:]
t+='\n阶段117主机解析工具/XSD来源固定，私有libxml2.so.2 runtime已构建，无全局安装；旧BIN1.3.2与工具2.0.0/schema兼容未验收。修正include后仍sensorDriverData读取达到CPU8秒限制，0 XML，进程已退出。lib64无libcamxgenerated*.so匹配，HAL静态生成代码尚未定位。记录后转显示源码：poll reset现有2ms循环在usleep之后到期，返回旧status，缺最终读；下一隔离候选加最终SW_RESET真实读，bit未清仍失败，全部quiescence/stalled mask guard保持。CAMSS/CCI SoC DT0056/0057已取得固定来源，仍不启用摄像头。\n'
p.write_text(t)
p=root/'DOCS-INDEX.md';t=p.read_text().replace('当前：[阶段116](sessions/116-camss-foundation-and-own-sensor-binaries.md)',f'当前：[阶段117]({link})、[阶段116](sessions/116-camss-foundation-and-own-sensor-binaries.md)',1)
t=t.replace('| 文件 | 内容 |\n|---|---|','| 文件 | 内容 |\n|---|---|\n| '+link+'、reference/kernel117/ | 有界BIN解析失败边界、同boot面板reprobe与既有initial_session恢复、45秒健康/CTL旧状态返回源码证据 |',1);p.write_text(t)
p=root/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text();start=t.index('[阶段116]');end=t.index('| 功能组',start)
t=t[:start]+f'[阶段117](../../{link})，[继续检查点](../../NEXT-SESSION.md)。\n\n'+intro+'\n'+t[end:]
t=t.replace('2026-10-12，阶段116','2026-10-12，阶段117',1)
t=t.replace('首个#115启动桌面存在；随后两次启动CTL reset -22，无DRM/Phosh/Phoc；RCU stall保留','第三次#115启动中有界panel reprobe+既有initial_session恢复DRM/Phosh；累计DPU1次，随后45秒0新增；RCU/CTL -22历史保留')
t=t.replace('历史FD640硬件GLES2/故障保留；当前DPU bind失败未启动GPU桌面，0 fault不能算通过','恢复后最新Phoc为freedreno/FD640，taint0/0 GPU fault；重复bind GMU资源EBUSY保留')
t=t.replace('先恢复DRM，然后GPU/压缩帧缓冲/应用压力/休眠/長稳','审查失败bind资源生命周期、GPU/压缩帧缓冲/应用压力/休眠/长稳')
t=t.replace('当前ADSP/card0运行，PCM closed双功放静音','恢复桌面后ADSP/card0运行，PCM closed双功放静音')
t=t.replace('BIN寄存器/供电parser、CCI/CAMCC、C-PHY/DMA/ICC/QoS及本机模组，ISP/图像数据流未验收','BIN parser有界失败/0 XML，匹配schema或HAL生成代码、CCI/CAMCC/C-PHY/DMA/ICC/QoS，物理未验收')
p.write_text(t)
print('CHECKPOINT117_DOCUMENTED_PARSER_STALL_SWITCH_AND_VERIFIED_DESKTOP_RECOVERY')
