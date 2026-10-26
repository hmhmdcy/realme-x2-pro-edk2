"""One narrow derivative of the actual 7cb/Image502 USB ko builder."""
from pathlib import Path
import hashlib,json,difflib
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
BASE=REF/'charging-ui-audit-20261023/usb-input-irq-board-candidate/build-ko.py'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
raw=BASE.read_bytes();assert sha(raw)=='7b69accb526573ad0419ec115f747844e8ac1da3941b9dc7c4ec68bad2656574'
text=raw.decode()
changes={
"AUTHOR = REF / 'charging-oem-audit-20261023/usb-input-irq-candidate'":"AUTHOR = HERE.parent / 'usb-input-irq-native-pm-link-candidate'\nBOARD = REF / 'charging-ui-audit-20261023/usb-input-irq-board-candidate'\nEXPORT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-input-irq-native-pm-link-module-private-01')",
"/usb-input-irq-board-01'":"/usb-input-irq-native-pm-link-module-01'",
"SOURCE_HASH = '0fdafb8b3924e431efd67a888cbb88b8f5fe6de22dc400b009bf64cba34b7be5'":"SOURCE_HASH = 'cf3c7f039035f7bd1e654e3d781e5f6f16ca01b0fc422234ee71aefd87cc6b3f'",
"assert not OUT.exists() and not (HERE / 'ko-result.json').exists()":"assert not OUT.exists() and not EXPORT.exists() and not (HERE / 'ko-result.json').exists()",
"392ba7974a8ed76151e4a320d0a1cb226c300612ef5e01ca7ff983a60d539c5d":"fa38684a6f618bd6d081b420c1323f8f146ac5af6174e3695e2a8b40bed7975f",
"dt = json.loads((HERE / 'dt-result.json').read_bytes())":"dt = json.loads((BOARD / 'dt-result.json').read_bytes())",
"image_leaf = HERE.parent / 'gauge-image502-notify-candidate'":"image_leaf = REF / 'charging-ui-audit-20261023/gauge-image502-notify-candidate'",
"'DT_result_sha256': sha(HERE / 'dt-result.json')":"'DT_result_sha256': sha(BOARD / 'dt-result.json')",
"'LOCALVERSION=+', 'W=1', '-j4'":"'LOCALVERSION=+', 'W=1', 'KCFLAGS=-Werror', '-j4'",
"exported_ko = PAIR / 'samurai-usb-input-irq-private.ko'":"EXPORT.mkdir(mode=0o700)\n        exported_ko = EXPORT / 'samurai-usb-input-irq-native-pm-link-private.ko'",
}
for old,new in changes.items():
    assert old in text,old;text=text.replace(old,new)
anchor="    before = {str(path): fingerprint(path) for path in tracked}"
assert anchor in text
text=text.replace(anchor,'''    protected = {
        PAIR / 'samurai-usb-input-irq-private.ko': '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f',
        Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko'): '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd',
        Path('/mnt/e/edk2-samurai-out/charging-management-20261023/protection-query-observer-module-private-01/samurai-gauge-protection-observer-private.ko'): '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044',
        Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-payload-private-01/manifest-new.json'): '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5',
        Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-payload-private-01/forward-two-files.tar.gz'): '0870e32b1c6f5a927a1480a4cd523c2804dc7f44fe1796e8adb2b0100ffc71ea',
    }
    for path,digest in protected.items(): assert sha(path)==digest
    note_utility = REF/'charging-oem-audit-20261023/protection-query-observer-module-candidate/build-ko.py'
    assert sha(note_utility)=='6d484f62844c4976c928ab9a6e81fee0851076a33ab188974dd06cbaf689262f'
    tracked += list(protected) + [Path(__file__), helper, note_utility]
    tracked += [AUTHOR / name for name in ['samurai-usb-input.c','samurai-usb-input-decode.h','native-pm-link.c.inc','delivery.json','test-result.json']]
''' + anchor)
text=text.replace("              'old_16_cases_reused_not_rerun': True,", "              'old_16_cases_reused_not_rerun': True, 'old_PM21_and_merge8_reused_not_rerun': True,")
text=text.replace("        assert output(['modinfo', '-F', 'intree', str(ko)]).strip() == 'Y'", "        assert output(['modinfo', '-F', 'intree', str(ko)]).strip() == 'Y'\n        assert output(['modinfo', '-F', 'name', str(ko)]).strip() == 'samurai_usb_input'")
text=text.replace("        assert not output(['modinfo', '-F', 'depends', str(ko)]).strip()", "        assert output(['modinfo', '-F', 'vermagic', str(ko)]).strip() == '7.3.0-rc6-rmx1931-samurai-k363+ SMP preempt mod_unload aarch64'\n        assert not output(['modinfo', '-F', 'depends', str(ko)]).strip()")
text=text.replace("        assert config(build / '.config') == config(BASE / 'build/.config')", "        assert config(build / '.config') == config(BASE / 'build/.config')\n        assert sha(build / '.config') == sha(BASE / 'build/.config')")
text=text.replace("            assert len(fields) == 2", "            assert len(fields) == 2 and fields[-2] in ('U','w','W','v','V')")
text=text.replace("        result.update(passed=True, module_path=str(ko)", """        spec = importlib.util.spec_from_file_location('frozen_note_reader',note_utility)
        util = importlib.util.module_from_spec(spec);spec.loader.exec_module(util)
        module_note,build_id = util.note(ko.read_bytes())
        (OUT/'note.gnu.build-id').write_bytes(module_note)
        (EXPORT/'note.gnu.build-id').write_bytes(module_note)
        result.update(passed=True, module_note_sha256=hashlib.sha256(module_note).hexdigest(),GNU_build_id=build_id,
                      vermagic=output(['modinfo','-F','vermagic',str(ko)]).strip(),module_path=str(ko)""")
end="if __name__ == '__main__':\n    raise SystemExit(main())"
assert end in text
text=text.replace(end,"""if __name__ == '__main__':
    if sys.argv[1:] == ['--execute']: raise SystemExit(main())
    assert sys.argv[1:] in ([],['--check-local'])
    assert sha(AUTHOR/'delivery.json')=='fa38684a6f618bd6d081b420c1323f8f146ac5af6174e3695e2a8b40bed7975f'
    author=json.loads((AUTHOR/'delivery.json').read_bytes())
    for name,row in author['files'].items(): assert sha(AUTHOR/name)==row['sha256']
    assert sha(AUTHOR/'samurai-usb-input.c')==SOURCE_HASH and sha(AUTHOR/'samurai-usb-input-decode.h')==DECODER_HASH
    print(json.dumps({'passed':True,'source_only':True,'storage_or_build_accessed':False,'device_accessed':False,'output_created':False}))
""")
compile(text,str(HERE/'build-ko.py'),'exec')
(HERE/'build-ko.py').write_text(text,encoding='utf-8',newline='\n')
(HERE/'method-delta.patch').write_text(''.join(difflib.unified_diff(raw.decode().splitlines(True),text.splitlines(True),fromfile='frozen-7cb/build-ko.py',tofile='IRQ-native-PM-link/build-ko.py')),encoding='utf-8',newline='\n')
print(json.dumps({'builder_sha256':sha((HERE/'build-ko.py').read_bytes()),'base_builder_sha256':sha(raw)}))
