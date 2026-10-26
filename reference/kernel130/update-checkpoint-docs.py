from pathlib import Path
import json,re
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel130'
load=lambda n:json.loads((ref/n).read_text())
bundle=load('complete-bundle-validation.json');warm=load('warmboot-validation.json');vol=load('host-volume-validation.json');cleanup=load('superseded-raw-cleanup-validation.json')
assert bundle['matching_boot_logdump_rootfs_modules_complete'] and warm['standard_openrc_bluez_auto_start_pass'] and vol['current_e129_volume_unmounted_offline_readonly_fsck_zero']
link='[阶段130](sessions/130-standard-bluez-discovery-and-startup-integration.md)'
status='阶段130补齐标准BlueZ5.87服务的本机DMS地址供应和default自动启动，实际两组LE/BR/EDR/混合扫描及HCI/MGMT发现事件通过；正常暖重启后无需手动服务/地址/网络激活，BlueZ运行且控制器默认关闭，5180MHz/网关/HTTPS/50.24秒窗口通过。当前内核仍#129，boot/logdump/770模块保持；完整rootfs130含936包、21,135条目反向内容与metadata零差异、双fsck/稀疏重建/encoded UID10000实际读写和四件套通过，服务/config/runlevel已增量部署，完整userdata未全量刷入。当前taint0/DPU0/GPU0/CRTC active1仅为本次启动窗口，旧GPU像素故障及持续显示未证明修复；BT启动UART错误累计2，配对/传输/冷启动/休眠与其余硬件边界保留，goal active。'
for name in ['README.md','FLYWHEEL.md']:
 p=r/name;t=p.read_text();t=t.replace('[阶段129](',link+'，[阶段129](',1);a=t.index('阶段129已实际刷入#129');b=t.index('\n\n',a);t=t[:a]+status+t[b:];t=t.replace('最新匹配镜像见阶段129','最新匹配镜像见阶段130',1);p.write_text(t)
p=r/'DOCS-INDEX.md';t=p.read_text();a=t.index('- [阶段129');t=t[:a]+'- '+link+'：实际标准蓝牙扫描、DMS地址与服务自动启动暖重启验收、完整匹配129内核的rootfs130。\n\n'+t[a:];p.write_text(t)
p=r/'linux-port/docs/HARDWARE-STATUS.md';t=p.read_text().replace('阶段129）','阶段130）',1);a=t.index('15组硬件保持。');b=t.index('\n\n',a);t=t[:a]+'15组硬件保持。 '+status+t[b:];t=t.replace('[阶段129](', '[阶段130](../../sessions/130-standard-bluez-discovery-and-startup-integration.md)、[阶段129](',1)
rows={
 '原生显示面板':('阶段130新暖启动#129 DRM/card1/Phosh/Phoc/taint0，50.24秒窗口DPU/GPU0、最终CRTC active1；另10秒只读encoder vsync3182→3182、underrun0','未施加绘制负载；持续绘制/命令帧/休眠/长稳与旧GPU像素故障继续开放，不能因active1/0故障判修复'),
 '普通USB与OTG':('当前#129原生NCM/SSH/SCP，阶段130正常OpenRC暖重启恢复新boot；无本轮分区刷写，boot/logdump/persist/GPT稳定基线保持','OTG/USB3/休眠/长稳；继续现机身份与物理by-path守卫'),
 'Wi-Fi':('128单播删除等待修复保持；130新暖启动自主5180MHz/网关3/3/HTTPS200，50.24秒6样本通过；两组实际蓝牙扫描时同PID桌面/MPSS/ADSP/5GHz保持','物理断电冷启动/休眠/长稳及历史非主动reason7仍开放，原双频profile/固件/校准保持'),
 '蓝牙':('本机只读DMS地址/MGMT/DBus读回，两组标准BlueZ5.87 LE/BR/EDR/混合扫描及真实HCI/MGMT发现事件通过；OpenRC服务start/restart及新暖启动自动供应地址/默认off通过','开启和启动期UART phase2 -84仍存在，新boot累计2；配对/传输、物理冷启动/休眠/长期共存待办'),
 '音频':('#129新暖启动ADSP/card0、PCM closed、双amp idle/failed0，23样本蓝牙扫描共存及6样本暖启动保持；历史UCM/扬声器/DMIC0电气验收保留','实际音质/耳机/DSM/校准/休眠及自动音频回归待办')}
