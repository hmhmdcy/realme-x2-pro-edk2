from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parent;root=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel247')
for p in R.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
old=json.loads((R.parent/'kernel246/source-lock.json').read_text())
lock=dict(stage=247,local_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.iterdir()) if p.suffix in ['.py','.ps1','.initd']},oem_memshare_commit='23172a1571bd91156032cc9fef16284a82b63d2c',oem_memshare_sources=json.loads((P.parent/'kernel245/memshare-source/manifest.json').read_text()),cached_board_audit_file_hashes=old['cached_board_audit_file_hashes'],upstream_diag_commit=old['upstream_diag_commit'],android_packed_diag_commit=old['android_packed_diag_commit'],protocol_sources=old['protocol_sources'],gnss_layout_sources=old['gnss_layout_sources'],clock174_and_prx722_full_layouts_not_verified=True)
(R/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
health=json.loads((R/'final-health-validation.json').read_text());sat=[json.loads((R/(label+'-satellite-validation.json')).read_text()) for label in ['baseline-off','comparison-online']];cno=sum(s['cno_fields'] for phase in sat for s in phase['systems'].values());assert cno==2586 and sum(s['positive_cno'] for phase in sat for s in phase['systems'].values())==0
assert json.loads((R/'evidence-export-validation.json').read_text())['members']==53
(P/'current-checkpoint-private.json').write_text(json.dumps(dict(stage=247,goal_active=True,gnss_fix_verified=False,classification='progress',guard='/var/lib/samurai/k247-runtime/boot-id-private.txt',transport='reference/kernel247/host.py',normal_linux_restart_request_count=1,raw_cno_fields=cno,raw_positive_cno=0,archive_members=53,snapshot_members=[12,12],user_reports_never_disassembled=True,user_reports_complete_assembly=True,last_confirmed_android_fix='unknown',environment='indoor open window',no_user_question_pending=True,health=health,next_work=['Prioritize before-modem configured client1/proc0 query/real provider comparison: startup query0x24 was seen; observer returned INVALID_ID while locked OEM board expects initial5MiB. GPS0 requests0 does not exclude dependency on client1.','Configured-size-only runtime reannouncement observed30.08s without requests; no extra GNSS run. Do not claim the candidate was adopted or is a full provider.','If implementing physical loan, reserve/allocate owned contiguous memory and verify SCM HLOS to MSS_MSA RW. Hold ownership while modem can DMA. No blind MSM8916 address/2MiB copy. Cached kernel feasibility is private; current source has QMI/SCM/CMA enabled and exported symbols, but module build/current inventory still must be checked.','Continue exact PRX722/Clock174/Config field and real LNA wiring analysis. The complete handset has no confirmed Android reception baseline; no hardware fault assumption.','Current boot247 guard;246 and earlier invalid. All workers/hooks/endpoints closed, WiFi and DSPs running, NV source preserved.']),indent=2)+'\n')
p=root/'NEXT-SESSION.md';archive=root/'archive/NEXT-SESSION-through246-2026-10-17.md';assert not archive.exists();archive.write_bytes(p.read_bytes());lines=p.read_text(encoding='utf-8-sig').splitlines()
lines[2]='2026-10-17 GNSS247：首次捕获启动期MEMSHARE 0x24/client1/proc0；OEM板源初始5MiB，观察器回INVALID_ID，因果待验。两轮2586个原始C/No全0。当前247启动，goal active。[247](reference/kernel247/README.md)。其它验收沿用240。'
for i,line in enumerate(lines):
 if line.startswith('246启动/boot235/Image183'):
  lines[i]='247启动/boot235/Image183，guard `/var/lib/samurai/k247-runtime/boot-id-private.txt`，246及更早失效。运输`reference/kernel247/host.py`，私有USB端点`E:/edk2-samurai-out/kernel247`，原严格SSH密钥保持。53项归档及两份12项快照核验；所有worker/hook/DIAG/52退出，MMpower1/DMSoffline/锁MT、NV源哈希保持，三DSP/Wi-Fi正常、taint/fault0。'
 if line.startswith('240核对（246未全机重验）'):lines[i]=line.replace('246未全机重验','247未全机重验')
 if line.startswith('GNSS见[246]'):
  lines[i]='GNSS见[247](reference/kernel247/README.md)：启动前发布52并回读，416.82秒仅收client1大小查询；OEM板源5MiB/启动分配，当前回INVALID_ID，尚未完整复现。GPS请求0不能排除该依赖。大小候选重发公告30秒0请求，未再搜星；下一步验证启动期client1配置及自有内存/SCM provider，不搬用其它SoC地址。1240份日志/2586个原始C/No全0，ClkFreqUnc1500→94仍无fix。Clock174/PRX722全字段、LNA接线待核；ADC/谱推断不证明物理链路。用户确认未拆机、装机完整，Android上次正常定位未知。'
text='\n'.join(lines)+'\n';assert len(text.encode())<=6500,len(text.encode());p.write_text(text)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text(encoding='utf-8-sig').replace('246于2026-10-17继续GNSS专项','247于2026-10-17继续GNSS专项').replace('[246真实RF/Clock与原始C/No](../../reference/kernel246/README.md)','[247启动MEMSHARE与OEM配置差异](../../reference/kernel247/README.md)');lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| GNSS定位 |'):
  lines[i]='| GNSS定位 | 247普通Linux重启；52/v1/i1在modem前发布及独立回读，416.82秒捕获0x24/client1/proc0大小查询1次。OEM板源初始5MiB/启动分配，观察器回INVALID_ID；无物理内存或SCM动作。两轮90秒同DIAG端点共1240日志、2586个原始C/No全0，QMI768/3912字段全0。53项归档及两份12项快照核验，worker/hook/DIAG/52退出；MMpower1/DMSoffline/锁MT、NV源保持，三DSP/Wi-Fi正常、fault/taint0 | 定位不可用，goal active。client1服务差异尚未建立GPS因果；GPS0请求0不能排除依赖。大小候选运行期重发公告30秒0请求，未再搜星；优先验证启动期完整配置及自有内存/SCM provider。Clock174/PRX722未全解，ADC/谱推断不证明LNA正常。用户确认未拆机/装机完整，最后Android正常定位未知；当前guard k247-runtime，246及更早失效，其余功能未全机重验 |'
p.write_text('\n'.join(lines)+'\n')
p=root/'DOCS-INDEX.md';s=p.read_text(encoding='utf-8-sig').replace('| GNSS标准链路、相关机型与modem文件服务 | [246','| GNSS标准链路、相关机型与modem文件服务 | [247启动MEMSHARE与OEM配置差异](reference/kernel247/README.md)、[246');p.write_text(s)
missing=[];checked=0
for p in [R/'README.md',root/'NEXT-SESSION.md',root/'DOCS-INDEX.md',root/'linux-port/docs/HARDWARE-STATUS.md']:
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  target=target.split('#',1)[0];checked+=1
  if target and not (p.parent/target).exists():missing.append([str(p.relative_to(root)),target])
assert not missing,missing
report=dict(stage=247,all_phase_python_sources_compile=True,local_links_checked=checked,missing_links=missing,checkpoint_bytes=len((root/'NEXT-SESSION.md').read_bytes()),locked_sources=len(lock['local_sources']),current_guard='k247-runtime',goal_active=True,gnss_fix_verified=False,question_pending=False)
(R/'documentation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
