from pathlib import Path
import json,re
root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel113'
report=json.loads((ref/'checkpoint-validation.json').read_text())
checks=report['checkpoints']
latest=next(checks[name] for name in ['desktop-after-ram-census14.tar']+[f'desktop-after-ram-v{i}.tar' for i in range(17,4,-1)] if name in checks)
v7=checks.get('sensor-ram-v7.tar')
new_result=(f"RAM v7实机扩展MID31/33成功，{v7['ram_writes']}次真实RAM写入、{v7['ram_renames']}次rename，daemon运行{v7['daemon_seconds']}秒至有界TERM退出143，无I2C fatal；两次accel查询254、无实际样本。"
            if v7 else '新RAM试验尚未验收。')
if 'sensor-ram-v8.tar' in checks:
    prox=json.loads((ref/'proximity-v8-validation.json').read_text())
    assert prox['real_sample_received'] and not prox['cover_uncover_verified']
    new_result+=' RAM v8新启动150秒试验同样完成240次RAM写入和204次rename、无I2C fatal，60秒后及第二轮accel仍254，光线/磁力计254；Sensortek STK3331接近传感器首次真实报告1个FAR样本、正常禁用，遮挡变化未验收。'
if 'proximity' in report:
    prox=report['proximity']
    assert prox['proximity_function_accepted']
    new_result+=f" RAM v9用户实际遮挡/移开，{prox['sample_count']}个样本/{prox['state_changes']}次NEAR/FAR变化，接近传感器实机通过；用户同时确认画面和操作正常。转储尚未取得，前置守卫退出的试验原档案保留，供电/SLPI收尾通过。"
if 'slow_boot_regression' in report:
    new_result+=' 第五次重启出现WCD934x/SLIMbus DMA错误和taint512，实际回到Phosh但音频门槛失败；先排空用户音频、停止ADSP/无线后，第六次正常重启恢复taint0及DPU/GPU故障0。该回归及原始失败证据保留，关机清理尚需重复验证。'
if 'sensor-ram-v10.tar' in checks:
    new_result+=' v10在触发前被已有DPU显示转储挡住，未触发DSP崩溃；显示转储已私有保存，试验收尾offline/供电0/taint0。v11改为按failing_device只选择SLPI。'
if 'reboot-audio-clean-7.tar' in checks:
    reboot=json.loads((ref/'reboot-audio-clean-7-validation.json').read_text())
    new_result+=f" 重复完整音频/ADSP排空后，第七次正常重启taint0、GPU故障{reboot['gpu_faults']}、DPU超时{reboot['dpu_timeouts']}；音频慢启动未复现，显示问题继续保留。"
if 'sensor-ram-v11.tar' in checks:
    trial=checks['sensor-ram-v11.tar']
    new_result+=f" v11转储捕获={trial['slpi_coredump_captured']}，收尾offline/供电0/taint0；加速度查询{trial['query_exit']}。"
if 'slpi_ulog_v11' in report:
    ulog=report['slpi_ulog_v11']
    new_result+=f" 实际SLPI转储按本机原厂ELF的VA/PA段映射解码，匹配代码块{ulog['original_code_blocks_matched']}个、有效ULog {ulog['valid_ulog_count']}个；未借用其它设备地址或固件。"
if 'physical_after_ram_v11' in report:
    new_result+=' 用户确认第七次重启/v11后解锁显示正常，并要求减少重复画面问题；后续优先自动日志核对，出现新故障或需要实物操作时再询问。'
if 'reboot-audio-clean-8.tar' in checks:
    new_result+=' 第八次完整音频/ADSP清理正常重启恢复taint0，启动快照DPU/GPU故障0；已补采USB重新枚举后的EUD日志。'
if 'slpi_ulog_v12' in report:
    new_result+=' v12无SSC查询、daemon启动3秒后取得早期转储，保留I2C_QUP_DDR与SPI_QUP_DDR在/icb/arbiter创建失败的错误4；这使问题范围缩小，但固件与配置不匹配尚未证明。'
if 'magnetometer_v13' in report:
    mag=report['magnetometer_v13']
    new_result+=f" 第九次正常重启taint0、启动DPU/GPU故障0。C28本机00098固件仅在单独Linux只读目录试验，MMC5603X磁力计取得{mag['sample_count']}个样本/{mag['unique_vectors']}个不同三轴μT向量；方向矩阵全0警告及旋转/准确度尚未验收。接近/加速度/光线254，不能整套替换00121。试验后恢复原firmware选择、SLPI offline/供电0/taint0，原SLPI文件逐字节保持。"
if 'magnetometer_v14' in report:
    mag=report['magnetometer_v14']
    new_result+=f" 第十次正常重启taint0；C28 v14取得{mag['sample_count']}样本/{mag['unique_vectors']}不同向量，最大方向分离{mag['maximum_vector_direction_separation_degrees']}度。用户完成转动，但指出可能超出60秒窗口，因此旋转响应未验收；不能把静置噪声认作响应。C35参考包已离线比较并在独立Linux目录暂存，尚未启动该固件。"
if 'reboot-audio-clean-11.tar' in checks:
    new_result+=' 第十一次完整音频/ADSP清理正常重启已核验新boot、taint0和NV/来源保持。'
if 'magnetometer_v15' in report:
    mag=report['magnetometer_v15']
    new_result+=f" C28 v15延长至180秒，{mag['sample_count']}样本/{mag['unique_vectors']}不同向量；窗口内转动确认={mag['physical_rotation_within_sampling_window_confirmed']}，旋转响应验收={mag['physical_rotation_response_verified']}。方向矩阵和指南针准确度仍待查。"
if 'sensors_v16_validation' in report:
    trial=report['sensors_v16_validation']
    new_result+=f" 第十二次新启动C35 v16磁力计取得{trial['sensors']['magnetometer']['sample_count']}样本；接近/加速度/光线/陀螺仪/compass查询均254。C35仍保留SPI初始化客户端失败，不能提供完整传感器方案。供电/SLPI/原selector收尾通过，默认未改变。"