for name,(done,todo) in rows.items():
 t,n=re.subn(r'^\| '+re.escape(name)+r' \|.*$',lambda m:f'| {name} | {done} | {todo} |',t,flags=re.M);assert n==1
t+='\n阶段130：'+status+' 下一轮优先本次新暖启动的有界真实GPU像素回归；旧25失败不能因未重跑判通过。\n';p.write_text(t)
p=r/'sessions/130-standard-bluez-discovery-and-startup-integration.md';t=p.read_text()
t=t.replace('标准service管理下的另一次LE/BR/EDR/混合扫描已执行完成，原始归档与验收收尾中；开机自动恢复仍需新启动验收，不能以热启动服务代替。','标准service管理下的第二组LE/BR/EDR/混合扫描原始验收通过：52条found、15个地址/类型组合、789条HCI包、23健康样本，结束服务运行/控制器off。同一阶段实际排空GUI/无线/音频/三remoteproc后正常OpenRC暖重启，新boot仍129，服务无需手动启动，新RAM DMS查询与MGMT/DBus地址读回一致，控制器默认off。')
t=t.replace('新镜像编码/反向导出验收正在进行，129稳定镜像与模板保留，userdata没有擦除或全量刷入。',f'完整130 sparse镜像{next(a["bytes"] for a in bundle["artifacts"] if a["role"]=="rootfs")}字节、SHA256 {next(a["sha256"] for a in bundle["artifacts"] if a["role"]=="rootfs")}；双dry-run fsck/稀疏payload与空洞/两superblock UUID-label/21,135条目内容与metadata反向零差异、encoded chroot UID10000实际创建/读写/删除和四件套通过。129稳定镜像与模板保留，userdata没有擦除或全量刷入。')
t=t.replace('下一步完成标准service原始验收与完整镜像，再实际新启动验证默认服务及DMS供应。','下一轮优先本次新暖启动的有界真实GPU像素回归；旧118的25失败仍未修复，不因新boot零故障直接判通过。')
t+=f'\n新暖启动第一个collector在NM尚未连接时freq断言失败，partial目录和原输出保留，没有手动activation；稍后只读观察已自主5180，第二collector先有界等待同一boot的自主频率/默认路由后新目录完整验收。50.24秒6样本服务/GUI/radio/ADSP/5GHz/taint0、网关3/3/HTTPS577字节/11来源/770模块/分区读回通过；boot UART错误累计2，本次窗口0新增。新boot DPU0/GPU0/final active CRTC1，但另10秒encoder vsync3182→3182/underrun0，无负载，不能称连续帧或GPU像素已修复。初始console warning0保持。\n\n仅清理E129卷两个可由保留129 sparse新鲜逐字节/空洞证明恢复的旧raw，实际分配释放{cleanup["allocated_bytes_removed"]}字节，129template/export/sparse与130全部产物保持。E129 sync卸载/read-only e2fsck0，稳定E118/122/126实际仍未挂载且本轮未修改；C新增删除0/9未证明.o保留/稳定Image存在。C余{vol["host_c_free_bytes"]}、E余{vol["host_e_free_bytes"]}字节，原WSL VHD未resize/compact。初次close因WSL空闲结束后/run锁不存在，在任何sync/卸载前失败；同次WSL先ensure重新核验挂载后完成关闭。所有作业terminal。\n';p.write_text(t)
art={a['role']:a for a in bundle['artifacts']}
(r/'NEXT-SESSION.md').write_text(f'''# Realme X2 Pro 继续检查点（阶段130，2026-10-12）

{status}

先读{link}、15组HARDWARE-STATUS及reference/kernel130/complete-bundle-validation.json。用户要求自动飞轮，无人工检查/配对，互联网/本机源码/反编译；长难错留档换项，静态补丁后实机日志验收；经验证obsolete才清理，稳定回退保持。goal active。

## 当前手机与匹配产物

当前新暖启动#129，release 7.3.0-rc6-rmx1931-samurai-k129+；当前boot身份仅E:/edk2-samurai-out/kernel130/embedded-boot-id-private.txt及phone /var/lib/samurai/k130-warmboot-r2/boot-id-private.txt。130 source-boot-id及旧129 embedded均属于上个boot，不可用于冻结当前boot。

boot {art['boot']['sha256']}，logdump {art['logdump']['sha256']}，modules {art['modules']['sha256']}均复用E:/edk2-samurai-out/kernel129已部署产物；rootfs130 {art['rootfs']['sha256']}、{art['rootfs']['bytes']} bytes在E:/edk2-samurai-out/kernel130。936包/770模块129匹配/21,135条目完整反向metadata与内容/双fsck/encoded降权实际写及四件套通过。服务/main.conf/runlevel增量已上机并实际暖启动验收，完整userdata未bulk刷入或擦除。

标准BlueZ服务need samurai-radio，start_pre有界samurai-bluetooth start严格DMS地址成功/读回后才启动原装daemon；default启用，AutoEnable=false，用户仍可控制完整BlueZ功能。地址与周边设备标识只在私有RAM/E现场，原NV/persist/凭据不变。两组LE12s/BR12s/auto20s实际D-Bus扫描、真实MGMT found及HCI Inquiry/LE命令通过。最终daemon标准服务running/controller off/Discovering false，无配对/连接/广告。

新暖boot无需手动service/address/network激活，实际新RAM DMS查询及DBus/MGMT读回一致。50.24秒6样本Phosh/Phoc原PID/radio/ADSP/5180/taint0、网关3/3/HTTPS200、11来源/770模块/boot-logdump-persist通过。init console warning0。新bootDPU0/GPU0，CRTC active1，但另10秒vsync3182不增长，无绘制负载；不能认定持续显示/GPU像素修复。BT UART启动错误累计2，power-on两组各新增1并QCA setup完成，错误未修复。SLPI offline/power0/PCM closed/amp idle failed0。

## 构建卷与清理

C /home/cy122/pmos-samurai-kernel129/128保留完整源码/build；本轮无新内核。E129 /home/cy122/pmos-samurai-rootfs129保存rootfs130、image-export130-fixed、新raw/restored，及旧129 template/export；两旧129 raw经新鲜payload/holes证明后删除{cleanup['allocated_bytes_removed']}字节，129完整sparse仍可恢复。原128模板/export/sparse在E126，两个128 raw已在129清理。稳定115/118/126/128/129回退保持，9未证明.o不删，本轮C删除0。

E129已sync卸载/read-only e2fsck0，118/122/126本轮未修改且实际未挂载。需要E129时在同一次WSL -d Ubuntu -u root先run reference/kernel129/ensure-rootfs-volume.py；操作E126先ensure-build-volume126。WSL会空闲退出、/run锁消失，不能假设上次挂载仍在。E129内余{vol['current_volume_inner_free_bytes']}、host C余{vol['host_c_free_bytes']}、E余{vol['host_e_free_bytes']}字节。新完整kernel clone需空间守卫，优先已有E构建卷，不resize/compact原VHD。

130 prepare/deploy/service-test/rootfs-pack/quiesce/reboot/cleanup/close全是已执行一次性脚本，不重放。所有作业terminal，当前手机正常service/桌面状态。首次临时DBus API调用错误、service verifier未定义ref及UARTchunk1/2区别、暖boot NM未ready断言、close未ensure失败都保留原输出并已纠正；不要覆盖原证据。

## 下一项

优先利用本次实际新暖启动taint0/DPU0/GPU0/CRTC active1，有界重复旧119签名非root真实GPU像素probe，先fresh取GUI/DRM/boot/帧计数，不混淆glmark exit0与像素通过。旧118真实33项2成功/25失败/6未知及CCU fault仍未修复；若再次难错完整留dump/实际rootcause线索后转下一15组缺口。不要把BT扫描当配对传输、TPG当物理camera、控制GNSS当fix。UART phase2 -84、物理camera/PM8008/HAL、GNSS真实fix、充电/休眠/指纹等继续开放。
''')
print('K130_DOCS_CHECKPOINT_UPDATED',flush=True)
