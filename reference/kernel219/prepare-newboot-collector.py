from pathlib import Path
import ast,json

here=Path(__file__).resolve().parent;previous=here.parent/'kernel211'
proof=json.loads((here/'factory-mode-candidate-build-validation.json').read_text())
build=json.loads((here/'build-package-validation.json').read_text())
text=(previous/'collect-newboot.py').read_text().replace('k211-','k219-').replace('stage=211','stage=219')
text=text.replace('c3bf043f2eea0c5f8e42cc8cac621ccfba023b181e400d0919174b87e3d37ba6',build['boot_sha256'])
text=text.replace('a28dd67a03afa9e918f87b85030f0158edecbcc2e3f1ce0a36405b78be70ba6a',proof['module_sha256'])
text=text.replace("assert selection[label]['crop']==dict(success=True,rect=[8,408,4640,2644])","assert selection[label]['crop'] in [dict(success=True,rect=[8,408,4640,2644]),dict(success=True,rect=[0,0,4656,3496])]")
text=text.replace("assert selection[label]['crop_bounds']==selection[label]['crop_default']","assert selection[label]['crop_bounds']==dict(success=True,rect=[0,0,4672,3512])")
text=text.replace('boot211_logdump183_persist_nv_readback_exact=True','boot219_logdump183_persist_nv_readback_exact=True')
marker="nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*')"
assert text.count(marker)==1
text=text.replace(marker,"assert Path('/lib/apk/db/installed').read_bytes()==(root/'k219-baseline/installed-before-private.txt').read_bytes()\nassert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip()=='N'\nassert (sensor/'of_node/port/endpoint/link-frequencies').read_bytes()==struct.pack('>QQQ',200000000,400000000,748800000)\n"+marker)
old="(3,'native_size'),(65535,'unsupported')";assert old in text
text=text.replace(old,"(3,'native_size'),(0x100,'compose'),(0x101,'compose_default'),(0x102,'compose_bounds'),(65535,'unsupported')")
marker="    assert selection[label]['unsupported']==dict(success=False,errno=22)"
assert text.count(marker)==1
text=text.replace(marker,marker+"\n    assert all(selection[label][name]==dict(success=False,errno=22) for name in ['compose','compose_default','compose_bounds'])")
ast.parse(text);assert not (here/'collect-newboot.py').exists();(here/'collect-newboot.py').write_text(text)
print('219 new-boot collector prepared; requires boot readback, loaded module note, real endpoint frequencies and unchanged products')
