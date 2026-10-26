"""Compile the actual candidate encoders against tiny userspace providers."""
from pathlib import Path
import re,shutil
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;inc=P/'include'
shutil.copytree(P.parent/'kernel402/include',inc,dirs_exist_ok=True)
(inc/'camss-icp-a5-colour.h').write_bytes((P/'camss-icp-a5-colour.h.proposed').read_bytes())
(inc/'linux/kernel.h').write_text('#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))\n')
types=(inc/'linux/types.h').read_text();types+='\ntypedef int32_t s32;\n';(inc/'linux/types.h').write_text(types)
c=(P/'camss-icp-a5-colour.c.proposed').read_text();(P/'colour.c').write_text(c)
s=(P/'camss-icp-a5-ipe.c.before').read_text();f=re.search(r'int camss_a5_ipe_encode_bypass_iq\([^;]+?\n\{.*?^\}\n',s,re.S|re.M);assert f
(P/'bypass.c').write_text('#include <string.h>\n#include <linux/errno.h>\n#include <linux/unaligned.h>\n#include "camss-icp-a5-ipe.h"\n'+f[0])
print('Prepared candidate codecs and userspace providers.')
