from pathlib import Path
import ast,hashlib,json,os,shlex,struct,subprocess
os.umask(0o077)
here=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel210/baseline-dtb');out.mkdir(mode=0o700)
names=['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={name:sha(k/name) for name in names}
recipe=(k/'arch/arm64/boot/dts/qcom/.sm8150-samurai.dtb.cmd').read_text().splitlines()[0].split(':=',1)[1]
commands=[];current=[]
for token in shlex.split(recipe):
    if token==';':commands.append(current);current=[]
    else:current.append(token)
commands.append(current)
assert len(commands)==3 and commands[0][0]=='gcc' and commands[1][0]=='./scripts/dtc/dtc' and commands[2][0]=='cat'
base='arch/arm64/boot/dts/qcom/'
mapping={base+'.sm8150-samurai.dtb.d.pre.tmp':str(out/'source-pre.d'),base+'.sm8150-samurai.dtb.d.dtc.tmp':str(out/'dtc.d'),base+'.sm8150-samurai.dtb.dts.tmp':str(out/'baseline.pp.dts'),base+'sm8150-samurai.dtb':str(out/'baseline.dtb')}
def rewrite(value):
    for original,target in sorted(mapping.items(),key=lambda item:-len(item[0])):value=value.replace(original,target)
    return value
for index,args in enumerate(commands[:2]):
    command=[rewrite(value) for value in args]
    assert Path(command[command.index('-o')+1]).parent==out
    p=subprocess.run(command,cwd=k,capture_output=True)
    (out/(str(index)+'-private.log')).write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,'Inspect private baseline compile failure'
source=ast.parse((here.parent/'kernel104/verify-firmware.py').read_text());function=next(node for node in source.body if isinstance(node,ast.FunctionDef) and node.name=='fdt_nodes')
namespace={'struct':struct,'align':lambda n,a:(n+a-1)//a*a};exec(compile(ast.Module(body=[function],type_ignores=[]),'known-fdt-parser','exec'),namespace)
parse=namespace['fdt_nodes']
deployed=out.parent.parent/'kernel204/sm8150-samurai-bt-wake-static-private.dtb'
assert sha(deployed)=='b9d9c2a141d46a746fb517394d235e9cca349d534652a391480e8b7b5aeae79b'
old=parse(deployed.read_bytes());new=parse((out/'baseline.dtb').read_bytes())
changes=[dict(path=path,property=name) for path in sorted(old.keys()&new.keys()) for name in sorted(old[path].keys()|new[path].keys()) if old[path].get(name)!=new[path].get(name)]
report=dict(stage=210,baseline_built_with_saved_kbuild_cpp_dtc_arguments=True,base_artifacts_unchanged=before=={name:sha(k/name) for name in names},candidate_sha256=sha(out/'baseline.dtb'),deployed_dtb_sha256=sha(deployed),byte_identical_to_deployed=(out/'baseline.dtb').read_bytes()==deployed.read_bytes(),deployed_nodes=len(old),source_nodes=len(new),only_deployed_nodes=sorted(old.keys()-new.keys()),only_source_nodes=sorted(new.keys()-old.keys()),changed_properties=changes)
assert report['base_artifacts_unchanged']
(here/'baseline-dtb-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
