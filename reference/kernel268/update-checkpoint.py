"""Archive old deployment identities and write the current camera checkpoint."""
from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parent;root=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel268')
archive=root/'archive'
for source,name in [(root/'NEXT-SESSION.md','NEXT-SESSION-through267-2026-10-18.md'),(root/'linux-port/camera/deployment-lock.json','camera-deployment-lock-through262-2026-10-18.json')]:
 target=archive/name;assert not target.exists();shutil.copyfile(source,target)
full=json.loads((P/'camera-forward-repo-r19/package-manifest.json').read_text())
health=json.loads((R/'final-health-validation.json').read_text())
rows=[{k:v for k,v in p.items() if k in ['name','version','file','sha256','bytes','arch']} for p in full['packages']]
names={'libcamera','libcamera-gstreamer','libcamera-ipa','libcamera-tools','libcamera-v4l2','samurai-camera-config','samurai-camera-stack'}
runtime=[p for p in full['packages'] if p['name'] in names];assert len(runtime)==7
launch=root/'linux-port/camera/snapshot-launcher'
launch_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in launch.iterdir() if p.is_file()}
assert launch_hashes['org.gnome.Snapshot.desktop']=='b857de670636c17d2dc0faaa902e94652fecc31d30f7d5df925e0bd3164b432e'
lock=dict(stage=268,kernel_boot_stage=267,current_boot_guard_stage=267,kernel_image_stage=183,
 framework_version='99990.7.2-r19',configuration_version='0.1.0-r14',pipewire_core_spa_gstreamer_version='1.6.9-r3',
 package_recipe='../packages/libcamera/APKBUILD',configuration_recipe='../packages/samurai-camera-config/APKBUILD',
 package_source_lock='../packages/libcamera/source-lock.json',built_packages=rows,installed_package_payloads=runtime,
 installed_package_count=961,ko_count=773,kernel_modules=health['modules'],
 boot_sha256='b79d0e0f53c9db04ca7b9de88727142eecdefed97229b8477226caf7ef6bf387',
 dtb_sha256='9a2307c0d93b4ad6d5b23c570a0c84a116a930d0de6b3370d5737eb0bac768c5',
 standard_regulator_consumers_and_dt_wiring=True,lab_supply_and_board_reset_provider_removed=True,
 cpu_isp_and_system_dma_heap=True,private_library_overrides_absent=True,per_application_copy_switch_absent=True,
 snapshot_launcher_profile='snapshot-launcher/',snapshot_launcher_sha256=launch_hashes,snapshot_cairo_workaround_still_required=True,
 snapshot_front_rear_gui_preview_switch_shutter_verified=True,snapshot_jpeg_decode_verified=True,
 current_camera_evidence='../../reference/kernel268/README.md',final_health_evidence='../../reference/kernel268/final-health-validation.json',
 system_services=health['system_services'],guard_path='/var/lib/samurai/k267-work/boot-id-private.txt',
 full_image_all_modules_and_rootfs_rebuild_pending=True,other_rear_cameras_quality_rotation_gpu_video_still_open=True,goal_status='active',
 previous_lock_archive='../../archive/camera-deployment-lock-through262-2026-10-18.json')
