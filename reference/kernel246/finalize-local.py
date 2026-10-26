from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parent;root=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel246')
for p in R.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
lock=dict(stage=246,local_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.iterdir()) if p.suffix in ['.py','.ps1','.initd']},upstream_diag_commit='23c12c167e93215853af4e59c021551767f6fec8',android_packed_diag_commit='bf51f920fdef2acb189f5c2e282148279a1f12c9',protocol_sources=json.loads((P.parent/'kernel244/protocol-source/manifest-private.json').read_text()),gnss_layout_sources=json.loads((P.parent/'kernel244/gnss-layouts/manifest-private.json').read_text()),cached_board_audit_file_hashes={x['file']:x['source_sha256'] for x in json.loads((P/'cached-oem-rf-resource-audit-private.json').read_text())},oem_r_diag_fetch_failed_not_used=True,clock174_and_prx722_full_layouts_not_verified=True)
(R/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
health=json.loads((R/'final-health-validation.json').read_text());(P/'current-checkpoint-private.json').write_text(json.dumps(dict(stage=246,goal_active=True,gnss_fix_verified=False,guard='/var/lib/samurai/k246-runtime/boot-id-private.txt',transport='reference/kernel246/host.py',new_linux_boot_confirmed=True,normal_linux_reboot_request_count=1,health=health,archive_members=59,snapshot_members=[11,11],raw_cno_fields=2607,positive_raw_cno=0,physical_assembly_and_last_android_fix_question_pending=True,next_work=['Continue interpreting actual Clock174/PRX722/Config layouts using primary evidence. ADC word offsets116/120 each match180/180 independently decoded PQWM1 values but this is empirical.','Review real antenna/LNA board control; cached board rfa/rf_clk3 belongs to WLAN, generic GNSS UART comment is not internal-GNSS wiring.','Current boot guard is246, DMS offline/MMpower1; do not reuse244 guards. If more live DIAG required, preserve first-startup endpoints for all planned phases instead of premature close.','Spectrum13x25 arithmetic allows three base integers, not just GPS. Power units and flags not validated; do not infer strong interference or physical LNA voltage.']),indent=2)+'\n')
checkpoint_file=P/'current-checkpoint-private.json';checkpoint=json.loads(checkpoint_file.read_text());checkpoint['next_work'].insert(0,'Prioritize MEMSHARE52/v1/i1 observation before first modem startup.245 only published it during a running modem;246 startup listener was DIAG only. Observe GPS client0 and actual size before allocating physical memory or changing SCM ownership; no blind MSM8916 2MiB copy.');checkpoint_file.write_text(json.dumps(checkpoint,indent=2)+'\n')
p=root/'NEXT-SESSION.md';archive=root/'archive/NEXT-SESSION-through245-2026-10-17.md'
if not archive.exists():archive.write_bytes(p.read_bytes())
lines=archive.read_text(encoding='utf-8-sig').splitlines();lines[2]='2026-10-17 GNSS246：普通Linux重启后取得1245份GNSS/RF/Clock日志；2607个原始C/No全0，online下ClkFreqUnc原值1500→94仍无fix。当前246启动、guard/运输已更新，goal active。[246](reference/kernel246/README.md)。其它验收沿用240。'
for i,line in enumerate(lines):
 if line.startswith('244启动/boot235/Image183'):
  lines[i]='246启动/boot235/Image183，guard `/var/lib/samurai/k246-runtime/boot-id-private.txt`，244及更早失效。运输`reference/kernel246/host.py`，私有USB端点`E:/edk2-samurai-out/kernel246`，保留原严格SSH密钥。59项完整归档及两份11项快照核验；hook/DIAG关闭，MMpower1/DMSoffline、锁MT、NV源哈希保持，三DSP/Wi-Fi正常、taint/fault0。'
 if line.startswith('240核对（244未重做全机验收）'):lines[i]=line.replace('240核对（244未重做全机验收）','240核对（246未全机重验）')
 if line.startswith('GNSS续作见[245]'):
  lines[i]='GNSS见[246](reference/kernel246/README.md)：同DIAG端点跨两轮90秒，UTC先准备；原始2607个C/No全0，online列表更连续仍无TRACK/fix。Clock/PRX的174/722字节版式未全解；ClkFreqUnc1500→94不证明物理XO锁定，非A/B/A。ADC经验映射116/120各180/180，不证明LNA/天线正常。下一步核实际天线/LNA链路及对应字段；谱日志仅算术推断。装机状态与Android上次定位已询问待反馈；245NONE/memshare0请求/MCFG SHA1证据保留。'
text='\n'.join(lines)+'\n';text=text.replace('245NONE/memshare0请求/MCFG SHA1证据保留。','245NONE/memshare0请求/MCFG SHA1证据保留；MEMSHARE启动前请求待观察。');assert len(text.encode())<=6500,len(text.encode());p.write_text(text)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text(encoding='utf-8-sig').replace('245于2026-10-17继续GNSS专项','246于2026-10-17继续GNSS专项').replace('[245锁/DIAG/MEMSHARE与运行配置](../../reference/kernel245/README.md)','[246真实RF/Clock与原始C/No](../../reference/kernel246/README.md)');lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| GNSS定位 |'):
  lines[i]='| GNSS定位 | 246普通Linux重启，未刷写；首次握手两ID成功、同端点跨两轮90秒取得1245份RF/Clock/测量日志，含Clock186、PRX182、Spectrum154。严格v0/长度/stride解析2607个原始C/No全0；QMI首轮766/online3872字段全0。UTC先准备、ClkFreqUnc原值1500→94；ADC经验offset116/120各180/180匹配NMEA。59项归档及两份11项快照核验，全部worker/hook/DIAG退出，MMpower1/DMSoffline/锁MT、NV源哈希保持，三DSP/Wi-Fi正常、fault/taint0 | 定位仍不可用，goal active。已确认零值存在modem原始记录，非仅上层解码；LNA/天线/RF配置与时钟物理状态仍待核。Clock174/PRX722未获完整字段定义，谱数据仅算术推断，不猜bit/功率单位。装机及Android最后定位基线待反馈。当前guard k246-runtime，244及更早失效；其余功能未全机重验 |'
p.write_text('\n'.join(lines)+'\n')
p=root/'DOCS-INDEX.md';s=p.read_text(encoding='utf-8-sig').replace('| GNSS标准链路、相关机型与modem文件服务 | [245','| GNSS标准链路、相关机型与modem文件服务 | [246真实RF/Clock与modem原始C/No](reference/kernel246/README.md)、[245');p.write_text(s)
missing=[];checked=0
for p in [R/'README.md',root/'NEXT-SESSION.md',root/'DOCS-INDEX.md',root/'linux-port/docs/HARDWARE-STATUS.md']:
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  target=target.split('#',1)[0];checked+=1
  if target and not (p.parent/target).exists():missing.append([str(p.relative_to(root)),target])
assert not missing,missing
report=dict(stage=246,all_phase_python_sources_compile=True,local_links_checked=checked,missing_links=missing,checkpoint_bytes=len((root/'NEXT-SESSION.md').read_bytes()),locked_sources=len(lock['local_sources']),current_guard='k246-runtime',goal_active=True,gnss_fix_verified=False)
(R/'documentation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
