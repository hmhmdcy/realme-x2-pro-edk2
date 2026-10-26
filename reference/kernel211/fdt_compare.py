"""Compare DTBs using source YAML's explicit phandle markers, never scalar guesses."""
from pathlib import Path
import ast,struct
import yaml

class Ref(int):pass
class Loader(yaml.SafeLoader):pass
Loader.add_constructor('!phandle',lambda loader,node:Ref(int(loader.construct_scalar(node),0)))
def tagged(loader,suffix,node):
    if isinstance(node,yaml.SequenceNode):return loader.construct_sequence(node,deep=True)
    return loader.construct_scalar(node)
Loader.add_multi_constructor('!',tagged)

def parser():
    source=Path(__file__).resolve().parent.parent/'kernel104/verify-firmware.py'
    function=next(node for node in ast.parse(source.read_text()).body if isinstance(node,ast.FunctionDef) and node.name=='fdt_nodes')
    namespace={'struct':struct,'align':lambda n,a:(n+a-1)//a*a}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'existing-fdt-parser','exec'),namespace)
    return namespace['fdt_nodes']

def flat(value):
    if isinstance(value,list):return [item for child in value for item in flat(child)]
    return [value]

def reference_positions(source_yaml):
    tree=yaml.load(Path(source_yaml).read_text(),Loader=Loader)
    assert isinstance(tree,list) and len(tree)==1
    positions={};yaml_handles={}
    def walk(node,path):
        for name,value in node.items():
            if isinstance(value,dict):walk(value,path.rstrip('/')+'/'+name)
            else:
                cells=flat(value)
                if name in ['phandle','linux,phandle']:
                    assert len(cells)==1;yaml_handles[int(cells[0])]=path
                marked=[(i*4,int(cell)) for i,cell in enumerate(cells) if isinstance(cell,Ref)]
                if marked:positions[(path,name)]=marked
    walk(tree[0],'/')
    return positions,yaml_handles

def compare(old,new,source_yaml):
    positions,yaml_handles=reference_positions(source_yaml)
    old_by_path={path:int.from_bytes(props['phandle'],'big') for path,props in old.items() if 'phandle' in props}
    new_handles={int.from_bytes(props['phandle'],'big'):path for path,props in new.items() if 'phandle' in props}
    remaining=[];normalized=0;references=0
    for path in sorted(old.keys()&new.keys()):
        for name in sorted(old[path].keys()|new[path].keys()):
            before=old[path].get(name);after=new[path].get(name)
            if before==after:continue
            modified=bytearray(after) if after is not None else None
            if name in ['phandle','linux,phandle'] and before is not None and after is not None:
                modified=bytearray(before)
            elif after is not None:
                for offset,value in positions.get((path,name),[]):
                    assert offset+4<=len(after)
                    handle=int.from_bytes(after[offset:offset+4],'big')
                    target=new_handles[handle]
                    assert yaml_handles[value]==target,'YAML reference does not match compiled source cell'
                    if target in old_by_path:
                        modified[offset:offset+4]=old_by_path[target].to_bytes(4,'big');references+=1
            if modified is not None and bytes(modified)==before:normalized+=1
            else:remaining.append(dict(path=path,property=name))
    return dict(old_nodes=len(old),new_nodes=len(new),only_old_nodes=sorted(old.keys()-new.keys()),only_new_nodes=sorted(new.keys()-old.keys()),phandle_only_properties_normalized=normalized,explicit_reference_cells_checked=references,remaining_changed_properties=remaining)
