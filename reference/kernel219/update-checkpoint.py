from pathlib import Path
import json

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel219')
# Correct a method label, never alter original measured values or private stdout.
p=here/'1928x1088-timing-vblank-1-validation.json'
r=json.loads(p.read_text())
r.update(dma_sync_read_start_end=False,no_cpu_pixel_buffer_access=True,
         method_annotation_correction='Metadata-only cam capture; original inherited DMA-read label was incorrect. Original private stdout retained.')
p.write_text(json.dumps(r,indent=2)+'\n')
capsule=dict(stage=219,state='boot219 and pixel-array timing module verified; native full RAW/RGB experimental capture passed',
 guard='/var/lib/samurai/k219-runtime/boot-id-private.txt',module_sha256='e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1',
 boot_candidate_sha256='156f0370fff6a65babc14738a62e4e2291594fe74f680cf3f62317dd0291198a',transition_pending=False,
 next='Finish existing full r6 build (exec session 40635), validate all 13 APKs and retained signatures/features, stage coherent 7-package upgrade with r5 rollback, then default system-heap RGB regression',
 full_peripheral_goal_active=True,installed_framework='99990.7.2-r5',installed_config='0.1.0-r0',experimental_fullres_default='N',
 active_build_session=40635,active_build_log=str(private/'full-r6-build-private.log'))
(private/'current-work-private.json').write_text(json.dumps(capsule,indent=2)+'\n')
status=repo/'linux-port/docs/HARDWARE-STATUS.md';text=status.read_text()
start=text.index('用途：');end=text.index('\n\n',start)
text=text[:start]+'用途：当前硬件验收清单。最后核对2026-10-16，阶段219。已部署boot219与时序修复模块；真实4MP/16MP RAW及实验16MP CPU RGB取流通过。手机仍为214完整r5包；默认4MP RGB分配失败已定位，r6完整包构建中，全外设goal开放。[219报告](../../reference/kernel219/README.md)、[检查点](../../NEXT-SESSION.md)、[边界](../../WORKING-BOUNDARIES.md)。'+text[end:]
lines=text.splitlines()
for i,line in enumerate(lines):
 if line.startswith('| 摄像头 |'):
  lines[i]='| 摄像头 | 219真实传感器4MP/16MP RAW及实验完整16MP CPU Quad RGB各六帧通过，暗场RAW噪声/变化与传感器测试图案正对照通过；旧2MP、4MP30/60、16MP各120帧实测，PIXEL_RATE/旧模式行长元数据修复后与硬件fps吻合。214完整r5包及215/216图案位宽/增益修复保持，taint/fault0 | 已装r5的4MP RGB四缓冲分配失败；system heap候选通过，完整r6包构建中尚未安装。16MP仍显式实验开关；标准CFA/几何、正常光照画质/标定/方向/API/GUI未验收。后置四路未接入；GPU ISP的CMA不足/黑帧/IOMMU unmap及未知PLDO输入、冷启/长稳开放；可复现整合/rootfs仍待完成 |'
status.write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(checkpoint_updated=True,metadata_annotation_corrected=True,full_goal_active=True)))
