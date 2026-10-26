from pathlib import Path
import ast,json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel211');repo=here.parents[1]
proof=json.loads((here/'pre-reboot-recovery-validation.json').read_text());assert proof['full_quiesce'] and proof['known_mclk_warnings_preserved']==2 and proof['private_archive_and_all_members_verified']
build=json.loads((here/'build-package-validation.json').read_text());assert build['firmware_only_dtb_changed'] and build['boot_sha256']=='c3bf043f2eea0c5f8e42cc8cac621ccfba023b181e400d0919174b87e3d37ba6'
text=(here.parent/'kernel210/flash-boot.py').read_text().replace("image=out/'boot-partition-k210-front.img';rollback=out.parent/'kernel204/boot-partition-k204-bt-wake.img'","image=out/'boot-partition-k211-sensor-domain.img';rollback=out.parent/'kernel210/boot-partition-k210-front.img'").replace('stage=210','stage=211')
ast.parse(text);(here/'flash-boot.py').write_text(text)
p=here/'prepare-new-endpoint.py';text=p.read_text();old="assert json.loads((p/'fastboot-reboot-private.json').read_text())['request_count']==1";assert old in text
text=text.replace(old,"assert json.loads((p/'flash-validation.json').read_text())['boot_flash_success'] and (p/'fastboot-reboot-request-private.json').exists()")
ast.parse(text);p.write_text(text)
p=here/'connect-newboot.py';text=p.read_text().replace("assert (host.PRIVATE/'fastboot-reboot-private.json').exists()","assert (host.PRIVATE/'fastboot-reboot-request-private.json').exists()")
text=text.replace('211 guarded warm reboot completed without flashing.','211 guarded boot-only sensor-domain update and new boot completed.')
ast.parse(text);p.write_text(text)
p=here/'collect-newboot.py';text=p.read_text().replace('89242ade44ddaebf2b124d3bb5e9bd6597d0c818488b1e84d719d36a5a5023c0',build['boot_sha256']).replace('boot210_logdump183_persist_nv_readback_exact','boot211_logdump183_persist_nv_readback_exact').replace('partitions_flashed=[]',"partitions_flashed=['boot']")
target="assert (sensor/'driver').resolve().name=='imx471'"
assert target in text;text=text.replace(target,target+"\nassert (sensor/'of_node/power-domains').read_bytes()==Path('/sys/bus/platform/devices/ac4b000.cci/of_node/power-domains').read_bytes()\ngenpd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text();(out/'sensor-domain-genpd-private.txt').write_text(genpd)\nassert '7-0010' in genpd")
text=text.replace('static_camera_bound=True,','static_camera_bound=True,sensor_titan_top_domain_attached=True,')
ast.parse(text);p.write_text(text)
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='211 cleanup recovered: all6 camera modules and3 DSPs offline,DRM inactive, only exact2 captured MCLK WARNs/taint512 retained; all native pre-reboot files archived/member-verified. Candidate boot c3bf043f/DTB6f9f5b0f changes only sensor power-domain; schema and firmware checks pass. No transition yet.',next='Run reboot-after-warning once using fresh quiesce proof, then fresh fastboot identity/boot-only flash211. Readback/new guard, verify own sensor-domain runtime wake and actual user capture.',transition_pending=False)
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
text=(repo/'NEXT-SESSION.md').read_text();start=text.index('2026-10-15，');end=text.index('\n\n',start)
text=text[:start]+'2026-10-15，阶段211进行中。CROP与heap修复已部署；清理发现MCLK独立恢复缺供电域，保留WARN2/taint512，并通过CCI正常PM保持对照。已补传感器TITAN_TOP域；候选boot c3bf043f…只改变该DT属性，schema/固件核对通过。当前已恢复完整停用/归档，尚未发切换。下一步只刷boot后验独立唤醒及用户态取流。[211进展](reference/kernel211/README.md)、[210快照](archive/NEXT-SESSION-through210-2026-10-15.md)。'+text[end:]
start=text.index('- 211当前现场：');end=text.index('\n',start)
text=text[:start]+'- 211当前现场：六个相机模块已卸载，三个DSP全部offline、GUI/GNSS watcher已停、DRM inactive。完整恢复检查明确保留两次MCLK WARN/taint512，拒绝其它/新增警告；私人归档逐成员已核对。原211 quiesce中途失败及全部对照日志保留。新boot未发，不能重跑原脚本；应使用reboot-after-warning.py及其一次性marker。'+text[end:]
(repo/'NEXT-SESSION.md').write_text(text)
print('Concrete211 domain boot, recovery transition and new-boot checks prepared; no reboot or flash sent yet.')
