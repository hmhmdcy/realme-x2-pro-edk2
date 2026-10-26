"""Authorize only same-source private GIR tools and fixed feedbackd source; no target runtime changes."""
from pathlib import Path
import hashlib
import io
import json
import re
import tarfile
import urllib.request

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'phosh-build-readiness-501'
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
sha=lambda b:hashlib.sha256(b).hexdigest()
closure={p['name']:p for p in json.loads((BASE/'closure-private.json').read_bytes())}
rows=[]
for name in ['gobject-introspection','gobject-introspection-dev']:
    p=BASE/'official-v324-exact-pool'/(name+'-1.86.0-r1.apk');raw=p.read_bytes()
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz',ignore_zeros=True) as t:
        text=t.extractfile('.PKGINFO').read().decode();members=t.getnames()
    info={}
    for line in text.splitlines():
        if ' = ' in line:
            k,v=line.split(' = ',1);info.setdefault(k,[]).append(v)
    expected=closure[name]['index_fields']
    for key,index_key in [('pkgname','P'),('pkgver','V'),('arch','A'),('commit','c')]:
        assert info[key]==[expected[index_key]],(name,key)
    for key,index_key in [('depend','D'),('provides','p')]:
        assert set(info.get(key,[]))==set((expected[index_key] or '').split()),(name,key)
    assert info['commit']==['f48701aa97c725aaabe89f85bb040ce56954d0bd']
    if name.endswith('-dev'):
        assert 'usr/lib/gobject-introspection/giscanner/_giscanner.cpython-314-aarch64-linux-musl.so' in members
    rows.append({'name':name,'path':str(p),'sha256':sha(raw),'pkginfo':info,
                 'metadata_V_A_c_D_p_same_as_edge':True,'fixed_edge_C':expected['C'],
                 'different_C_recorded_in':str(OLD/'same-version-pool-result.json'),
                 'usage':'private build-time GIR tool/runtime only, excluded from phone payload'})
recipe=(HERE/'gobject-introspection-APKBUILD').read_text()
assert 'pkgver=1.86.0' in recipe and 'pkgrel=1' in recipe
assert re.search(r'^source="https://download.gnome.org/[^\n]+"$',recipe,re.M)
assert '.patch' not in recipe

feedback_recipe=(HERE/'feedbackd-APKBUILD').read_text()
assert 'pkgver=0.8.9' in feedback_recipe and 'pkgrel=4' in feedback_recipe
assert '.patch' not in feedback_recipe
name='feedbackd-0.8.9.tar.xz'
expected=re.search(r'^([0-9a-f]{128})  '+re.escape(name)+r'$',feedback_recipe,re.M)[1]
url='https://sources.phosh.mobi/releases/feedbackd/'+name
dest=BASE/'same-source-build-inputs';dest.mkdir(mode=0o700)
with urllib.request.urlopen(url,timeout=35) as response:
    assert response.url==url
    raw=response.read(64*1024*1024+1)
assert len(raw)<=64*1024*1024 and hashlib.sha512(raw).hexdigest()==expected
(dest/name).write_bytes(raw)
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:xz') as t:
    members=t.getnames()
    texts={m:t.extractfile(m).read().decode() for m in members if m in ['feedbackd-0.8.9/meson.build','feedbackd-0.8.9/meson_options.txt','feedbackd-0.8.9/libfeedback/meson.build']}
    headers=[m for m in members if m.startswith('feedbackd-0.8.9/libfeedback/') and (m.endswith('.h') or '.pc' in m or 'enum' in m or 'version' in m)]
result={'same_source_input_change_explicit':True,'original315_closure_still_failed':True,
        'GIR_private_tools':rows,
        'GIR_recipe_sha256':sha((HERE/'gobject-introspection-APKBUILD').read_bytes()),
        'GIR_recipe_same_fixed_commit_no_release_patch':True,
        'feedbackd_source':{'path':str(dest/name),'url':url,'sha256':sha(raw),'sha512':expected,
                            'recipe_sha256':sha((HERE/'feedbackd-APKBUILD').read_bytes()),
                            'original_fixed_commit':'9300ed125d6bd60af3180e37b0413312d74c79ab','patches':[],
                            'version':'0.8.9','pkgrel':4,'header_members':headers,'selected_build_text':texts},
        'no_install_build_or_phone_runtime_change_yet':True,
        'program_sha256':sha(Path(__file__).read_bytes())}
(HERE/'three-inputs-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'GIR_metadata_same_V_A_c_D_p':True,'GIR_same_recipe_no_patches':True,
                  'feedbackd_source_sha256':sha(raw),'headers':headers,'build_text':texts,
                  'result_sha256':sha((HERE/'three-inputs-result.json').read_bytes())},indent=2))
