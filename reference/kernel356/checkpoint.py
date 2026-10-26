"""Record partial implementation and actual failures, preserving the full goal."""
from pathlib import Path
import json, re, shutil
import host

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
state=json.loads((HERE/'source-state.json').read_text())
crash=json.loads((P/'crash-r1-private.json').read_text())
console='\n'.join(crash['pstore'].values())
attempts=[dict(run='r1',passed=False,boot_changed=not crash['boot_matches'],
    old_pstore_permission_fault_observed='fsr=0x408, iova=0x00000000' in console,
    modem_watchdog_observed='crash detected in modem: type watchdog' in console,
    cleanup_not_proven=True)]
for run in ['r2','r3','r4']:
    r=json.loads((HERE/('boot-runtime-'+run+'-validation.json')).read_text())
    attempts.append(dict(run=run,terminal=r['terminal'],worker_process_observed=r['worker_process_observed'],
        passed=r['passed'],device_result=r['device_result'],taint_before=r['taint_before'],taint_after=r['taint_after'],
        reported_fault_count_excludes_later_identified_of_reference_errors=True))
r5=json.loads((P/'latest-r5-observation-private.json').read_text())
assert not r5['ssh_command_executed'], 'Reconcile the new device state before checkpointing'
attempts.append(dict(run='r5',worker_pid=7780,ssh_command_executed=False,worker_terminal_status_unknown=True,
    wrong_generic_physical=0x8b700000,corrected_candidate_not_launched=True))
(HERE/'boot-attempts.json').write_text(json.dumps(dict(stage=356,attempts=attempts,
    firmware_boot_verified=False,corrected_board_candidate_runtime_tested=False),indent=2)+'\n')
for relative,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
    path=ROOT/relative;d=json.loads(path.read_text())
    d.update(current_camera_evidence=prefix+'reference/kernel356/README.md',in_progress_stage=356,
        in_progress_evidence=prefix+'reference/kernel356/README.md',in_progress_installed=False,
        a5_icp_candidate_source_commit=state['commit'],icp_hardware_backend_installed=False,
        icp_firmware_boot_verified=False,icp_boot_candidate_implemented=True,
        board_camera_firmware_physical=0x9ab00000,board_camera_firmware_bytes=0x500000,
        corrected_board_carveout_runtime_tested=False,device_current_ssh_status='banner_exchange_timeout',
        current_device_runtime_state_verified=False,deployed_snapshot_is_historical=True,
        current_adaptation_goal_status='active')
    path.write_text(json.dumps(d,indent=2)+'\n')
entry='''356当前：A5 boot/IRQ/HFI/SYS_INIT/PING/PC_PREP/stop候选已实现，实机尚无完整握手。R1权限fault后自动重启，R2复位时序导致AHB WARN/taint512，R3读fwversion但无ACK，R4取指5MiB边界fault/500ms timer触发并清理。R5 worker7780 /var/lib/samurai/k356-boot-r5状态未知，USB/WiFi SSH banner超时，不能因观察失败重启事务。修正后第7构建未发送手机。

重要板级修正：原R5误用generic SM8150 0x8b700000（落入86200000大块no-map区）。匹配Realme官方19781源码23172a157...及当前k298 DTB实际为独立camera_mem 0x9ab00000/5MiB。已改memory-region-names firmware精确引用该节点，拒绝任意大区包含判断；离线DT合并解析通过，选择函数12项、内存host/ARM各51项、timer/PM9项通过。core229000/test66824 W1Werror构建通过。source354目录branch samurai-icp-a5-bootstrap356 commit3a485310daa7baed7d1f0d1798ded15cc85ad1ab，7文件clean，privateheader不入源。没有SYS_INIT/PING/PC_ACK/IPE图像成功。

当前不能声称设备相机仍正常或临时模块已移除。observe-boot.py r5只读观察既有事务，private356/latest-r5-observation-private.json保留失败；恢复后先读boot ID、R5 state/proc/pstore，再决定清理/实验，原305guard仍保留，新恢复356guard用于R2-R5。原始ELF/反汇编/日志/private物理数据不镜像。另发现主线drivers/iommu/of_iommu.c查询iommu-addresses时of_find_node_by_phandle缺of_node_put，动态DT有OF refcount ERROR；旧故障计数漏该项，当前worker已统计，需底层修正。完整目标含IPE会话/IOIQ/libcamera+原厂Gamma/LTM/前摄CCM、AE防频闪/模式/光学/同步/连续AF仍active。

'''
path=ROOT/'NEXT-SESSION.md';s=path.read_text();s=re.sub(r'^# 当前检查点：\d+', '# 当前检查点：356',s,count=1)
at=s.index('\n\n',s.index('\n\n')+2)+2;s=s[:at]+entry+s[at:];path.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('继续完整多摄/骁龙ISP goal。读WORKING-BOUNDARIES、NEXT-SESSION、reference/kernel356/README。356启动尚未成功，R5 worker7780状态未知且SSH握手超时，不能重放/盲重启。当前候选已修原R5错误物理地址8b700000为原厂19781和当前DTB共同确认的9ab00000/5M，改named memory-region；构建7通过但未发手机。source354/branch samurai-icp-a5-bootstrap356 commit3a485310daa7baed7d1f0d1798ded15cc85ad1ab。恢复先observe-boot.py r5读state/proc/boot/pstore，原guard不覆盖。可继续底层of_iommu.c节点引用泄漏修复及原固件分析。R1曾自动重启、R2 WARN taint512、R3无ACK、R4fault并清理；尚无完整FW启动或IPE图像成功。保持全部目标，不缩成启动单阶段。\n')
path=ROOT/'linux-port/camera/README.md';path.write_text('356当前：实现A5固件传输候选，纠正板级固件内存地址；实机启动失败，R5进程状态未知／SSH无响应，修正候选未发送。[356详情](../../reference/kernel356/README.md)。以下为历史。\n\n'+path.read_text())
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/README.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for source in paths:
    target=mirror/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
print('Recorded356 implementation, board correction, failed attempts and unknown R5 state; goal remains active.')
