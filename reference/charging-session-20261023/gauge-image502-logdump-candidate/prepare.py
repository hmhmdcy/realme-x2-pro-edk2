"""Derive only this FAT carrier from frozen 501 packer; never invoke tools."""
from pathlib import Path
import ast,hashlib,json
H=Path(__file__).resolve().parent
B=H.parent/'gauge-image501-carriers-candidate/package-logdump.py'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(B.read_bytes())=='0b0a7d7fa006de6e8ffcc456dfde6f664c3d8edf0a2e9f7a378f6e464e93d9c7'
old=B.read_text();s=old
def sub(a,b):
 global s
 assert s.count(a)==1,a;s=s.replace(a,b)
sub('Only privately replace ACA FAT /Image.','Only privately replace current Image501 FAT /Image with frozen Image502.')
sub('sys.dont_write_bytecode=True','sys.dont_write_bytecode=True\nif sys.flags.optimize: raise RuntimeError("Non-optimized interpreter required")')
sub("OLD=ROOT/'kernel365/logdump-k365-candidate-private.img'","OLD=ROOT/'charging-management-20261023/gauge-image501-logdump-private-01/logdump-gauge501-private.img'")
sub("IMAGE=Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01/build/arch/arm64/boot/Image')","IMAGE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01/build/arch/arm64/boot/Image')")
sub("OUT=ROOT/'charging-management-20261023/gauge-image501-logdump-private-01'","OUT=ROOT/'charging-management-20261023/gauge-image502-logdump-private-01'")
s=s.replace('aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da','7e5de5b437fbc884d97a103e77bd97a21b77c99151c67b7bcb1745d51076cbf9')
sub("    image=pinned(IMAGE,'3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02')\n",'')
sub("'15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'","'3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'")
sub("    assert f['files']['Image']['size']==len(image)==59243008","    assert f['files']['Image']['size']==59243008")
sub('    return old,image,f','''    proof=load_502_proof()
    if proof is None:
        return old,None,f
    image=pinned(IMAGE,proof['Image_sha256'])
    assert len(image)==proof['Image_bytes'] and len(image)>0
    return old,image,f''')
sub('    old,image,a=check_local();paths=[OLD,IMAGE,Path(__file__)]+[Path(p) for p,_ in TOOLS.values()]',
'''    old,image,a=check_local()
    if image is None: raise RuntimeError('Image502 frozen terminal proof not supplied; no Image read or packaging')
    paths=[OLD,IMAGE,Path(__file__),HERE/'Image502-pins.json']+[HERE.parents[1]/'charging-ui-audit-20261023/gauge-image502-notify-candidate'/n for n in ['delivery.json','build-result.json','abi-reuse-result.json','execution-receipt.json']]+[Path(p) for p,_ in TOOLS.values()]''')
sub("target=OUT/'logdump-gauge501-private.img'","target=OUT/'logdump-gauge502-private.img'")
sub('private undeployed ACA FAT Image501 replacement only','private undeployed current-501 FAT Image502 replacement only')
sub("'Image501_sha256':sha(image)","'Image502_sha256':sha(image)")
sub("b['files']['Image']['size']==a['files']['Image']['size']","b['files']['Image']['size']==len(image)")
sub("        check_local();print(json.dumps({'checked':True,'tools_executed':False,'unique_private_exists':OUT.exists()}))", 
"        _,image,_=check_local();print(json.dumps({'checked':True,'Image502_proof_ready':image is not None,'new_Image_read':image is not None,'tools_executed':False,'unique_private_exists':OUT.exists()}))")
helper=(H/'proof-gate.inc').read_text()
sub('def check_local():',helper+'\ndef check_local():')
sub('import hashlib,json,os,shutil,struct,subprocess,sys,traceback','import hashlib,io,json,os,shutil,struct,subprocess,sys,traceback')
sub('def save(p,v):', '''def read_bytes(p):
    # DrvFS large single read returned ENOMEM; keep identical bytes semantics.
    with p.open('rb') as source, io.BytesIO() as output:
        while chunk := source.read(1024*1024):
            output.write(chunk)
        return output.getvalue()

def save(p,v):''')
# Replace only file I/O calls; parser/content/ranges stay bytes, not mmap/model.
tree=ast.parse(s);lines=s.splitlines(keepends=True);offsets=[0]
for line in lines:offsets.append(offsets[-1]+len(line))
swaps=[]
for node in ast.walk(tree):
 if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='read_bytes' and not node.args and not node.keywords:
  lo=offsets[node.lineno-1]+node.col_offset;hi=offsets[node.end_lineno-1]+node.end_col_offset
  swaps.append((lo,hi,'read_bytes('+ast.unparse(node.func.value)+')'))
for lo,hi,value in sorted(swaps,reverse=True):s=s[:lo]+value+s[hi:]
ast.parse(s)
(H/'package-logdump.py').write_text(s)
def fn(src,n):
 t=ast.parse(src);node=next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n)
 return '\n'.join(src.splitlines()[node.lineno-1:node.end_lineno])
assert fn(old,'parse_fat')==fn(s,'parse_fat')
a=old[old.index('        # Require all changed bytes'):old.index('        r.update(passed=True')]
b=s[s.index('        # Require all changed bytes'):s.index('        r.update(passed=True')]
assert a==b.replace('read_bytes(target)','target.read_bytes()')
save={'parent_script_sha256':sha(B.read_bytes()),'candidate_sha256':sha((H/'package-logdump.py').read_bytes()),
 'parse_fat_function_unchanged':True,'parse_fat_function_sha256':sha(fn(s,'parse_fat').encode()),
 'ranges_and_fsck_sequence_unchanged_after_IO_substitution':True,'ranges_and_fsck_original_sha256':sha(a.encode()),
 'ranges_and_fsck_IO_substitution':'read_bytes(target) in place of target.read_bytes() only',
 'bounded_file_reads':len(swaps),'bounded_read_chunk_bytes':1048576,'parser_content_remain_bytes':True,
 'new_size_equality':"b['files']['Image']['size']==len(image)",
 'old_size_equality':"b['files']['Image']['size']==a['files']['Image']['size']",
 'old_501_fixed_Image_bytes':59243008,'new_Image_length_may_differ':True,
 'only_private_FAT_Image':True,'new_Image_not_read_by_generator':True}
(H/'reuse-result.json').write_text(json.dumps(save,indent=2)+'\n')
print(json.dumps(save))
