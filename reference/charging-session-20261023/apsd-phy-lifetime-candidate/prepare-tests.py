"""Extract actual candidate functions; fake only OS/MMIO and old owner join."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
src=(H/'phy-qcom-snps-femto-v2.c').read_text()
owner=(H/'samurai-apsd-owner.c').read_text()
manifest=[]
def fn(s,name,source):
 m=re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|bool|void)\s+(?:__maybe_unused\s+)?'+name+r'\([^;]*?\)\s*\{',s,re.M)
 assert m,name
 i=s.index('{',m.start())+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 b=s[m.start():i]
 manifest.append(dict(function=name,source=source,line=s[:m.start()].count('\n')+1,sha256=sha(b.encode())))
 return b
macros='\n'.join(l for l in src.splitlines() if l.startswith('#define ') and not l.startswith('#define SNPS_HS_NUM_VREGS'))
struct=re.search(r'^struct qcom_snps_hsphy \{.*?^\};',src,re.S|re.M).group()
header=(H/'phy-qcom-snps-femto-v2-window.h').read_text()
header='\n'.join(l for l in header.splitlines() if not l.startswith('#include'))
(H/'tested-types.inc').write_text(macros+'\n#define SNPS_HS_NUM_VREGS 3\n'+header+'\n'+struct+'\n')
arrays='\n'.join(re.search(r'static const u32 '+n+r'\[\] = \{.*?\};',src,re.S).group() for n in
 ['qcom_snps_hsphy_window_offsets','qcom_snps_hsphy_window_masks','qcom_snps_hsphy_window_values'])
pre=['qcom_snps_hsphy_window_busy','qcom_snps_hsphy_window_write','qcom_snps_hsphy_window_begin_active','qcom_snps_hsphy_window_end_active']
post=['qcom_snps_hsphy_write_mask','qcom_snps_hsphy_suspend','qcom_snps_hsphy_resume','qcom_snps_hsphy_runtime_suspend','qcom_snps_hsphy_runtime_resume',
 'qcom_snps_hsphy_set_mode','qcom_snps_hsphy_init','qcom_snps_hsphy_exit','qcom_snps_hsphy_prepare','qcom_snps_hsphy_complete',
 'qcom_snps_hsphy_withdraw','qcom_snps_hsphy_remove','qcom_snps_hsphy_shutdown','qcom_snps_hsphy_probe']
(H/'tested-functions.inc').write_text('static const struct phy_ops qcom_snps_hsphy_gen_ops;\n'+arrays+'\n'+
 '\n\n'.join(fn(src,n,'phy-candidate') for n in pre)+'\n#include "phy-lifetime.inc"\n'+
 '\n\n'.join(fn(src,n,'phy-candidate') for n in post)+'\n')
names=['owner_free','owner_pd_get','owner_pd_put','owner_phy_binding_matches','owner_phy_cancel_join','owner_phy_complete','owner_phy_attach','owner_phy_detach','owner_entry_gate']
(H/'tested-owner.inc').write_text('\n\n'.join(fn(owner,n,'owner-candidate') for n in names)+'\n')
(H/'function-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(extracted_functions=len(manifest),lifecycle_include_sha256=sha((H/'phy-lifetime.inc').read_bytes()))))
