from pathlib import Path
import ast, host, json, shutil
here = Path(__file__).resolve().parent
dest = here / 'reboot-r2'; dest.mkdir()
private = host.PRIVATE / 'reboot-r2'; private.mkdir(mode=0o700)
shutil.copyfile(host.PRIVATE / 'usb-ipv6-candidates-private.json', private / 'usb-ipv6-candidates-private.json')
names = ['host.py', 'run-native.py', 'collect-pre-reboot.py', 'quiesce-current183.sh', 'stop-gnss-idle.py', 'disable-crtc.py', 'check-quiesce.py', 'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py', 'deploy-and-quiesce.py', 'reboot-current.py', 'fastboot-reboot-current.py', 'collect-newboot.py', 'connect-newboot.py', 'refresh-usb-endpoint.ps1']
for name in names:
    source = (here / name).read_text().replace('kernel207', 'kernel207/reboot-r2').replace('k207', 'k207r2')
    source = source.replace('k207r2-tftp-deploy', 'k207-tftp-deploy')
    if name == 'collect-pre-reboot.py':
        source = source.replace("root / 'k207r2-baseline/boot-id-private.txt'", "root / 'k207-runtime/boot-id-private.txt'")
        source = source.replace('ffb65d31b337fbdad89ff9c575b133574756121f75cd2967da10f1028c1b5fbd', '854c9a8c787d68ccefc998064983f3aa67141fe94def27f4dde87925bd18f24f')
        anchor = "expected['/usr/sbin/samurai-bluetooth'] = sha('/usr/sbin/samurai-bluetooth')"
        assert source.count(anchor) == 1
        source = source.replace(anchor, anchor + "\nexpected['/usr/sbin/samurai-modem-configs'] = 'd4c62be6054b3ff74f3ed2868c4b456ccb519f75954ad7094235826559a64862'")
        source = source.replace("watch['worker_starts'] == watch['worker_completions'] == 1", "watch['worker_starts'] == watch['worker_completions'] == 0")
        source = source.replace('same205_r2_boot=True', 'same_first207_boot=True')
    if name == 'collect-newboot.py':
        source = source.replace('reboot_cycle=1', 'reboot_cycle=2')
        anchor = "watch = json.loads((root/'gnss-assist/watch-state.json').read_text())"
        assert source.count(anchor) == 1
        extra = '''mcfg_manifest=json.loads(Path('/run/samurai-wifi/mcfg-state/source-manifest-private.json').read_text())
assert mcfg_manifest==json.loads((root/'k207-stock-mcfg-inventory/mcfg-source-manifest-private.json').read_text())
fwroot=Path('/run/samurai-wifi/firmware/qcom/sm8150/realme/samurai')
assert len(mcfg_manifest)==173 and all(hashlib.sha256((fwroot/name).read_bytes()).hexdigest()==info['sha256'] for name,info in mcfg_manifest.items())
'''
        source = source.replace(anchor, extra + anchor)
        source = source.replace('new_tftp_and_wifi_helper_exact=True,', 'new_tftp_and_wifi_helper_exact=True,stock_mcfg_173_files_staged_automatically_and_exact=True,')
    if name in ['host.py', 'connect-newboot.py']:
        source = source.replace("Path(__file__).resolve().parent.parent/'kernel188/host.py'", "Path(__file__).resolve().parent.parent.parent/'kernel188/host.py'")
        source = source.replace("here.parent/'kernel188/host.py'", "here.parent.parent/'kernel188/host.py'")
    if name == 'fastboot-reboot-current.py': source = source.replace('host.PRIVATE.parent /', 'host.PRIVATE.parents[1] /')
    if name.endswith('.py'): ast.parse(source)
    (dest / name).write_text(source)
mcfg = json.loads((host.PRIVATE / 'deploy-stock-mcfg-r2-host-private.log').read_text())
(here / 'mcfg-deployment-validation.json').write_text(json.dumps(mcfg, indent=2) + '\n')
for label in ['query-pdc-readonly', 'query-pdc-details']:
    p = host.PRIVATE / (label + '-host-private.log')
    value = json.loads(p.read_text()); value['verified_first207_boot'] = True
    (here / (label + '-validation.json')).write_text(json.dumps(value, indent=2) + '\n')
plan_path = host.PRIVATE / 'current-work-private.json'; plan = json.loads(plan_path.read_text())
plan.update(state='First207 boot complete. Same-handset173 stockMCFG files copied/verified intoRAM; native mdtime12byte read passed; wifi854/helperd4 installed. Preparing NEW second ordinary reboot, no second transition sent.', current_boot_guard='/var/lib/samurai/k207-runtime/boot-id-private.txt', second_reboot_prepared=True, second_reboot_sent=False, next='Use reference/kernel207/reboot-r2 fresh preflight and its own markers; do not replay first207 transition. Verify automatic173filecopy and real firmware MCFG requests after newboot.')
plan_path.write_text(json.dumps(plan, indent=2) + '\n')
(private / 'current-work-private.json').write_text(json.dumps(dict(stage=207, cycle=2, state='Prepared only; first207boot current; no second transition sent.', current_boot_guard='/var/lib/samurai/k207-runtime/boot-id-private.txt', host='reference/kernel207/reboot-r2/host.py', next='Fresh preflight, quiesce/archive, one ordinary reboot; no flash.'), indent=2) + '\n')
nextfile = here.parents[1] / 'NEXT-SESSION.md'; text = nextfile.read_text()
text = text.replace('samurai-wifi仍ffb65d31…', 'samurai-wifi现854c9a8c…，新增samurai-modem-configs d4c62be6…')
text = text.replace('下一步补齐本机原厂只读MCFG目录到RAM和启动脚本，核对真实QRTR读取，再用新身份/新目录准备下一轮普通重启。', '已将173文件8,807,671字节从本机只读modem分区完整复制到RAM，逐文件匹配清单，正式QRTR读回mdtime12字节通过；未重启TFTP/MPSS或启GPS。新helper854和复制程序d4已安装。首次复制因旧/run/samurai-wifi为755而在复制前停止，已保留失败并改用700的mcfg-state子目录。下一步用reference/kernel207/reboot-r2的新目录/marker进行第二次普通启动，验自动复制和实际modem请求；第二轮尚未发重启。')
nextfile.write_text(text)
print('Prepared second ordinary boot with stock MCFG automatic staging; current first207 boot retained, no second transition sent.')
