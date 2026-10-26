from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel223')
assert json.loads((here/'package-build-validation.json').read_text())['framework_and_config_packages_built']
for name in ['inspect-full-features.py','collect-forward-packages.py','host-runtime-qa.py','stage-r7-packages.py']:
 text=(here.parent/'kernel220'/name).read_text().replace('kernel220','kernel223').replace('stage=220','stage=223').replace('libcamera220','libcamera223').replace('candidate220','candidate223').replace('packages220','packages223').replace('packages-config220','packages-config223').replace('samurai-camera-config220','samurai-camera-config223').replace('k220-','k223-').replace('99990.7.2-r7','99990.7.2-r8').replace('0.1.0-r2','0.1.0-r3')
 text=text.replace('upstream_verifier_uses_current_r7_core_and_base','upstream_verifier_uses_current_r8_core_and_base')
 if name=='stage-r7-packages.py':
  text=text.replace('samurai-camera220-r7','samurai-camera223-r8').replace('r7-candidate-','r8-candidate-').replace('r7-bundle-','r8-bundle-').replace('r7-transfer-','r8-transfer-').replace('r7-staging-','r8-staging-')
  text=text.replace('k223-r7-package-candidates','k223-r8-package-candidates')
  text=text.replace("rollback=root/'k219-r6-package-candidates'","rollback=root/'k220-r7-package-candidates'")
  text=text.replace("'0.1.0-r1'","'0.1.0-r2'").replace("'99990.7.2-r6'","'99990.7.2-r7'")
  text=text.replace('actual_seven_r6_rollback','actual_seven_r7_rollback').replace('retain actual r5 rollback','retain actual r7 rollback')
  name='stage-r8-packages.py'
 compile(text,name,'exec');(here/name).write_text(text)
state=json.loads((private/'current-work-private.json').read_text());state.update(state='r8/r3 all13 packages built; original2142254 files/links/modes restored; paired SOF kernel candidate physically verified but not deployed',active_build_session=None,protected_original214_snapshot=None,next='Verify13 signatures/full-feature artifacts and5IPA, stage isolated runtime with actual r7/r2 rollback, then test r8 capture-control snapshots with paired fae1 driver before coherent deployment.')
(private/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n')
p=repo/'NEXT-SESSION.md';text=p.read_text().replace('r8采集时控制快照完整构建中，session54480；原214源码受保护','r8控制快照13包已构建，原214树已恢复；签名和实机待验')
text=text.replace('reference/kernel222/host.py','reference/kernel223/host.py').replace('guard /var/lib/samurai/k222-baseline/boot-id-private.txt','guard /var/lib/samurai/k223-baseline/boot-id-private.txt')
start=text.index('- r8构建session54480');end=text.index('\n-',start+2)
text=text[:start]+'- r8构建54480终态成功，SDK /home/cy122/x2pro-linux/libcamera214-root原/work/libcamera2254文件/链接/权限已恢复，无待恢复快照；候选/work/libcamera223-built，原r7缓存220-built保持。配方libcamera223/config223、13包/packages223及/packages-config223。签名/5IPA/实机仍待验，手机r7。'+text[end:]
assert len(text.encode())<=6500,len(text.encode());p.write_text(text)
p=here/'README.md';text=p.read_text().replace('完整r8/config-r3构建session54480进行中；','完整r8/config-r3的13包已构建；').replace('SDK原214已移至/private/libcamera214-before223保护，活构建不可移动当前/work/libcamera；终态恢复，候选保留/work/libcamera223-built。','SDK原214的2254文件/链接/权限已恢复，没有待恢复快照；候选保留/work/libcamera223-built。');p.write_text(text)
print('K223_COMPLETE_R8_VALIDATORS_PREPARED_ORIGINAL214_RESTORED')
