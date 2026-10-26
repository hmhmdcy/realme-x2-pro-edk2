from pathlib import Path
ns={};exec((Path(__file__).parent/'verify-tests.py').read_text().split("names=['audio-runtime'",1)[0],ns)
a=ns['archive']('audio-runtime')['modules.txt'].decode().splitlines()
b=ns['archive']('checkpoint')['modules.txt'].decode().splitlines()
print('MODULE_ROWS',len(a),len(b))
print('BEFORE_NAMES',[x.split()[0] for x in a]);print('AFTER_NAMES',[x.split()[0] for x in b])
for x,y in zip(a,b):
    if x!=y:
        p=x.split();q=y.split()
        print(p[0],dict(before_use_count=p[2],after_use_count=q[2],other_fields_equal=p[:2]+p[3:]==q[:2]+q[3:]))