if (ref/'lsm6ds3c-config-comparison.json').exists():
    new_result+=' 同机型Lineage18配置参考的10个真实文件经Git blob哈希核验；LSM6DS3C总线/IRQ/电源14项与原配置及实际RAM v7一致，简单的SPI实例/IRQ/电源配置错误暂不受支持。未更改本机配置或校准。'
if 'sensors_v17_validation' in report:
    trial=report['sensors_v17_validation']
    assert trial['syntax_escape_alone_did_not_enable_magnetometer']
    new_result+=' 第十三次正常重启和RAM v17已核验：只把原磁力计JSON字符串中的一个TAB转为\\t，解码配置值不变；原00121仍只取得STK3331接近1样本，其余五种查询254。这个语法修正未解决磁力计枚举，SPI npa客户端失败仍存在。51个ULog按原MDT及19个代码块校验，5013条完整解码；桌面/网络/时钟/音频空闲及收尾通过。'
if (ref/'audio-quiesce-12-validation.json').exists():
    new_result+=' boot12关机准备曾因ADSP停止超过15秒退出143；随后独立核验三个DSP全部offline、原生声卡注销、功放静音/供电0/taint0，再归档并正常重启。保留中断与失败读PCM的空文件，不把不存在的节点认作PCM样本。'
if 'passive_after_v17' in report:
    passive=report['passive_after_v17']
    new_result+=f" boot13在{passive['uptime_seconds']/60:.1f}分钟后的只读复核仍taint0、DPU超时{passive['dpu_timeouts']}/GPU故障{passive['gpu_faults']}、Phosh进程存在；未追加物理确认，显示长稳仍未验收。"
if 'npa_own_firmware' in report:
    new_result+=' 本机00121/v17反汇编及运行时ICB表核对完成：16表示字节，即两对master/slave；客户端类型0x400受支持，错误4确为缺路由。表内68路径/12 master/33 slave，所请求的39/41→0均不存在；但SPI失败走正常返回，I2C同样NULL仍取得STK3331样本，不能把这条日志作为传感器未实例化的根因。下一步转向本机SSC注册/实例化和完整SUID事件。'
if 'ssc_census14' in report:
    new_result+=' 第十四次正常启动及census14已核验：全量/默认各32次请求、64帧、32个SUID事件，全部成功且Google Protobuf独立解码相符。accel/gyro/mag/ambient_light两组均无SUID，proximity均1，六项CLI对照仍仅STK3331取得1样本；默认过滤不足以解释四项缺失。空类型全量目录13 UID需继续按属性识别，不能把匿名条目认作物理传感器。转储51个ULog/5168条、19代码块映射通过，收尾offline/供电0/taint0、桌面回归通过。'
status=f'''当前部署Linux #113及匹配的boot内嵌DTB；postmarketOS/Nura edge与Phosh继续运行在已有userdata F2FS。用户确认113首次供电试验后画面稳定、解锁和应用正常。最近一次完整桌面检查（boot14、并非当前显示回归现场）DPU超时{latest['dpu_timeouts']}、GPU故障{latest['gpu_faults']}、taint0；111滚动花屏历史与显示长稳仍保留。

USB NCM/密钥SSH、2.4GHz NetworkManager Wi-Fi、HTTPS/NTP、桌面UCM/空闲PCM/功放关闭通过。113完整停止无线服务后的正常重启恢复；EFI关机运行时异常依旧，不能将其等同于重启卡死。boot/logdump、live DT节点属性、NV6/来源4/persist保持，userdata不重刷。

113按本机原厂19781 SSC代码加入L7C/L8C手动供电消费者，默认不启用，只允许SLPI offline时切换。RAM v5/v6实际开启、测试、关闭通过，短窗未复现112的I2C崩溃；仍无加速度样本。v6发现wire方法31实际是扩展MID入口，守护进程10.13秒即因缓冲布局不符退出，退出码0不能算健康。新分派/真实RAM rename已通过ASan/UBSan；实机新结果以聚合检查点为准，不提前记传感器通过。

完整适配目标尚未完成。15组硬件继续保留，摄像头、指纹、GNSS、蜂窝通话/数据、休眠和长期稳定尚未验收。私人身份、凭据、固件、校准、原始日志、录音和镜像仅存私有输出，不公开、不提交推送。
'''
link='[阶段113](sessions/113-sensor-power-and-extended-rpc.md)，[继续检查点](NEXT-SESSION.md)。\n\n'
status=status.replace('实机新结果以聚合检查点为准，不提前记传感器通过。',new_result)
if 'ssc_attributes15' in report:
    status+='\nboot15属性枚举已完成：10个SUID查询、15个属性查询与响应、50个QMI帧经独立Google Protobuf解码一致。发现Sensortek stk_stk2x3x以wise_light（physical/available=true）注册；ambient_light为空不能再解释为光线硬件完全未注册。真实lux样本未验收；原00121下仍无accel/gyro/mag条目。51 ULog/5113记录与19代码块映射通过，原selector/offline/供电0/试验末态taint0、源4/NV6保持。\n'
if 'display_regression15' in report:
    status='''当前优先修复boot15新花屏闪烁。用户触发条件未知，显示会话恢复后确认画面稳定；永久修复未验收。boot15在传感器试验开始前已有1次DPU超时，原现场累计3次，不能归因于SLPI。首次greetd重启在fbcon仍保持输出时新增drm_crtc_wait_one_vblank WARN，taint升至512；该失败保留。恢复原Phosh、运行时解绑fbcon后仍新增1次DPU超时，累计5次/GPU故障0。正常锁屏截图只证明当时软件图像，不替代面板实测。当前SLPI offline/供电0，显示恢复与后续时序试验以各档案为准。

'''+status
scope='''2026-10-12用户最新约束：后续只运行自动化调试，不要求用户做人工画面、触摸、遮挡、转动或听音检查；此类验收留待用户恢复参与。继续互联网/源码仓库/本机反汇编取证，补齐完整postmarketOS rootfs镜像和缺失功能。长时间无可验证进展的问题更新证据后转到下一项，不反复等待人工反馈。最新要求为先更新文档并完成本轮收尾；完整系统尚未完成，rootfs新镜像尚未交付。

'''
if 'current_user_scope' in report: status=scope+status
if 'display_clock15b' in report:
    status+='\n原生DRM时序对照15b实际完成3×140次翻页：371MHz原速率、约1.107GHz原厂接近速率、返回原速率；均保持1080×2400@60和原DSC。测试跟踪窗口内425次帧完成、DPU/PP超时0；恢复Phosh后新增2次DPU超时，不能说升频修复。原生缓冲为普通格式，Phosh为QCOM压缩格式；这仅形成待验证假设。\n'
