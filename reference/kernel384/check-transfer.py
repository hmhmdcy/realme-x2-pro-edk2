"""Reuse failure-injection providers with the new actual transfer body."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel382/check-transfer.py').read_text()
s=s.replace('import host','import host')
s=s.replace("(P/'camss-icp-a5-boot.h.proposed')","(P/'camss-icp-a5-boot.h.before')")
s=s.replace("(HERE/'session-regression.c')","(HERE.parent/'kernel382/session-regression.c')")
s=s.replace('typedef uint16_t u16;typedef uint32_t u32;','typedef int32_t s32;typedef uint16_t u16;typedef uint32_t u32;')
s=s.replace('u8 *input=malloc(460800),*output=malloc(460800),stripe[2892]={0};','u8 *input=malloc(460800),*output=malloc(460800);')
s=s.replace('  put_unaligned_le32(1,stripe+20);u16 stripe_count=1;memcpy(stripe+428,&stripe_count,2);\n','')
s=s.replace('.striping=stripe,','').replace('.striping_bytes=sizeof(stripe),','')
s=s.replace('if(scenario==71)job.striping_bytes=2268;','if(scenario==71)one.io.output.width=one.io.output.stride=642;')
s=s.replace('stage=382','stage=384')
s=s.replace('external_iq_input_removed_and_kernel_defaults_checked=True,','external_iq_and_striping_inputs_removed_and_kernel_defaults_checked=True,')
s=s.replace('#define ARRAY_SIZE(x)',r'#define max(a,b) ((a)>(b)?(a):(b))\nstatic void put_unaligned_le16(u16 v,void *p){memcpy(p,&v,2);}\n#define ARRAY_SIZE(x)')
exec(compile(s,str(HERE/'check-transfer-generated.py'),'exec'),globals())
