from pathlib import Path
import json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
for name in ['firmware-sfr-validation.json','start-regression-validation.json','diagnostic-regression-validation.json','stop-regression-validation.json','intree-build-validation.json']:
 assert json.loads((HERE/name).read_text())['passed']
source=json.loads((HERE/'source-state.json').read_text());assert source['applied'] and not source['installed']
for rel,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/rel;d=json.loads(p.read_text())
 d.update(latest_work_stage=368,in_progress_stage=368,in_progress_installed=False,in_progress_evidence=prefix+'reference/kernel368/README.md',
  icp_response3_sfr_error_path_proven_in_original_firmware=True,icp_response3_sfr_evidence=prefix+'reference/kernel368/firmware-sfr-validation.json',
  a5_icp_candidate_source_commit=source['commit'],a5_icp_candidate_source_branch=source['branch'],a5_icp_candidate_source_installed=False,
  a5_terminal_sfr_error_candidate_built=True,a5_terminal_sfr_candidate_evidence=prefix+'reference/kernel368/intree-build-validation.json',
  a5_dev_coredump_candidate_bytes=568,a5_dma_before_powerdown_candidate=True,
  icp_next_step='Pre-arm bounded devcoredump collection for a fresh targeted SFR/teardown-order diagnostic; never replay366',
  icp_watchdog_root_cause_verified=False,current_adaptation_goal_status='active',full_camera_runtime_goal_verified=False)
 if 'maintained_commit' in d:d.update(maintained_branch=source['branch'],maintained_commit=source['commit'])
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'NEXT-SESSION.md';s=p.read_text()
s=s.replace('# 当前检查点：367（基线恢复，完整多摄／ISP目标 active）','# 当前检查点：368（SFR故障处理候选已构建，现机367基线）',1)
anchor='## 实际新结果\n'
note='''## 368最新进展（未部署）

原厂SendSfrMessage完整348字节指令执行11路径证明：先处理SFR，再在1b9f2向e001004c发布3；3为错误路径，不能等待它转1或发SYS_INIT。cache/log/format/power为明确桩，不冒充整RTOS。新core以3为终态失败，清理前用标准devcoredump保存568字节有界LE快照；SFR受声明/实际分配双边界限制。DMA别名及backing改在PM供电释放前回收，unmap失败保留PM引用，watchdog原因仍未证明。

实际start13组、stop7组、诊断helper与解码器ASan/UBSan通过，旧版4个反例保留。源码source354现在samurai-a5-terminal-sfr368／9c60745372258f2f37374862a06c9fd09eeaf240；只有A5后端一个C文件变更，k363实际in-tree core W1/Werror零诊断（232352字节），共享输出/config恢复，未部署。当前设备/guard/包/DT保持下述367基线，没有再次CPU释放或重启。

定点只读专用9ab00000固件RAM的一个4KiB代码页与ELF不符，停止未读异常状态页；不能据此恢复实际SFR或判断异常寄存器。raw数据私存368。解码器reference/kernel368/decode-start-dump.py只读已收集的私有devcoredump，不自动操作设备。

下一步以新的针对性诊断预先收集devcoredump，取得实际SFR原因并验证回收次序；不重放366，不在未保全错误前重复启动。尚无完整SYS_INIT/PING/PC_ACK、IPE或完整多摄校准。详见reference/kernel368/README.md。

'''
assert anchor in s and '## 368最新进展' not in s;s=s.replace(anchor,note+anchor,1)
s=s.replace('完整内核源/mnt/samurai-full282/source354，分支samurai-icp-board-dt365，提交e217016006e609333a715c10f2f3e442dc4da95f；','实际DT来源提交e217016006e609333a715c10f2f3e442dc4da95f（365），维护检出source354现在为上列368候选；')
p.write_text(s)
(ROOT/'NEXT-SESSION-PROMPT.md').write_text('从368候选／现机367基线继续active多摄/ISP目标。先读NEXT-SESSION.md、WORKING-BOUNDARIES.md、reference/kernel368/README.md。原厂SendSfrMessage实际指令11路径确认HFI3是SFR错误；新core终态错误+568字节标准devcoredump+先退DMA后PM已在source354/9c60745372提交，in-tree k363 W1/Werror通过，13start/7stop及dump/decoder模型通过，未部署。现机boot366/DT365/Image363、r29/r24，host367 guard保持，没有本轮CPU释放/重启。DDR单页不匹配所以不读残留异常页。下一步预先收集dump的新针对性SFR/回收诊断，不重放366；watchdog原因、完整HFI/IPE、2MP身份、其它模式和光学/同步/连续AF仍开放。固件/校准/日志私存，storage284挂ext4，SDK bind串行。\n')
p=ROOT/'sessions/INDEX.md';s=p.read_text();s=s.replace('## 最新交接\n','## 最新交接\n\n- [368原厂SFR响应3与错误诊断／DMA回收候选](../reference/kernel368/README.md)\n',1);p.write_text(s)
p=ROOT/'DOCS-INDEX.md';s=p.read_text().replace('[367基线恢复与ICP/DT实测](reference/kernel367/README.md)','[368SFR错误诊断与回收候选](reference/kernel368/README.md)');p.write_text(s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/p for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','sessions/INDEX.md','DOCS-INDEX.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']]
for p in paths:
 assert 'private' not in p.name.lower()
 dest=mirror/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
print('368 candidate checkpoint mirrored; actual deployed367 baseline unchanged, goal remains active.')