if 'display_linear15_failed' in report:
    result=report['display_linear15_failed']
    status+=f"\nWLR_DRM_NO_MODIFIERS试验退出1，未确认选项进入Phoc，未得到线性缓冲证据；原启动脚本逐字节恢复。回滚后累计DPU{result['total_dpu_timeouts']}、GPU故障{result['gpu_faults']}、taint{result['taint_after']}，新GPU故障不隐去。显示问题继续待办；不作为稳定系统验收。\n"
if 'display_idle_restored15' in report:
    status+='\nbringup临时idle-delay=0已经恢复原值60秒，锁屏策略保持。\n'
if 'wrap_up15' in report:
    status+='\n本轮收尾完成：GPU故障日志及最终现场日志私有归档；GPU devcoredump曾可见323,539字节，采集前已消失，未取得转储二进制。初次核验发现原display已耗尽snapshot触发器仍保留一个事件；补充收尾解除该触发器，原快照SHA保持，最终五个诊断trace实例停止且事件全部关闭。SLPI offline、传感器供电0、原00121 selector和启动脚本恢复，NV6/source4保持、空闲PCM关闭/双功放静音、Phosh进程及F2FS rw核验。未新增刷机或rootfs镜像。\n'
    final=report['wrap_up15']
    current=f"最新状态：本轮文档和收尾已完成，仍运行#113/boot15及已有userdata F2FS/Phosh。DPU累计{final['total_dpu_timeouts']}次、GPU故障{final['gpu_faults']}次、taint{final['taint_after']}，显示/GPU问题未解决；用户画面恢复确认早于后续试验。诊断trace/事件已全部关闭，临时idle-delay恢复60秒，原启动脚本/SLPI选择恢复；没有新增rootfs镜像、刷机或重启。以下保留早期阶段和本轮证据各自的状态范围。\n\n"
    status=scope+current+'''本轮自动化结果：原00121固件已枚举wise_light/Sensortek stk_stk2x3x物理光线条目，15个属性响应经独立解码核验；真实lux及自动亮度未验收，accel/gyro/mag仍无条目。STK3331遮挡变化和C28 MMC5603X窗口内转动的既有证据保持，两版功能不能合并认作一个完整系统。

显示取证：原回归在传感器试验前已有DPU超时；会话重启的fb_helper/vblank WARN使taint变为512。原生DRM三轮共420翻页，约371/1107/371MHz测试窗口均无超时，恢复Phosh后却新增2次超时，升频未获修复验收。禁用modifier试验退出1、未确认Phoc环境或线性缓冲，原launcher逐字节回滚；随后记录GPU故障。用户画面恢复确认只覆盖更早的恢复阶段。

本轮收尾：GPU故障日志、dmesg、display/radio trace与snapshot私有归档；GPU devcoredump曾可见323,539字节，采集前已消失，未取得二进制。原display已耗尽snapshot触发器解除后，快照SHA保持；最终五个诊断trace实例停止、事件全部关闭。SLPI offline、传感器供电0、原selector和启动脚本恢复，idle-delay恢复60秒；NV6/source4保持、PCM关闭、双功放静音，Phosh/Phoc/greetd及F2FS rw核验。fbcon bind=0为本boot运行时设置，taint512尚未通过新启动清除，本轮未再重启或刷机。

15组硬件状态保持。显示/GPU稳定性、光线采样、加速度/陀螺仪、原00121磁力计、摄像头、指纹、GNSS、蜂窝通话/数据、休眠等仍待验收；完整rootfs新镜像尚未交付。私人身份、凭据、固件、校准、原始日志、录音和镜像保留在私有输出，未公开、提交或推送。
'''
path=root/'README.md'; text=path.read_text(); start=text.index('Unofficial EDK2/UEFI port')
path.write_text(text.split('\n',1)[0]+'\n\n'+link+status+'\n'+text[start:])
path=root/'FLYWHEEL.md'; text=path.read_text(); start=text.index('> 2026-10-08')
procedure='''持久F2FS重启使用kernel109/reboot-pmos-persistent.sh及kernel113/observe-radio-clean-reboot.ps1，前缀必须跨历史阶段唯一，当前bootID/SLPI offline/手动供电0引用守卫通过后停止GUI/NM/WPA/BT/ath10k/MPSS、核验NV、sync、OpenRC正常关机。每个EUD owner在finally关闭并detach，先释放再com-up，SSH恢复后核对新boot和原始日志。

F1需当前启动F2FS同步/冻结或只读卸载证明；旧启动关机日志不能复用。113首次刷机取得成功freeze及F1回执，再独立fastboot识别和分区大小检查，仅刷boot/logdump。flash-pmos.ps1会erase userdata，不用于更新；旧110救援DTB不匹配113。回退113之前需成套使用111 boot与112 logdump，不混用内嵌DTB。

'''
path.write_text(text.split('\n',1)[0]+'\n\n'+link+status+'\n'+procedure+text[start:])
path=root/'linux-port/docs/HARDWARE-STATUS.md'; text=path.read_text(); tail=text[text.index('| 功能组 |'):]
replacements={
'触摸':'| 触摸 | 用户确认113供电试验后Phosh解锁及应用正常 | 方向/边缘/休眠/长稳 |',
'原生显示面板':f'| 原生显示面板 | 113实际解锁应用正常；最新桌面DPU超时{latest["dpu_timeouts"]} | 111滚动花屏记录；首次接管/休眠/纯白光学/长稳 |',
'GPU':f'| GPU | FD640硬件GLES2 Phosh；最新GPU故障{latest["gpu_faults"]}/taint0 | 应用压力/休眠/长稳 |',
'普通USB与OTG':'| 普通USB与OTG | NCM/SSH/SCP与EUD共存；113完整正常重启恢复，boot/logdump实机哈希通过 | 直接重启失败历史；OTG/USB3/休眠/长稳 |',
'其它传感器':'| 其它传感器 | 原厂19781 L7/L8顺序供电及收尾通过；扩展MID/240次写入/204次rename；STK3331真实1个FAR样本 | 接近遮挡变化未验收；加速度/光线/磁力计仍无SUID；陀螺仪等待查 |'}
lines=tail.splitlines()
for i,line in enumerate(lines):
    for name,value in replacements.items():
        if line.startswith('| '+name+' |'): lines[i]=value
