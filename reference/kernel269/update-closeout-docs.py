"""Archive the previous checkpoint and reconcile the current closeout entries."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parent;root=R.parents[1]
health=json.loads((R/'final-health-validation.json').read_text())
feedback=dict(stage=269,user_confirmed_automatic_rotation_correct=True,
 user_report='现在自动旋转正常了',user_identified_crashing_application='Camera (Snapshot)',
 standard_matrix='-1,0,0;0,-1,0;0,0,1',independent_observer_only_captured_left_up_transform_1=True,
 complete_physical_pose_sequence_not_captured_by_observer=True,fresh_boot_startup_order_verification_pending=True)
(R/'rotation-user-feedback-validation.json').write_text(json.dumps(feedback,ensure_ascii=False,indent=2)+'\n')
archives={}
for source,dest in [('NEXT-SESSION.md','archive/NEXT-SESSION-through268-2026-10-18.md'),
 ('linux-port/camera/deployment-lock.json','archive/camera-deployment-lock-through268-2026-10-18.json')]:
 p=root/dest;assert not p.exists();data=(root/source).read_bytes();p.write_bytes(data);archives[dest]=hashlib.sha256(data).hexdigest()
checkpoint='''# Realme X2 Pro 当前检查点

2026-10-18：[269收尾](reference/kernel269/README.md)。用户要求停止新增实验、更新文档；本轮已收尾，完整摄像头和整机适配未完成。后续按用户指示续作，不把本轮进展当成全目标完成。

## 当前手机身份

固件仍boot267／Image183，`7.3.0-rc6-rmx1931-samurai-k132+`，773ko／961包。用户打开Camera (Snapshot)后意外重启，原267/268启动guard与PID失效。现用[269 host](reference/kernel269/host.py)、原严格SSH主机密钥和重新发现的私人USB端点；guard `/var/lib/samurai/k269-work/boot-id-private.txt`，本地主机身份收据在私人269目录。不要绕过旧guard或把旧PID当当前服务。

收尾Phosh7908、PW8731/start75856、WP8738/start75860，手机 `/var/lib/samurai/k269-services-current-private.json` 为该次核对权威。续作先重读，用户可能已操作。桌面重建的临时--unlocked用户启动覆盖已恢复，lock/idle偏好未改；当前会话沿用--unlocked至退出。

libcamera五组件r19、config/stack-r14、PW/SPA/Gst1.6.9-r3保持。49项相机包载荷重新核对。五模块当前文件SHA前缀：PM8008 MFD bcdbf711、regulator d4dbb9cd、IMX319 53917b99、IMX471 e49dab26、CAMSS ff9fdfa3，加载note与磁盘一致。双PM8008走公共MFD/regulator及设备树供电，lab模块、板级reset provider和旧loader配置均已撤。[部署锁](linux-port/camera/deployment-lock.json)。

## 已验证与下一步

整屏旋转方向已修：RMX1931板级设备包提供标准udev `ACCEL_MOUNT_MATRIX=-1,0,0;0,-1,0;0,0,1`，X/Y取反、Z保持，原版SensorProxy SSC后端处理。正常竖握及左侧朝上的传感器报告正确；桌面重建后独立观察为left-up／90°，用户确认自动旋转正常。完整左右往返未被观察窗口录下，单独记录用户反馈，不能冒充机器轨迹。当前SSC路径没有内核IIO节点，属于板级用户态配置，不能称DTS修复；后续IIO接入才由驱动消费DT挂载矩阵。[旋转说明与证据](reference/kernel269/README.md#整屏旋转板级配置不改应用)。

桌面原先先于radio／SSC启动，当前标准OpenRC配置改为greetd依赖dbus和iio-sensor-proxy，撤掉相反的before-radio边，依赖缓存更新通过；下一次整机启动顺序仍待验。`samurai-platform 5-r1`与`samurai-desktop 3-r1`完整配方已同步，25项源校验通过，前者同时删除旧实验供电参数和reset softdep。两项手机配置单独部署，APK尚未构建／安装。候选pmaports工作树 `/home/cy122/x2pro-linux/pmaports-camera-common269`，本地提交5e955a7c19355da6962eba9f03874cdf0081dfff，未发布；原目录及其用户改动保持。

Snapshot意外重启未解决。上一启动pstore已保存262132字节，末尾6196秒modem watchdog、6202秒日志结束；未见相机WARN/Oops栈，但证据不足以排除打开相机的关联。旋转规则当时尚未写入。新启动只做一次既有Cairo启动器36.84秒观察，无新增fault，但传感器全程suspended、vb2完成／取出0，未实际取流；这不是相机通过或重启问题修复。随后读取到息屏，标准接口唤亮后输出恢复；按用户要求收尾，未追加第二轮。[重启与补测边界](reference/kernel269/README.md#snapshot意外重启未解决)。

此前268同一旧启动已验证：标准cam72帧、跨框架交替36帧、系统预览1097帧／1081次保留前缀检查、9张后台JPEG；未改Snapshot前后预览、Switch Camera、两次快门及三张GUI JPEG解码通过。这些历史结果保持，但不能覆盖本轮新启动的稳定性问题。[268](reference/kernel268/README.md)。CPU ISP/system heap及Snapshot Cairo/禁用GL、Vulkan、offload回退仍在，默认GPU未修。

内核维护树 `/home/cy122/x2pro-linux/upstream` 当前 `samurai-camera-common`／1f5da50bbcba4fbe89917db7987429fdf078f257，原samurai-bringup/db301b64保留。已删除五个禁用OF实验helper；固件IOVA窗口移到RMX1931设备树，公共CAMSS保留标准DMA mask／完整SG检查和动态调试。40024个实际函数ASan/UBSan案例及旧实现负对照、四类DT schema通过，新旧937节点全部属性语义相同。[269源码及范围](reference/kernel269/README.md#内核收敛与验证边界)。

**新Image＋全部773模块＋DTB已完整构建成功，尚未部署。** 输出 `/home/cy122/x2pro-linux/camera269-full-build-r1`，release `7.3.0-rc6-rmx1931-samurai-k269+`；Image SHA256 9153da19b7ead38943792a84526723fb6d17177a0a2a45939972cd08465a3f61，DTB 51b289d64645a2decd77147a1d0be0ed2165ed3e72890086939da10a1e6e610a。构建已terminal/exit0，勿重启同一事务。五相机模块W=1诊断0，全树1140条尚待分类；其它外设源码与现机对应仍待核，新Image不可直接当已验收产物刷写。完整rootfs尚未重建，候选源本轮未发布，远端状态按268历史收据解释，续作先重读远端。

最后只读健康：无相机进程，269跟踪关闭；四rails disabled/users0，双sensor／双CCI／CAMSS suspended，MCLK1/2关；本次启动warning/Oops/modem/fatal/GPU0、taint0。[健康收据](reference/kernel269/final-health-validation.json)。这不抹除上一启动modem watchdog。所有新事务目录已执行，不能盲目重放采用guard、安装矩阵、重建桌面、拍摄探测或完整构建脚本。

下一步：核新身份与原日志，在真正出帧／窗口可见条件下复现Snapshot故障；核首次启动顺序；审核完整内核与其它外设对应后准备一致Image/DTB/模块和回退再上机；整合可重放用户态/rootfs及发布源。低照度/颜色/相机图像方向、其它后摄、录像、GPU与长稳继续待办。前摄纯色测试按用户延期。旧r15/r10七包回退、267旧模块/boot备份及268事务均保留。

## 其它功能和规则

先读[操作边界](WORKING-BOUNDARIES.md)与[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。NV/校准/工厂备份不误写；电池保护不绕过；切换前核当前身份；密钥和私人数据不公开，蓝牙只扫描、不配对/连接，振动不新增脉冲。PC私人目录为E:/edk2-samurai-out/kernel269及历史267/268；场景、原日志、USB端点、启动ID、密钥和含私人initramfs的镜像不公开。

260桌面GNSS室外300秒280次更新、262次严格校验，停止后LOW_POWER与设置恢复通过；18次未分类、Accuracy=0旧校验问题、冷启/PM/长稳/绝对精度仍开放。[260](reference/kernel260/README.md)。261中文/字体/输入法/商店及Phoc文本输入待办；full upgrade961包、Phoc0.57保持，[维护](reference/full-upgrade-20261018/README.md)。本轮没有重做其它硬件验收，基带新增watchdog须保留在稳定性待办。

上轮检查点已[归档](archive/NEXT-SESSION-through268-2026-10-18.md)。早期[240交接](reference/kernel240/HANDOFF.md)与[267](reference/kernel267/README.md)、[268](reference/kernel268/README.md)保留对应阶段证据，旧身份／版本／PID不用于当前操作。
'''
(root/'NEXT-SESSION.md').write_text(checkpoint)
lockpath=root/'linux-port/camera/deployment-lock.json';d=json.loads(lockpath.read_text())
d.update(stage=269,current_boot_guard_stage=269,guard_path=health['current_guard'],final_health_evidence='../../reference/kernel269/final-health-validation.json',
 current_camera_evidence='../../reference/kernel269/README.md',snapshot_gui_evidence_stage=268,current_boot_actual_capture_validation_pending=True,
 current_boot_unexpected_reboot_followup=True,snapshot_reboot_cause_unresolved=True,
 goal_status='incomplete_user_requested_closeout',previous_lock_archive='../../archive/camera-deployment-lock-through268-2026-10-18.json',
 full_image_and_all_modules_candidate_built=True,candidate_kernel_receipt='../../reference/kernel269/full-build-validation.json',candidate_kernel_deployed=False,
 full_rootfs_rebuild_pending=True,board_rotation_matrix='-1,0,0;0,-1,0;0,0,1',
 board_rotation_rule_sha256=health['sensor_rule_sha256'],sensor_startup_order_receipt='../../reference/kernel269/sensor-startup-order-validation.json',
 sensor_startup_fresh_boot_validation_pending=True)
d.pop('full_image_all_modules_and_rootfs_rebuild_pending',None)
d.pop('other_rear_cameras_quality_rotation_gpu_video_still_open',None)
d['other_rear_cameras_quality_camera_orientation_gpu_video_still_open']=True
d['system_services'].update(stage=269,new_processes=[dict(name=p['comm'],pid=p['pid'],start_ticks=p['start_ticks']) for p in health['services']['processes'] if p['comm'] in ['pipewire','wireplumber']],phosh_pid=7908)
lockpath.write_text(json.dumps(d,indent=2)+'\n')
changed=['NEXT-SESSION.md','linux-port/camera/deployment-lock.json']
def insert_after_title(name,paragraph):
 p=root/name;s=p.read_text();title,rest=s.split('\n\n',1);p.write_text(title+'\n\n'+paragraph+'\n\n'+rest);changed.append(name)
insert_after_title('linux-port/camera/README.md','2026-10-18最新：[269收尾](../../reference/kernel269/README.md)。整屏旋转使用RMX1931板级标准udev安装矩阵，用户确认恢复正常；桌面服务依赖已修，首次整机启动顺序待验。统一Image/773模块/DTB已构建，未刷入；手机仍267固件/Image183、r19/r14、PW r3，意外重启后改用269guard。用户打开Snapshot发生卡死重启，pstore末尾modem watchdog，原因未解决；本轮补测没有出帧，不能视为通过。完整rootfs、画质/其它镜头/GPU/录像/长稳仍未完成。本轮按用户要求收尾；以下各阶段的active、健康和构建待办只对应其历史窗口。')
p=root/'linux-port/camera/README.md';s=p.read_text().replace('2026-10-18当前：[267]','267/268阶段历史结果：[267]',1).replace('240交接时完整适配目标为paused、未完成；后续已恢复active。','240交接时完整适配目标为paused、未完成；267/268继续推进，269按用户要求收尾。',1);p.write_text(s)
insert_after_title('linux-port/docs/HARDWARE-STATUS.md','269收尾（2026-10-18）：[板级旋转与完整构建](../../reference/kernel269/README.md)。标准udev安装矩阵修复整屏方向，用户确认自动旋转正常；桌面依赖SensorProxy的启动顺序已更新但跨启动待验。新Image和773模块构建成功、未部署，完整rootfs待办。用户打开Snapshot卡死重启，pstore末尾modem watchdog；补测未出帧，稳定性问题未解决。现机仍267固件/Image183、r19/r14/PW r3，新的269guard替代旧启动身份。最后只读健康正常不覆盖上一启动故障；本轮按用户要求收尾，完整适配未完成。下述阶段结果与健康值按对应时间解释。')
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text().replace('267/268相机当前（','267/268相机阶段结果（',1)
rows=s.splitlines()
for i,line in enumerate(rows):
 if line.startswith('| 摄像头 |'):
  rows[i]='| 摄像头 | 267公共PM8008/IMX319与设备树、268公共libcamera r19/config-r14/PW r3；此前标准cam72帧、交替36帧、1097帧预览/1081次前缀检查、9后台JPEG和未改Snapshot前后界面切换/快门/JPEG解码通过；269统一Image/773模块构建成功但未部署 | 269用户打开Snapshot卡死重启，末尾modem watchdog，原因未解决；补测0实际帧，不能视为通过。低照度/颜色/相机图像方向、其它后摄、录像、GPU、长稳、完整rootfs和新内核上机仍待办；既有Cairo回退保持 |'
 elif line.startswith('| 其它传感器 |'):
  rows[i]=line.replace('人工运动/方向/自动旋转、','269板级安装矩阵及桌面重新发现传感器后，用户确认整屏自动旋转正常；首次整机启动顺序、3D安装/精度及更广运动回归仍待验。')
 elif line.startswith('| 蜂窝通话与数据 |'):
  rows[i]=line.replace('| mcfg.tmp','| 269保存到一次modem watchdog并伴随整机意外重启，原因和与Snapshot的关联未明。mcfg.tmp',1)
p.write_text('\n'.join(rows)+'\n')
p=root/'linux-port/camera/kernel/README.md';s=p.read_text();parts=s.split('\n\n',2)
parts[1]='2026-10-18最新：[269](../../../reference/kernel269/README.md)维护分支已删除五个禁用OF实验helper，固件IOVA限制移到RMX1931板级树，公共CAMSS使用标准DMA mask/SG检查。新Image、DTB及全部773模块已从同一清洁提交完整构建成功，五相机目标W=1诊断0，全树1140条待分类；937节点设备树语义保持。候选尚未部署／发布，完整rootfs尚未重建；手机仍267固件/Image183及267模块。以下219/223与267/268构建状态是历史记录，不能替代当前部署身份。'
p.write_text('\n\n'.join(parts));changed.append('linux-port/camera/kernel/README.md')
insert_after_title('reference/kernel268/README.md','后续[269收尾](../kernel269/README.md)：已完整构建新Image/773模块但未部署，并修复板级整屏旋转。用户打开Snapshot发生意外重启，末尾modem watchdog，稳定性原因未明；原267/268启动guard和PID已失效，现用269guard。下文GUI通过与最终健康只对应268原启动，不覆盖新故障。')
insert_after_title('reference/kernel267/README.md','后续当前状态见[269收尾](../kernel269/README.md)：手机发生意外重启，当前启动身份与服务改用269；固件267/Image183及本阶段模块保持，新完整内核候选已构建但未部署。下文267/268的active、guard、PID与健康按历史解释。')
insert_after_title('reference/kernel240/HANDOFF.md','当前续作先读[269收尾](../kernel269/README.md)和[检查点](../../NEXT-SESSION.md)：整屏旋转已确认修复，新完整内核未部署；Snapshot意外重启与modem watchdog仍未解决。用户要求收尾，以下240阶段的优先级、旧缓冲缺陷及身份均为历史，不再作为当前状态。')
p=root/'DOCS-INDEX.md';s=p.read_text();needle='| Camera应用、实体前后摄与内部TPG | ';assert needle in s
s=s.replace(needle,needle+'[269收尾、板级旋转与完整内核候选](reference/kernel269/README.md)、',1)
s=s.replace('| 蓝牙、Wi-Fi与USB |','| 传感器板级方向与桌面启动顺序 | [269旋转修复与验证边界](reference/kernel269/README.md)、[平台配方](linux-port/packages/samurai-platform/README.md)、[桌面依赖配方](linux-port/packages/samurai-desktop/README.md) |\n| 蓝牙、Wi-Fi与USB |',1);p.write_text(s);changed.append('DOCS-INDEX.md')
p=root/'HANDOVER-NEXT.md';s=p.read_text().replace('当前相机状态见[267公共供电]','当前收尾、板级旋转、完整内核候选及Snapshot重启待办见[269](reference/kernel269/README.md)；此前相机验证见[267公共供电]',1);p.write_text(s);changed.append('HANDOVER-NEXT.md')
p=root/'sessions/INDEX.md';s=p.read_text();needle='| [kernel268](<../reference/kernel268/README.md>) | 268 公共链路缓存修复与前后摄界面切换拍照 |';assert needle in s
s=s.replace(needle,needle+'\n| [kernel269](<../reference/kernel269/README.md>) | 269 内核维护收敛、板级旋转修复与收尾 |',1);p.write_text(s);changed.append('sessions/INDEX.md')
report=dict(stage=269,previous_checkpoint_and_lock_archive_sha256=archives,updated_documents=changed,
 current_boot_guard_stage=269,full_new_kernel_built_but_not_deployed=True,snapshot_reboot_unresolved_and_zero_frame_probe_recorded=True,
 automatic_rotation_user_feedback_and_machine_observation_separated=True,user_requested_closeout=True,full_adaptation_incomplete=True)
(R/'documentation-update-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
