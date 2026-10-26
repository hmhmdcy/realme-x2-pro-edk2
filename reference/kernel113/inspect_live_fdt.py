from pathlib import Path
import json,struct,tarfile

def fdt(data):
    magic,total,off,strings=struct.unpack_from('>4I',data)
    assert magic==0xd00dfeed and total==len(data)
    nodes={}; stack=[]
    while True:
        token,=struct.unpack_from('>I',data,off); off+=4
        if token==1:
            end=data.index(0,off); stack.append(data[off:end].decode()); off=(end+4)&~3
            nodes['/'+ '/'.join(stack[1:])]={}
        elif token==2: stack.pop()
        elif token==3:
            size,noff=struct.unpack_from('>2I',data,off); off+=8
            end=data.index(0,strings+noff); key=data[strings+noff:end].decode()
            nodes['/'+'/'.join(stack[1:])][key]=data[off:off+size]; off=(off+size+3)&~3
        elif token==4: pass
        elif token==9: return nodes
        else: raise AssertionError('FDT token')

if __name__=='__main__':
    out=Path('/mnt/e/edk2-samurai-out/kernel113')
    with tarfile.open(out/'first-before-slpi.tar') as t:
        m=next(m for m in t if m.name.endswith('live-fdt-private.dtb'))
        live=fdt(t.extractfile(m).read())
    src=fdt((out/'dtb-sensor-power').read_bytes())
    changes=[]
    for name,props in src.items():
        assert name in live,name
        for key,val in props.items():
            if live[name].get(key)!=val: changes.append(dict(node=name,property=key))
        for key in set(live[name])-set(props): changes.append(dict(node=name,property=key,added=True))
    print(json.dumps(dict(property_changes=changes,added_nodes=sorted(set(live)-set(src)))))
