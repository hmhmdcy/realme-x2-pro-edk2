from pathlib import Path
import hashlib, json, re, subprocess

k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel168')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel168')
def function(s,name):
    hit=re.search(r'^(?:static (?:inline )?)?(?:int |void |bool |u32 \*)(?:__maybe_unused )?'+name+r'\([^;{]*\)\n\{',s,re.M)
    assert hit,name
    start=hit.start();a=s.index('{',start);depth=1;b=a+1
    while depth:
        depth+=(s[b]=='{')-(s[b]=='}');b+=1
    return s[start:b]+'\n'
def run(label,source,expected=0):
    path=out/(label+'-private.c');path.write_text(source)
    binary=out/(label+'-private')
    build=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Wno-unused-variable','-Wno-unused-function','-Wno-unused-parameter','-Werror','-g','-fsanitize=address,undefined',str(path),'-o',str(binary)],capture_output=True)
    (out/(label+'-build-private.log')).write_bytes(build.stdout+build.stderr)
    assert build.returncode==0,(label,build.stderr.decode())
    result=subprocess.run([str(binary)],capture_output=True)
    (out/(label+'-run-private.log')).write_bytes(result.stdout+result.stderr)
    assert result.returncode==expected,(label,result.stdout.decode(),result.stderr.decode())
    assert not result.stderr,label
    return result.stdout.decode().strip()

ngd=(k/"drivers/slimbus/qcom-ngd-ctrl.c").read_text()