if 'proximity' in report:
    lines=[('| 其它传感器 | STK3331接近：用户遮挡/移开，37样本36次NEAR/FAR切换通过；供电/真实RAM写入rename收尾通过 | 加速度/光线/磁力计无SUID；陀螺仪与休眠未验收 |' if line.startswith('| 其它传感器 |') else line) for line in lines]
if 'magnetometer_v13' in report:
    lines=[('| 其它传感器 | 原始00121下STK3331遮挡切换通过；本机C28 00098对照下MMC5603X磁力计50个真实向量样本 | 两版功能不能合并认定；磁力计矩阵/旋转/准确度未验收；加速度/光线/陀螺仪仍待办 |' if line.startswith('| 其它传感器 |') else line) for line in lines]
if 'magnetometer_v14' in report:
    mag=report.get('magnetometer_v15',report['magnetometer_v14'])
    response='窗口内转动响应通过' if mag['physical_rotation_response_verified'] else '窗口内转动响应待验收'
    lines=[(f"| 其它传感器 | 原始00121下STK3331遮挡切换通过；C28 00098下MMC5603X {mag['sample_count']}个真实样本，{response} | 两版功能不能合并认定；磁力计矩阵/准确度、加速度/光线/陀螺仪仍待办 |" if line.startswith('| 其它传感器 |') else line) for line in lines]
if 'ssc_attributes15' in report:
    lines=[(line.replace('磁力计矩阵/准确度、加速度/光线/陀螺仪仍待办','磁力计矩阵/准确度、加速度/陀螺仪待办；wise_light物理光线条目已枚举，lux采样未验收') if line.startswith('| 其它传感器 |') else line) for line in lines]
if 'display_regression15' in report:
    lines=[('| 原生显示面板 | boot15新花屏已复现，用户确认会话恢复后稳定；DPU累计5次，旧快照保留 | 永久修复、休眠、纯白光学、长稳未验收 |' if line.startswith('| 原生显示面板 |') else
           '| GPU | FD640硬件GLES2 Phosh；boot15 GPU故障0；显示重启后DRM WARN导致taint512 | 应用压力、休眠、长稳；正常截图不能验收面板 |' if line.startswith('| GPU |') else line) for line in lines]
if 'display_linear15_failed' in report:
    result=report['display_linear15_failed']
    lines=[(f"| 原生显示面板 | boot15新花屏回归保留，DPU累计{result['total_dpu_timeouts']}；用户在后续试验前确认恢复稳定 | 永久修复/休眠/长稳未验收；人工检查暂缓 |" if line.startswith('| 原生显示面板 |') else
           f"| GPU | FD640硬件GLES2，boot15已记录{result['gpu_faults']}次GPU故障、taint{result['taint_after']}；原生翻页对照窗口通过 | 新GPU故障/压缩帧缓冲/应用压力/休眠/长稳 |" if line.startswith('| GPU |') else line) for line in lines]
