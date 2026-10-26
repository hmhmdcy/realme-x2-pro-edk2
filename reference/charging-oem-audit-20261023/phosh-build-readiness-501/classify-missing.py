"""Read fixed package graph and source branches; no solver, package or dependency change."""
from collections import deque
from pathlib import Path
import hashlib
import json
import re

HERE=Path(__file__).resolve().parent
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
sha=lambda b:hashlib.sha256(b).hexdigest()
closure=json.loads((BASE/'closure-private.json').read_bytes())
partial=json.loads((HERE/'partial304-result.json').read_bytes())
abi=json.loads((HERE/'closure-abi-result.json').read_bytes())
inventory=json.loads((HERE/'inventory-result.json').read_bytes())
expected={}
for b in (BASE/'root/lib/apk/db/installed').read_text().split('\n\n'):
    f=dict(l.split(':',1) for l in b.splitlines() if ':' in l)
    if 'P' in f:expected[f['P']]=f
expected.update({p['name']:p['index_fields'] for p in closure})
def key(s):return re.split(r'[<>=~]',s,maxsplit=1)[0]
providers={}
for name,p in expected.items():
    for value in (p.get('p') or '').split():providers.setdefault(key(value),set()).add(name)
graph={}
for name,p in expected.items():
    edges=set()
    for s in (p.get('D') or '').split():
        if s.startswith('!'):continue
        dep=key(s)
        if dep in expected:edges.add(dep)
        else:edges.update(providers.get(dep,set()))
    graph[name]=edges
roots=list(inventory['seed']['present_makedepends'])+inventory['seed']['missing_makedepends']
def path(starts,target):
    queue=deque([[s] for s in starts]);seen=set(starts)
    while queue:
        p=queue.popleft()
        if p[-1]==target:return p
        for n in sorted(graph.get(p[-1],set())):
            if n not in seen:seen.add(n);queue.append(p+[n])
    return None
essential={'gobject-introspection':'GIR runtime required by actual g-ir-scanner/compiler path',
           'gobject-introspection-dev':'Provides g-ir-scanner/compiler; real src/meson.build608/620 generates GIR for bindings-lib=true',
           'feedbackd-dev':'Direct original makedepend and meson.build libfeedback-0.0 dependency; cannot omit original fixed headers/pkg-config'}
rows=[]
runtime={p['actual_package'] for p in abi['direct_soname_provider_comparison']}
for failure in partial['remaining_missing']:
    name=failure['name'];frombuild=path(roots,name);fromcheck=path(['xvfb-run','xmlstarlet'],name)
    rows.append({**failure,'category':essential.get(name,'Development dependency closure' if name in ['nss-dev','xkeyboard-config-dev'] else 'Indirect runtime/backend dependency of original development-package closure'),
                 'phosh_compiler_or_GIR_direct_need':name in essential,
                 'is_one_of_42_direct_runtime_providers':name in runtime,
                 'shortest_from_original_makedepends':frombuild,
                 'shortest_from_checkdepends':fromcheck,
                 'check_or_docs_only':frombuild is None and fromcheck is not None})
result={'missing_count':11,'missing':rows,'critical_direct_build_or_GIR_missing':sorted(essential),
        'only_check_or_docs_missing':[p['name'] for p in rows if p['check_or_docs_only']],
        '42_direct_runtime_providers_missing':[p['name'] for p in rows if p['is_one_of_42_direct_runtime_providers']],
        'minimal_next_action':'Find exact three compiler/GIR payloads first using same-version official pools and frozen C/signature; do not disable bindings-lib or replace feedbackd headers. Standard APKBUILD still needs complete package dependency closure, so do not force-install304 with unresolved dependencies.',
        'metadata_graph_only_not_new_package_solver':True,'source_sha256':sha(Path(__file__).read_bytes())}
(HERE/'missing-classification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
