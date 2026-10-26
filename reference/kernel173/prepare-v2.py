from pathlib import Path
import json, shutil, tarfile, hashlib

ref = Path(__file__).parent
out = Path('/mnt/e/edk2-samurai-out/kernel173')
shutil.copyfile(ref / 'source-validation.json',ref / 'source-validation-v1.json')
shutil.copyfile(out / 'candidate-files-private.tar',out / 'candidate-files-v1-private.tar')
exec(compile((ref / 'prepare-candidate.py').read_text(),'prepare-candidate.py','exec'),{'__file__':str(ref / 'prepare-candidate.py')})
s = (ref / 'test-ucm-candidate.py').read_text()
s = s.replace('k173-ucm-test-verified','k173-ucm-test-v2').replace('/run/samurai-ucm173','/run/samurai-ucm173-v2')
s = s.replace("'list _conflictingdevs/Headphones/HiFi'", "'get JackHWMute/Headphones/HiFi','get JackHWMute/Headset/HiFi'")
a = s.index("    p = batch('expected-conflict'"); b = s.index("    batch('inactive'",a)
s = s[:a] + '''    batch('shared-pcm-ports',['set _verb HiFi','set _enadev Speaker','set _enadev Mic',
                             'set _enadev Headphones','set _enadev Headset','list _enadevs'])
    check('Headphones','Headset')
    batch('speaker-mic-return',['set _verb HiFi','set _enadev Speaker','set _enadev Mic'])
    check('Speaker','Mic')
''' + s[b:]
s = s.replace('conflict_rejected=True','shared_pcm_ports_select_one_backend_and_one_tx=True')
s = s.replace('user_privilege_exec_pass=True,route_cases=rows', 'user_privilege_exec_pass=True,ucm_version=2,route_cases=rows')
(ref / 'test-ucm-v2.py').write_text(s)
d = (ref / 'deploy-ucm.py').read_text()
d = d.replace('k173-deploy','k173-deploy-v2').replace('k173-ucm-test-verified','k173-ucm-test-v2')
d = d.replace("test['conflict_rejected']", "test['shared_pcm_ports_select_one_backend_and_one_tx']")
old = "    if existing: pulse(['unload-module',str(existing[0]['index'])])\n"
new = old + '''    children = [r for r in modules() if r['name'] == 'module-alsa-card']
    assert all('device_id="0"' in r['argument'] and 'name="platform-sound"' in r['argument'] for r in children)
    for r in children:
        if any(m['index'] == r['index'] for m in modules()):
            pulse(['unload-module',str(r['index'])])
    assert not any(r['name'] == 'module-alsa-card' for r in modules())
'''
assert d.count(old)==1; d = d.replace(old,new)
d = d.replace('    time.sleep(2)\n', '    time.sleep(2)\n    if not any(r["name"]=="module-switch-on-port-available" for r in modules()):\n        pulse(["load-module","module-switch-on-port-available"])\n',1)
d = d.replace('    for n in [\'HiFi.conf\',\'Realme_X2_Pro.conf\']:\n        source', '    changed = True\n    for n in [\'HiFi.conf\',\'Realme_X2_Pro.conf\']:\n        source',1)
(ref / 'deploy-ucm-v2.py').write_text(d)
compile(s,'test-ucm-v2.py','exec'); compile(d,'deploy-ucm-v2.py','exec')
print('K173_V2_TOOLS_PREPARED',flush=True)
