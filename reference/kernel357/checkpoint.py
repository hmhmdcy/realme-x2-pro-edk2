from pathlib import Path
import json, re, shutil

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel357')
state=json.loads((HERE/'source-state.json').read_text())
assert state['tracked_clean'] and not state['installed']
for name in ['node-lifetime-validation.json','kernel-build-validation.json']:
    assert json.loads((HERE/name).read_text())['passed']
events=[json.loads(l) for l in (P/'passive-r2.events.jsonl').read_text().splitlines()]
passive=next(e for e in events if e['event']=='finished')
logs=(P/'passive-r2.txt').read_text()
reset=json.loads((P/'system-reset-r1-private.json').read_text(encoding='utf-8-sig'))
sahara=json.loads((P/'sahara-reset-r1-private.json').read_text(encoding='utf-8-sig'))
report=dict(stage=357,eud_passive_frames=passive['frames'],cpu5_rcu_stall_observed='detected stalls' in logs,
    cpu5_nmi_nonresponse_observed="CPUS still haven't responded to the NMI: 5" in logs,
    ssh_auth_cross_cpu_bpf_wait_observed=all(x in logs for x in ['sshd-auth.pam','kick_all_cpus_sync','bpf_arch_text_copy','do_seccomp']),
    exact_cpu5_program_counter_not_observed=True,msm_reset_assert_and_release_written=reset['assert_written'] and reset['release_written'],
    observed_post_reset_sahara_hello=True,sahara_protocol_version=2,sahara_mode=0,
    sahara_reset_acknowledged=sahara['reset_acknowledged'],linux_boot_restored=False,
    last_observed_main_usb_mode='05c6:9008',eud_com_disabled=True,eud_usb_forwarding_released=True,
    r5_terminal_report_never_observed=True,r5_old_linux_worker_cannot_run_in_current_sahara_mode=True,
    programmer_uploaded=False,partition_commands_sent=0,installed_kernel_or_dt_changed=False,
    user_onsite_force_restart_requested=True,full_goal_status='active')
(HERE/'device-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
    path=ROOT/relative;d=json.loads(path.read_text())
    d.update(current_camera_evidence=prefix+'reference/kernel357/README.md',in_progress_stage=357,
        in_progress_evidence=prefix+'reference/kernel357/README.md',in_progress_installed=False,
        iommu_node_lifetime_candidate_commit=state['commit'],iommu_node_lifetime_fix_installed=False,
        device_current_ssh_status='unavailable_device_in_9008',device_current_usb_mode='05c6:9008',
        current_device_runtime_state_verified=False,deployed_snapshot_is_historical=True,
        current_adaptation_goal_status='active')
    path.write_text(json.dumps(d,indent=2)+'\n')
entry='''357当前：公共of_iommu_get_resv_regions节点引用泄漏已修。将循环np改__free(device_node)=NULL，正常/zero-length continue/alloc失败均自动put。原/新实际完整函数9场景，旧泄漏409、新0；ARM64 of_iommu.o W1Werror 12.72sec通过/27736bytes，未装、需未来统一Image。source354目录当前branch samurai-iommu-node-lifetime357 commitba61a62293e0f6bc5838c06f2e85e033e3d702a8，父3563a485310...，一行/459bytepatch/clean。

重要设备状态已变化：EUD成功接收924帧，直接看到CPU5 RCU stall/NMI无响应，sshd-auth.pam等待kick_all_cpus_sync/BPF/seccomp；CPU5实际PC未知。EUD CtrlU/换行各新回执、真实ttyEUD0登录提示；用既有私存凭据登录一次无shell/无明确拒绝。private357/login-auth-secret-*及后续pstore可能含密码输入的debug十六进制，严禁原样输出/镜像。

为恢复按主机已有Qualcomm eud_msm_reset bit0低/100ms/高发一次硬件复位，旧Linux退出/NCM消失，主USB进入9008 COM16；读HELLO48bytes v2 mode0。按bkerler原cmd_reset发一次Sahara命令7，得命令8长度8确认，但随后仍9008，无Linux/fastboot。没有programmer上传、分区/NV操作或改boot。已com-off/detach，9505消失，USBIP已释放，9501和9008保留。不可重复reset-eud-msm.ps1/reset-sahara.ps1；已有一次操作marker，先查状态。旧R5进程不在当前Sahara环境运行，仍无它的正常终态/清理报告。

用户不在现场，已异步请回现场后按realme官方方法电源+音量上>10秒，启动画面后松开/保持USB再告知。现场请求pending期间继续主机原厂固件适配；不能宣称设备已恢复或goal完成。恢复后先读boot/pstore/R5state+临时module/fw/DT，原guard保留；356修正9ab00000/5M命名memory-region候选build7从未发机，尚无SYS_INIT/PING/PC_ACK或IPE图像。357文档/脱敏证据镜像，原件/secret/raw logs仅私存。完整goal含实际ICP/IPE/libcamera、原厂Gamma/LTM/前CCM、AE防频闪/模式/光学/同步/连续AF继续active。

'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text();s=re.sub(r'^# 当前检查点：\d+','# 当前检查点：357',s,count=1)
at=s.index('\n\n',s.index('\n\n')+2)+2;path.write_text(s[:at]+entry+s[at:])
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/ISP goal。当前357，读WORKING-BOUNDARIES/NEXT-SESSION/reference/kernel357/README。设备现在9008 COM16：EUD证实CPU5 stall/NMI无响应，SSHauth跨核BPF等待；一次EUD MSM reset后进入9008，一次SaharaRESET得到ACK但未恢复。已退出EUDCOM/USBIP，无programmer/分区/boot操作。用户不在现场，已异步请求电源+音量上>10秒现场重启，等待期间继续主机原固件适配。不要重复复位marker；先读实际USB。private357/login-auth-secret-*及pstore可能含密码debug字节，勿打印/镜像。当前source354路径branch samurai-iommu-node-lifetime357 commitba61a622...父3563a485310...；公共IOMMU引用修正9回归旧409/new0+ARM64W1Werror对象通过未装。356修板级固件physical9ab00000/5M+named memory-region的build7未发机，ICP/IPE仍未通。恢复先查boot/pstore/R5state/临时资源，保留原guard。全goal不缩小，主机可继续原厂AE曝光表/防频闪及ISP调校实现。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('357当前：公共IOMMU引用泄漏修正已构建、未安装；手机CPU停滞后的远程恢复停在9008，现场强制重启请求待回应。[357详情](../../reference/kernel357/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
    target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded357 common IOMMU fix and unrecovered9008 state; full camera/ISP goal remains active.')
