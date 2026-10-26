from pathlib import Path
import hashlib,json,re,urllib.request
R=Path(__file__).resolve().parent;root=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel245')
for p in R.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
url='https://raw.githubusercontent.com/linux-mobile-broadband/libqmi/main/data/qmi-service-pdc.json';p=P/'qmi-service-pdc.json'
if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=30).read())
b=p.read_bytes();assert b'Get Selected Config' in b and b'0x22' in b and b'Get Config Info' in b
lock=dict(stage=245,local_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(R.iterdir()) if p.suffix=='.py'},upstream_diag_commit='23c12c167e93215853af4e59c021551767f6fec8',android_diag_commit='bf51f920fdef2acb189f5c2e282148279a1f12c9',memshare_sources=json.loads((P/'memshare-source/manifest.json').read_text()),pdc_idl=dict(url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()),log_code_header_sha256='2d281226995f78c7add768088c1f304bf57157eede91df62b5c02726260ff619')
(R/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
health=json.loads((R/'final-health-validation.json').read_text());(P/'current-checkpoint-private.json').write_text(json.dumps(dict(stage=245,goal_active=True,gnss_fix_verified=False,guard='/var/lib/samurai/k244-runtime/boot-id-private.txt',health=health,all_workers_terminal=True,temporary_servers_removed=True,archive_members=81,next_step='First-modem-startup persistent DIAG with ten verified RF/clock log IDs; confirm UTC before GNSS. Current CMD replies do not prove data logging recovery.'),indent=2)+'\n')
p=root/'NEXT-SESSION.md';old=p.read_bytes();archive=root/'archive/NEXT-SESSION-through244-2026-10-17.md';assert not archive.exists();archive.write_bytes(old);lines=old.decode('utf-8-sig').splitlines()
lines[2]='2026-10-17 GNSS245：保持244启动/Linux。MT→NONE未恢复接收；原端口恢复DIAG VERSION，日志仍0包。memshare观察113秒请求0，active配置ID匹配原机MBN SHA1。仍无正SNR/TRACK/fix，goal active。[245](reference/kernel245/README.md)。其它验收沿用240。'
for i,line in enumerate(lines):
 if line.startswith('244启动/boot235/Image183'):
  lines[i]='244启动/boot235/Image183，guard `/var/lib/samurai/k244-runtime/boot-id-private.txt`，236及更早无效。运输`reference/kernel244/host.py`，私有端点仍在`E:/edk2-samurai-out/kernel244`，245证据另存kernel245；严格原SSH密钥。245全部worker退出、81项归档核验，DIAG/52服务0、锁MT、NV源哈希保持、三DSP/Wi-Fi正常、taint/fault0；无新重启/刷写。'
 if line.startswith('建议优先处理Snapshot'):
  lines[i]=line.replace('建议优先处理Snapshot缓冲所有权和降帧，拍照、切换及长稳可按诊断需要安排。','Snapshot缓冲回收和降帧待续，当前优先GNSS。')
 if line.startswith('GNSS见[244]'):
  lines[i]='GNSS续作见[245](reference/kernel245/README.md)：五轮90秒共3784个有效SNR字段全0，缺列表不计0；含锁NONE、DIAG缓存/feature重发、MEMSHARE公布服务观察。244首次启动的270份测量仍NumValidReports0，本轮未恢复日志。下一步在modem首次启动前保持十类RF/Clock日志端点，UTC准备后再比较；必要时启动阶段观察MEMSHARE请求。当前0请求不排除启动需求；active ID匹配MBN SHA1不等于全部RF/NV回读。243开窗/WLAN和UFS归因保持；不猜GPIO/NV。'
s='\n'.join(lines)+'\n';assert len(s.encode())<=6500,len(s.encode());p.write_text(s)
p=root/'linux-port/docs/HARDWARE-STATUS.md';s=p.read_text(encoding='utf-8-sig').replace('244于2026-10-16继续GNSS专项','245于2026-10-17继续GNSS专项').replace('[244真实DIAG测量](../../reference/kernel244/README.md)','[245锁/DIAG/MEMSHARE与运行配置](../../reference/kernel245/README.md)');lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| GNSS定位 |'):
  lines[i]='| GNSS定位 | 245保持244启动/Linux，五轮90秒共3784个有效SNR字段全0/SEARCH，含MT→NONE对照后恢复MT。原DIAG端口可回VERSION，但缓存/feature重发后日志0包；244首次启动270份真实测量均NumValidReports0保持。临时MEMSHARE服务113秒请求0、无物理分配/地址/SCM变更并撤销。两类active ID等于原机对应MBN SHA1，未激活配置。81项归档核验、所有worker/临时服务退出、NV源哈希保持，三DSP/Wi-Fi正常、fault/taint0 | 定位仍不可用，goal active。下一步首次modem启动的持续RF/Clock采集，先确认UTC准备；0日志不证明RF关闭，0内存请求不排除启动需求，ID匹配不等于全部NV回读。仍无LNA/XO根因证据。当前guard为k244-runtime，236失效；其它功能未全机重验 |'
p.write_text('\n'.join(lines)+'\n')
p=root/'DOCS-INDEX.md';s=p.read_text(encoding='utf-8-sig').replace('最后整理：2026-10-16','最后整理：2026-10-17').replace('| GNSS标准链路、相关机型与modem文件服务 | [244','| GNSS标准链路、相关机型与modem文件服务 | [245锁/DIAG/MEMSHARE与active MCFG](reference/kernel245/README.md)、[244');p.write_text(s)
bad=[];checked=0
for p in [R/'README.md',root/'NEXT-SESSION.md',root/'DOCS-INDEX.md',root/'linux-port/docs/HARDWARE-STATUS.md']:
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  if '://' in target or target.startswith('#'):continue
  target=target.split('#',1)[0];checked+=1
  if target and not (p.parent/target).exists():bad.append([str(p.relative_to(root)),target])
assert not bad,bad
report=dict(stage=245,locked_sources=len(lock['local_sources']),checkpoint_bytes=len((root/'NEXT-SESSION.md').read_bytes()),local_links_checked=checked,missing_links=bad,goal_active=True,gnss_fix_verified=False,all_phase_python_sources_compile=True)
(R/'documentation-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