path.write_text('# RMX1931 Linux 硬件接入清单（2026-10-12，session113）\n\n15组硬件保持。\n\n'+status+'\n'+'\n'.join(lines)+'\n')
(root/'NEXT-SESSION.md').write_text('''# 继续：113手动传感器供电与扩展FastRPC

先读[阶段113](sessions/113-sensor-power-and-extended-rpc.md)、[硬件状态](linux-port/docs/HARDWARE-STATUS.md)、[聚合核验](reference/kernel113/checkpoint-validation.json)。完整适配目标尚未完成，本轮按用户要求更新文档并收尾。

手机已刷113 boot/logdump，userdata F2FS沿用109持久Phosh，不执行flash-pmos.ps1。113内核/DTB/内嵌DTB匹配，供电默认0引用、SLPI auto_boot false。用户确认113首次RAM v5试验后画面稳定、解锁应用正常；之后正常重启/新试验的物理状态不能冒称已经再次确认。每个档案的DPU/GPU计数独立，花屏长期稳定未完成。

原厂本机Android R仓库commit23172a1571bd91156032cc9fef16284a82b63d2c的19781 SSC明确使用L7C VDD、10ms、L8C IO，113只增加手动消费者。切换持有rproc lock且只允许offline；保持资源与NV/校准来源只读。试验真实写入/rename仅在/run私有tmpfs副本，绝不写persist/vendor。供电引用不等同于物理电压测量。

v5/v6短窗无112 I2C崩溃但未出现accel；v6诊断确认wire31/sc1f030000被误作stat拒绝，daemon约10.13秒返回0是上游忽略listener失败。上游8fd3b22说明wire31的首DWORD是扩展MID；已实现受边界验证的分派和方法33 RAM rename，实际handler/alias/readback/RO/traversal/symlink/directory/NULL与ASan/UBSan通过。静态hexagonrpcd-v5私有暂存，未替换系统包或自动启动。v7/v8分别新boot有界90/150秒，240次写入204次rename、无I2C fatal。v8发现Sensortek STK3331接近传感器、真实1个FAR样本；遮挡变化未验收。加速度/光线/磁力计查询254，仍无SUID。

1. 用109 SSH/SCP包装器检查当前uname/taint0/bootID、SLPI offline、/sys/devices/platform/sensor-power/state引用0；SCP远端带root@169.254.42.1:。先查看113私有新档案与当前phone checkpoint，不要重放旧boot守卫。
2. 113首次刷机源bootID为112第二次正常重启，首次113为k113-first-before-slpi。已验证三次113正常重启；当前k113-reboot-radio-clean-3用于v8，试验已结束，SLPI offline、供电0、taint0。SLPI同boot再次启动曾超时，测试一轮后走完整正常重启再试，不反复原地启动。prefix必须跨阶段唯一；radio-clean-2在109历史路径已存在，安全守卫拒绝，改用k113-radio-clean-2。
3. 日常重启用113 observe-radio-clean-reboot.ps1及phone k113-tools/reboot-radio-clean.sh（109完整关机helper）；先taint0/SLPI offline/供电0，停止无线/MPSS、NV检查、sync、OpenRC重启。EUD reader45秒/每owner finally释放，待300秒root发现，不暂时无SSH就F1。F1前独立取得当前rw根成功冻结或只读卸载证据；旧112历史F1恢复脚本封禁。
4. 源码/home/cy122/pmos-samurai-kernel113/{kernel,initramfs}与隔离的/home/cy122/hexagonrpc-v04-k112。规范EDK2目录恢复109原产物，手机当前boot为113；113私有完整回退是111 boot +112 logdump。只做匹配候选，不能混用内嵌DTB。六LUN/GPT18、persist/NV6/source4边界持续核验。
5. 继续15组硬件：显示/重启长稳、5GHz、传感器真实样本、摄像头、指纹、GNSS、蜂窝通话数据和休眠。蓝牙不配对、振动不发脉冲、NFC仅控制器、充电探针已收尾。GPIO和NV不得盲写。

私人凭据/PIN/SSID/PSK/身份/固件/校准/原始日志/镜像存E:/edk2-samurai-out，不公开、不提交推送。正确PIN私有文件有一个8位数字，不能把整个三行文本当PIN扫描。旧109/112更新文档脚本会回写旧状态，不用于当前记录。
''')
print('KERNEL113_CURRENT_STATUS_AND_CONTINUATION_SAVED; 15 HARDWARE GROUPS PRESERVED')
if 'proximity' in report:
    path=root/'NEXT-SESSION.md'
    text=path.read_text()
    text=text.replace('已验证三次113正常重启；当前k113-reboot-radio-clean-3用于v8，试验已结束','已验证四次113正常重启；k113-reboot-radio-clean-4用于v9，试验已结束')
    text+='\nRAM v9实测接近STK3331通过：用户完成遮挡移开且确认画面操作正常，37样本/36次NEAR/FAR变化，末态FAR。转储触发前守卫退出1，原档案保留；v10准备在daemon仍运行时捕获并逐项保存守卫，不重放旧boot。当前下一轮boot与结果需读取新档案核实。\n'
    if 'slow_boot_regression' in report:
        text+='\n第五次重启 slow-boot-radio-clean-5 为taint512/WCD934x efuse WARN，SLIM DMA准备31次失败/682个ENOSPC，不能记硬件通过。audio-radio-quiesce-5确实排空用户进程、PCM关闭/功放静音、停止ADSP和无线，NV6/source4保持；第六次 reboot-audio-clean-6 已核验新boot/taint0/分区及DTB匹配。当前下一轮RAM v10以第六次boot为守卫，结果以私有新档案为准，不能用旧reboot-radio-clean-5（该路径未创建）。\n'
    if 'sensor-ram-v10.tar' in checks:
        text+='\nv10已经结束：现存devcd1来源为DPU显示控制器，全设备转储为空的守卫退出，未触发SLPI crash；display-dump-after-v10.tar保留真实显示转储，desktop-after-ram-v10保留DPU超时2。不要重放v10。\n'
    if 'reboot-audio-clean-7.tar' in checks:
        text+='\n当前启动检查点为k113-reboot-audio-clean-7；第七次正常重启已核验taint0、分区/DTB匹配和NV/source保持。v11只按SLPI设备来源筛选转储，已暂存手机k113-tools。是否完成试验及DSP解码必须读取sensor-ram-v11/ulog-v11最新档案；同boot不能反复启动SLPI。\n'
    if 'sensor-ram-v11.tar' in checks:
        text+='\nv11已经结束并取得20,871,615字节SLPI ELF，收尾offline/供电0/taint0。51个ULog按本机固件段映射校验19个代码块后解码；SPI npa客户端失败、NPA早期记录已滚出，不能直接归因。v12准备在daemon启动3秒、无SSC查询时获取早期转储，必须使用新的reboot-audio-clean-8检查点。用户已确认v11后解锁显示正常，并要求减少重复显示问题。\n'
    if 'sensor-ram-v12.tar' in checks:
        text+='\n当前phone checkpoint为k113-reboot-audio-clean-8。v12已完成早期转储并收尾offline/供电0/taint0；daemon运行4.15秒，主动debug crash后EPIPE返回0，不能算长期健康。ULog确认两个QUP_DDR客户端错误4；参考本机原始SLPI.HY.2.2-00121与维护者RMX1931 Chinese C28包进行离线版本/段映射比较。下载包只供选取SLPI资料，绝不执行整包刷机脚本或改NV/原厂分区。是否下载/准备/实际测试新固件必须查看最新c28-reference档案。\n'
    if 'sensor-ram-v13.tar' in checks:
        text+='\n最新phone checkpoint为k113-reboot-audio-clean-9；第九次正常重启已核验，C28 v13已结束并恢复原始00121选择，SLPI offline/供电0/taint0。C28 00098确实得到MMC5603X磁力计50样本48个不同向量、正常禁用，但方向矩阵全0；接近/加速度/光线254。参考magnetometer-v13-validation/ulog-v13-validation，不能把两版分别通过的硬件合并成一个可用系统。当前无自动SLPI服务，后续需新启动再试。\n'
    if 'sensor-ram-v14.tar' in checks:
        text+='\n更新：phone checkpoint k113-reboot-audio-clean-10；v14 C28磁力计60秒采样302样本258不同向量、最大方向变化1.5度，用户转动可能晚于窗口，响应未通过。用户明确要求重试，v15改为同固件180秒窗口/新boot11守卫，C35比较保留为v16/新boot12。不能重放当前boot SLPI试验。C35已在samurai-c35-trial单独只读Linux目录暂存，不覆盖原文件；默认selector仍为原始00121。\n'
    if 'reboot-audio-clean-11.tar' in checks:
        text+='\n最新启动守卫为k113-reboot-audio-clean-11，核验taint0。v15结果/收尾及用户操作时机以最新档案为准；准备文件不等于已经完成试验。\n'
    if 'magnetometer_v15' in report:
        mag=report['magnetometer_v15']
        text+=f"\nv15已完成：磁力计{mag['sample_count']}样本；窗口内转动确认={mag['physical_rotation_within_sampling_window_confirmed']}，响应通过={mag['physical_rotation_response_verified']}。原firmware selector恢复、SLPI offline/供电0/taint0；指南针准确度仍未接受。\n"
    if 'sensors_v16_validation' in report:
        text+='\n最新phone checkpoint为k113-reboot-audio-clean-12；C35 v16已完成，磁力计50样本，接近/加速度/光线/陀螺仪/compass均254，SPI客户端错误仍存在。固件自身MDT/19个代码块映射解码通过；收尾SLPI offline/供电0/taint0、原00121 selector恢复。C28 v15用户窗口内转动通过的证据保留；不能据此说C35旋转已验证。下一步比较同机型C38 vendor参考与本机原始配置，只作私有离线分析，不能导入他人persist校准。\n'
    if (ref/'lsm6ds3c-config-comparison.json').exists():
        text+='\n参考进展：C38 LFS真实对象未取得（REST 403、media断开、LFS有界120秒超时），不能把指针当配置。另取cyyyss/vendor_realme_RMX1931 lineage-18.1固定b94e26044cb95092add5dd8026fab0fdcb61433a的10个真实配置/声明文件，Git blob哈希通过。与当前合并版文件结构不同，但LSM6DS3C的总线/SPI2/IRQ132/电源14项与本机原配置和实际RAM v7完全一致，SoC339筛选均匹配。暂未支持简单bus/IRQ/rail选择错误，不因此盲改配置。校准未比较或导入，手机配置未变。后续继续本机旧SLPI版本及SPI NPA路由/固件ABI调查；每次试验先取得新boot13守卫，不重放boot12。\n'
    if 'sensors_v17_validation' in report:
        text+='\n最新phone checkpoint为k113-reboot-audio-clean-13。v17已完成单TAB转义RAM配置试验，解码校准/硬件值均未改变；原00121接近1样本，磁力计/加速度/光线/陀螺仪/compass仍254。语法修正不是枚举问题的完整解法。原selector/offline/供电0/taint0、源4/NV6保持，桌面/网络/NTP/空闲音频核验通过，DPU/GPU计数0。不能重放boot13 SLPI；下一轮须新启动14守卫。\n'
        text+='\n关机准备12初始ADSP stop有界15秒退出143，实际约15.07秒后原生offline；最终独立证明所有DSP离线及声卡注销，保留停止前closed PCM证据和失败读取后的空文件，才正常重启13。EUD关机读取中断保留，启动采集完成并释放owner；SSH新boot/完整早期日志另行通过。后续ADSP停止时限应留出余量并核对最终状态，不能把退出143改记为正常停止。\n'
    if (ref/'older-realme-package-links.json').exists():
        text+='\n旧固件资料：RealmeUpdater tracker固定6e0a3181b7c365b5a9d560c9abe164100b9faec3的RMX1931 A.11/A.13/A.15官方域名OZIP链接均返回206范围读取，包大小约2.64–2.72GB。仅在主机私有目录读取资料，不执行包脚本或整包刷机。A.11选择性范围提取是否成功、SLPI版本与CRC/映射结果必须看a11-package-range-validation及后续参考核验，不能把链接可访问记作固件通过。\n'
    if 'a11_reference_attempt' in report:
        text+='\nA.11当前未完成：68项ZIP目录可读，但完整modem/SLPI未取得，CRC未通过也未部署。小块/Python/curl/串行读取均有不完整响应；一次约64.7MB区间请求取得21,011,704字节后120秒超时，后续43.7MB请求为空、curl18。78个长度检查通过的缓存范围和中断数据保留私有，不能据此启动A.11。prepare-a11-v18.py只备有代码，包/脚本未生成或暂存；boot14尚未发出。后续优先定位SPI/NPA或寻找可完整校验的同型号来源，不自动重放失败下载。\n'
    if 'passive_after_v17' in report:
        passive=report['passive_after_v17']
        text+=f"\n当前boot13在{passive['uptime_seconds']/60:.1f}分钟处只读复核：taint0、DPU/GPU计数{passive['dpu_timeouts']}/{passive['gpu_faults']}、Phosh进程存在、SLPI offline/供电0。这只是当前日志与进程证据，不替代物理画面/休眠/长期验收。quiesce-clean-boot13.sh已在主机准备ADSP停止25秒余量，未执行、未暂存；之后的新试验仍需boot14守卫。\n"
    if 'npa_own_firmware' in report:
        text+='\n最新主机取证：参见npa-own-firmware-validation.json。原00121的24文件与v17档案一致；v17运行时callback 1024字节、lookup 384字节、tree lookup 160字节、SPI正常返回附近384字节均逐字节匹配原固件。0x400客户端受支持；16字节在callback右移3位，实际两对39/41→0，不能误读为16个master或客户端容量。ICB的1是资源上下文数，不是master数，实际12个master/33 slave和68条路径。两条旧请求无路由，错误4不是内存不足；SPI记录错误后回到正常epilogue，I2C的NULL句柄也与v17的STK3331样本并存。NPA失败作为缺传感器根因尚未证明，停止把补ICC/AP时钟/扩大客户端容量当作已确定解法。Sr-0w固定47087509的SPI笔记已更正早期归因，本轮结论用本机代码和转储独立验证，不借其地址。初始全量objdump只有root前段，终态未记录，不算完整成功；text7与NPA指定范围的独立进程已返回0，原始partial保留。下一步检查本机SSC描述符/注册与实例化，以及无过滤的SUID/事件解码，再决定有明确假设的boot14试验。本轮未刷机/改手机，A.11仍CRC未通过。\n'
    if 'ssc_census14' in report:
        text+='\n最新有效状态（优先于前面历史段落）：phone checkpoint k113-reboot-audio-clean-14，正常启动已核验；boot13 quiesce25秒余量完整完成，所有DSP/声卡/功放最终状态通过。census14全量与默认各32请求/64帧/32个768事件，64请求全部成功；Google Protobuf独立逐帧解码与实机记录一致，四种缺失物理类型仍0/proximity1。原00121全量空类型目录13 UID、总并集15，下一步只查询条目属性，识别其类型/可用标记，不能预先认作硬件已实例化。六项CLI仍仅接近1样本，SLPI转储20,871,615字节、51 ULog/5168条/19代码块映射通过。原selector/offline/供电0/taint0、源4/NV6及桌面/Wi-Fi/HTTPS/NTP/音频空闲通过，DPU/GPU0；新启动物理画面未重复询问。boot14 SLPI试验已结束，不能原地重放。A.11仍未CRC验收，旧prepare-a11-v18的boot14守卫不可复用。下一轮属性试验需要新的boot15检查点。\n'
    if 'ssc_attributes15' in report:
        text+='\n最新有效状态（覆盖前面boot14及更早的历史指导）：phone checkpoint k113-reboot-audio-clean-15。attributes15试验已结束；10个SUID事件768、15个属性事件128，25个成功ACK，独立逐帧解码通过。wise_light/Sensortek stk_stk2x3x为physical/available=true，但尚无真实光线样本；后续需按正确自定义协议查询，不把ambient_light缺失认作硬件不存在。接近仅1样本，原00121 accel/gyro/mag仍无条目；5113条ULog/19代码块映射通过，原selector/offline/供电0、源4/NV6保持，试验收尾taint0。boot15 SLPI已用过，下一轮传感器仍需新boot，显示回归优先。\n'
    if 'display_regression15' in report:
        text+='\n当前显示回归优先：用户新花屏闪烁，触发未知；恢复显示会话后确认画面稳定，不能接受永久修复。原回归display-regression-boot15.tar保留（taint0/DPU3），首次会话重启display-session-reset-boot15.tar新增fb_helper/vblank WARN变为taint512，且initial_session只在每boot第一次启动，曾进入Phrog，现已恢复原配置的cy122 Phosh。display-no-fbcon-boot15.tar证明运行时vtcon1 bind=0后仍新增DPU1，不能称根因解决；display-wake15正常PNG仅软件截图。当前累计DPU5/GPU0，taint512不能用默认taint0重启或传感器守卫。display-trace15只读保存原snapshot与trace，超时忙位真实；原快照已耗尽的snapshot:count=0没有重置。会话idle-delay从60暂改0供bringup，旧值保存在k113-display-visible15，结束需恢复60。新的原生DRM时序对照为display-clock15系列，第一轮inactive守卫退出1，未提交测试模式；Phosh已恢复，失败档案保留。下一步看实际试验档案后决定针对性补丁，不能盲写时钟寄存器或重刷userdata。\n'
    if 'current_user_scope' in report:
        text=text.replace('# 继续：113手动传感器供电与扩展FastRPC','# 继续：113自动化适配、rootfs完整性与已知回归')
        text=text.split('\n',1)[0]+'\n\n'+scope+'最新检查点和收尾状态见文末；以下早期启动/试验段落仅作历史，不用于重放守卫。\n'+text.split('\n',1)[1]
    if 'display_clock15b' in report:
        text+='\n2026-10-12最新时序对照：15首轮被残留CRTC状态守卫挡住，恢复Phosh新增DPU1（累计6）；15b先正常关闭旧输出再试。三轮共420翻页、425帧完成，约371/1107/371MHz均无测试窗口超时；完整操作新增2次DPU（累计8），发生在恢复Phosh之后，升频不能记修复。普通帧缓冲与Phosh QCOM压缩格式的差异是后续可自动验证假设，不是已证明根因。\n'
    if 'display_linear15_failed' in report:
        result=report['display_linear15_failed']
        text+=f"\n最新显示试验已收尾：WLR_DRM_NO_MODIFIERS=1未确认进入Phoc，退出1、没有线性缓冲证据，原launcher逐字节回滚。当前boot15 taint{result['taint_after']}、DPU累计{result['total_dpu_timeouts']}、GPU故障{result['gpu_faults']}；GPU转储不能忽略。用户要求无人参与自动化，显示光学验收暂缓，长时间未解问题保留后切换到rootfs完整性/缺失功能清点；不能宣称显示已永久稳定。\n"
    if 'display_idle_restored15' in report:
        text+='\n临时idle-delay=0已恢复60秒，原锁屏策略保持；无需再次运行bringup常亮脚本。\n'
    if 'wrap_up15' in report:
        text+='\n本轮最终收尾核验：wrap-up15.tar.gz/validation保存GPU故障日志、当前dmesg和原display/radio trace/snapshot；GPU devcoredump早先只读清点为323,539字节，收集时已不存在，未取得二进制，不能记为转储捕获成功。初次核验发现原display已耗尽snapshot触发器仍占一个事件，wrap-up15-trace-final.tar.gz补充解除该触发器并逐字节哈希核验快照保持；最终五个trace实例停止且事件全部关闭，新试验触发器也已解除。Phosh进程存在、F2FS rw、SLPI offline/供电0/原selector、源4/NV6、PCM closed和功放静音保持。当前运行时fbcon bind=0，下一次正常重启会恢复；taint512仍需新启动才能清除。没有EUD/fastboot/adb主机诊断进程或sensor/DRM试验进程。后续先核对实际boot和服务状态，再为taint512的已知原因设计明确的正常重启守卫，不重放默认taint0脚本。本轮到此结束，不再追加试验或自动重启。完整rootfs新镜像仍待准备与校验，不用会erase userdata的flash-pmos.ps1。\n'
    if 'wrap_up15' in report:
        text='''# 继续检查点：Realme X2 Pro Linux #113（2026-10-12）

本轮已按用户要求更新文档并收尾，不再追加试验、刷机或自动重启。完整适配目标尚未完成。

先读[最新进展](sessions/113-sensor-power-and-extended-rpc.md)、[15组硬件状态](linux-port/docs/HARDWARE-STATUS.md)、[最终收尾核验](reference/kernel113/wrap-up15-validation.json)及[聚合核验](reference/kernel113/checkpoint-validation.json)。历史启动和试验的具体过程放在阶段记录；不能重放旧boot守卫。

## 当前现场

| 项目 | 收尾核验结果 |
| --- | --- |
| 部署 | Linux #113，匹配boot/logdump/内嵌DTB；沿用已有userdata F2FS/Phosh |
| 启动检查点 | k113-reboot-audio-clean-15；完整bootID仅在私有文件 |
| 显示/GPU | DPU累计9次、GPU故障1次、taint512；花屏永久修复未验收 |
| 桌面/存储 | Phosh/Phoc进程存在、greetd started、F2FS根rw；后续试验后的物理画面未验收 |
| 临时设置 | 原launcher逐字节恢复；idle-delay恢复60秒、锁屏策略保持；fbcon运行时bind=0 |
| 传感器 | SLPI offline、VDD/VDDIO引用0；原qcom/sm8150/realme/samurai/slpi.mdt selector恢复，无自动SLPI服务 |
| 音频空闲 | 两项PCM closed，双功放powered=0/muted=1 |
| 来源/NV | 6项NV与4项来源哈希保持；原厂分区/校准不改 |
| 诊断 | display/radio/display-clock15/display-clock15b/display-linear15跟踪及事件全部关闭；无传感器/DRM试验进程或主机EUD/fastboot/adb诊断进程 |

原display已耗尽snapshot触发器也已解除，原快照前后SHA保持。wrap-up15.tar.gz与wrap-up15-trace-final.tar.gz保存最终现场和补充收尾证据，均私有。GPU devcoredump早先可见323,539字节，但采集时已消失，二进制未取得；GPU故障日志已经保存，不能记为转储捕获成功。收尾期间没有新增DPU/GPU故障或内核警告。

taint512来自本boot的显示会话重启WARN，仍保留在当前内核。下一次实际继续时先用[USB SSH包装器](reference/kernel109/usb-ssh-pmos.ps1)核对uname、boot、taint、服务和供电状态。已有taint0守卫不能直接用于此现场；需要根据完整日志设计明确的正常重启守卫，保持F2FS同步、用户音频/PCM/功放/ADSP及无线完整排空。没有准备或发出boot16。当前boot15的SLPI试验已经结束，不能原地重复启动。

## 已取得的结论及未解决项

原00121固件的10个SUID查询、15个属性响应、50个QMI帧经独立Google Protobuf解码一致，发现wise_light/Sensortek stk_stk2x3x物理光线条目。真实lux及自动亮度仍待正确自定义协议采样；原00121没有accel/gyro/mag条目。[属性核验](reference/kernel113/ssc-attributes15-validation.json)与[ULog核验](reference/kernel113/ulog-attributes15-validation.json)保留证据。STK3331真实遮挡变化已通过；C28 MMC5603X的898样本和窗口内转动响应已通过，但矩阵/准确度未验收，两版分别通过的硬件不能合并成一个可用默认固件。

显示原trace表明看门狗到期时busy真实，TE/vblank仍继续、CTL start IRQ成功而PP未完成；现有看门狗竞争及DSI burst/EOT修复已经在运行内核中。原生DRM约371/1107/371MHz三轮420翻页均无窗口超时，但恢复Phosh后新增2次DPU超时，不能接受升频修复。普通帧缓冲与Phosh QCOM压缩modifier差异只形成假设。WLR_DRM_NO_MODIFIERS试验退出1，未确认环境或线性缓冲，原launcher已回滚；新GPU故障保留。参见[跟踪](reference/kernel113/display-trace15-validation.json)、[时序对照](reference/kernel113/display-clock15b-validation.json)、[失败回滚](reference/kernel113/display-linear15-failed-validation.json)。

A.11 modem范围下载未完成、CRC未通过、SLPI未提取/部署；不再把私有片段当候选。旧prepare-a11-v18.py的boot14守卫无效。NPA错误4是缺路由，但SPI正常返回、I2C NULL与STK3331实际采样并存，尚未证明是缺失传感器根因；不盲补ICC/AP时钟或客户端容量。

## 后续执行约束与优先项

用户要求只运行自动化调试，继续互联网/源码仓库/本机反汇编取证。画面、触摸、遮挡、转动和听音等人工验收暂缓，不因日志或截图正常就替用户验收。长时间无可验证进展的错误保留证据和文档后转到下一项。

下一阶段优先清点并补齐完整postmarketOS rootfs镜像：当前仍使用阶段109已有持久F2FS系统，新完整镜像尚未生成或交付。先记录实际包/服务/固件依赖及缺失功能，离线构建、校验内容、保留当前userdata及回退证据，再安排有明确假设的自动化测试。flash-pmos.ps1会erase userdata，不用于日常更新；不能用文档或准备文件冒称新rootfs已经刷入。

15组硬件继续保留：显示/GPU稳定性、5GHz、完整传感器服务、音频实听、摄像头、指纹、GNSS、蜂窝通话/数据、OTG及休眠仍有未验收项。蓝牙未配对、NFC仅控制器、振动未发脉冲、充电探针已结束。优先可自动验证的项目，不盲写GPIO/NV。

源码在/home/cy122/pmos-samurai-kernel113/{kernel,initramfs}及隔离的/home/cy122/hexagonrpc-v04-k112。规范EDK2源码/产物已恢复阶段109，手机当前boot仍为113；113完整回退组合是111 boot +112 logdump，不能混用内嵌DTB。F1前必须有当前启动F2FS同步/冻结或只读卸载证明，旧启动日志不能复用。任何新测试必须使用跨历史阶段唯一前缀和实际当前boot守卫。

身份、凭据、PIN、SSID/PSK、固件、校准、原始日志、录音及镜像只存E:/edk2-samurai-out，不公开、提交或推送。旧109/112文档脚本会回写旧状态，不用于本阶段。最新用户约束见[user-scope-20261012.json](reference/kernel113/user-scope-20261012.json)。
'''
    path.write_text(text)