(root/'linux-port/camera/deployment-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
(root/'NEXT-SESSION.md').write_text('''# Realme X2 Pro 当前检查点

2026-10-18：用户要求继续按主线 Linux＋SM8150 公共驱动＋RMX1931 设备树适配摄像头，尽量保持发行版和应用通用。[267内核供电](reference/kernel267/README.md)与[268公共库/实机应用](reference/kernel268/README.md)已完成本阶段验证，完整相机与整机适配仍 active。

## 当前手机身份

boot267/Image183，7.3.0-rc6-rmx1931-samurai-k132+，773ko/961包。guard `/var/lib/samurai/k267-work/boot-id-private.txt`；使用reference/kernel267/host.py（268委托它）及私人新USB IPv6端点、原严格主机密钥。260旧guard、265与267旧PID均失效。当前普通服务PW16218/start341625、WP16224/start341628、Phosh15483，手机`/var/lib/samurai/k268-services-current-private.json`为权威。

267已刷boot并完整读回，Image183/logdump保持，不重放暂存/quiesce/restart/flash。双PM8008共用MFD/regulator，IMX319用sony,imx319及DT接线/电压/方向，lab模块、板级reset provider和loader配置已撤。MFD bcdbf711、regulator d4dbb9cd、IMX319 53917b99；前摄e49dab26/CAMSS ff9fdfa3保持。[当前部署锁](linux-port/camera/deployment-lock.json)。

libcamera五组件r19、config/stack-r14，公共PW/SPA/Gst 1.6.9-r3。原生签名七包升级，49项载荷再核对、其余954包记录保持；无私人库或应用复制开关。CPU ISP/system heap与Snapshot Cairo启动回退仍在，默认GPU未修复。

## 已验证与下一步

标准cam前后各三轮72帧；独立cam与常驻PipeWire交替另36帧，三轮预览1097帧、1081次保留前65536字节检查、9张后台JPEG。实际Snapshot前后预览、点击Switch Camera和两次快门通过；前摄1920×1080、后摄1600×900 JPEG成功解码。图库场景、原日志和密钥留私人目录，不公开像素。低照度/颜色/方向校准、其它后摄、录像、GPU与长稳尚未验收。

GUI r1/r2受锁屏和窗口状态影响，r3只扫深度20遗漏按钮，r4在应用启动前因屏保active被拒绝；r5深度64完成双摄。临时Phosh --unlocked用户覆盖、lock-enabled/idle设置均恢复，当前会话未再重启；正常锁屏可恢复，不再把GetActive=false单独当作已解锁证明。一发式GUI/安装上下文保持终态，不直接重放。

最终无存活Snapshot，五模块加载note与磁盘一致，四rails OFF/users0，双sensor/CCI/CAMSS suspended，MCLK1/2关，新增fault0/taint0。[最终健康](reference/kernel268/final-health-validation.json)。格式、图和AE由公共库管理，不外部写回旧media状态。

维护内核源已提交db301b64c，十四输入与实际部署源逐字对应。独立维护树五个相机目标W=1编译无诊断，DTB逐字等于现机。第一次完整模块链接因缺vmlinux.o被拒绝，第二次明确只编译对象；未伪造或部署链接产物。完整新Image、全部模块及rootfs尚未重建，下一阶段继续做源码/镜像整合并验收画质和其它镜头。canonical仍旧after228输出，不能当新部署产物使用。[源码与构建边界](reference/kernel268/README.md)。

原r15/r10七包、world/repos/db和267旧模块/boot回退均保留，联合降级模拟通过。PC私人目录E:/edk2-samurai-out/kernel267、kernel268；新事务均已执行，不重复覆盖上下文。用户延期纯色测试，不作为其它工作的前置条件。

## 其它功能和规则

先读[操作边界](WORKING-BOUNDARIES.md)与[硬件清单](linux-port/docs/HARDWARE-STATUS.md)。NV/校准/工厂备份不误写；电池保护不绕过；切换前核当前身份；密钥和私人数据不公开，蓝牙只扫描、不配对/连接，振动不新增脉冲。

260桌面GNSS室外300秒280次更新、262次严格校验，停止后LOW_POWER与设置恢复通过；18次未分类、Accuracy=0旧校验问题、冷启/PM/长稳/绝对精度仍开放。用户已取回手机接USB，旧室外worker不重跑。[260](reference/kernel260/README.md)。261中文/字体/输入法/商店及Phoc文本输入待办；full upgrade现961包、Phoc0.57。[维护](reference/full-upgrade-20261018/README.md)。音频、充电、传感器、SIM、外围和完整rootfs边界继续见硬件清单。

本次前的完整检查点已[归档](archive/NEXT-SESSION-through267-2026-10-18.md)。旧[265](reference/kernel265/README.md)、[240](reference/kernel240/HANDOFF.md)记录保留为历史，不用于当前手机身份或版本。
''')
print('Archived old checkpoint/lock; current identities, packages, evidence and open work recorded.')
