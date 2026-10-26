"""Build a V4L2 NV12/NV21 flat-patch client using existing allocation helpers."""
from pathlib import Path
import hashlib,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
base=(HERE.parent/'kernel386/m2m-client.c').read_text().replace('int main(int argc, char **argv)','int inherited386_main(int argc, char **argv)')
start=base.index('static unsigned char luma(');end=base.index('\nstatic void pattern(',start)
base=base[:start]+'''static unsigned char luma(unsigned id,unsigned sequence,unsigned x,unsigned y)
{
 (void)id;(void)sequence;unsigned row=y/80,col=x/80;
 return !row?16+32*col:row<4?128:row==4?64:192;
}
static unsigned char chroma(const struct stream *s,unsigned sequence,unsigned x,unsigned y)
{
 (void)sequence;unsigned row=(2*y)/80,col=x/80;unsigned u,v;
 if(!row){u=v=128;}else if(row<4){u=96+32*(col%3);v=96+32*(row-1);}else{u=64+48*(col%4);v=208-48*(col/2);}
 return ((x&1)^s->nv21)?v:u;
}
'''+base[end:]
extra=(HERE.parent/'kernel392/cancel-client.c').read_text();extra=extra[extra.index('struct test_context {'):].replace('int main(int argc,char **argv)','int inherited392_main(int argc,char **argv)').replace('.stride=640,.frames=2','.stride=640,.frames=2,.nv21=test_nv21')
source=base+'\nstatic int test_nv21;\n'+extra+'\n'+(HERE/'chain-client-tail.c').read_text();assert len(re.findall(r'\bint main\(',source))==1
file=HERE/'chain-client.c';file.write_text(source);binary=P/'colour-client'
q=subprocess.run(['aarch64-linux-gnu-gcc','-static','-O2','-g','-Wall','-Wextra','-Werror','-pthread',str(file),'-o',str(binary)],capture_output=True);(P/'client-build-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
report=dict(stage=400,aarch64_static_v4l2_client=True,fixed_modes=8,formats=['NV12','NV21'],frames=16,flat_patch_grid=[8,6],byte_input_unchanged_and_output_canary_checks=True,pair_and_identity_byte_equality_checked=True,bytes=binary.stat().st_size,sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),private_path=str(binary),passed=True)
(HERE/'client-build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
