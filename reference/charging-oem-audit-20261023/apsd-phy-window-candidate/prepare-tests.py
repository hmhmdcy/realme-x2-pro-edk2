"""Extract complete candidate and generic-PHY functions; no model rewrite."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'apsd-integration/current-r7/snapshots'
text=(HERE/'phy-qcom-snps-femto-v2.c').read_text()
core=(BASE/'drivers--phy--phy-core.c').read_text()
def function(s,name):
 m=re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|bool|void)\s+(?:__maybe_unused\s+)?'+name+r'\([^;]*?\)\s*\{',s,re.M)
 assert m,name
 start=m.start();i=s.index('{',start)+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[start:i]
names=['qcom_snps_hsphy_window_busy','qcom_snps_hsphy_window_write',
 'qcom_snps_hsphy_window_begin','qcom_snps_hsphy_window_end','qcom_snps_hsphy_write_mask',
 'qcom_snps_hsphy_suspend','qcom_snps_hsphy_resume',
 'qcom_snps_hsphy_runtime_suspend','qcom_snps_hsphy_runtime_resume',
 'qcom_snps_hsphy_set_mode','qcom_snps_hsphy_init','qcom_snps_hsphy_exit']
functions=[function(text,n) for n in names]+[function(core,n) for n in ['phy_init','phy_exit','phy_set_mode_ext']]
manifest=[]
for n,b in zip(names+['phy_init','phy_exit','phy_set_mode_ext'],functions):
 s=text if n in names else core
 manifest.append(dict(function=n,line=s[:s.index(b)].count('\n')+1,sha256=hashlib.sha256(b.encode()).hexdigest(),source='candidate' if n in names else 'fixed-generic-phy-core'))
arrays='\n'.join(re.search(r'static const u32 '+n+r'\[\] = \{.*?\};',text,re.S).group() for n in
 ['qcom_snps_hsphy_window_offsets','qcom_snps_hsphy_window_masks','qcom_snps_hsphy_window_values'])
(HERE/'tested-functions.inc').write_text('static const struct phy_ops qcom_snps_hsphy_gen_ops;\n'+arrays+'\n\n'+'\n\n'.join(functions)+'\n')
header=(HERE/'phy-qcom-snps-femto-v2-window.h').read_text()
types=header[header.index('enum qcom_snps_hsphy_window_state'):header.index('int qcom_snps_hsphy_window_begin')]
macros='\n'.join(l for l in text.splitlines() if l.startswith('#define ') and not l.startswith('#define SNPS_HS_NUM_VREGS'))
struct=re.search(r'^struct qcom_snps_hsphy \{.*?^\};',text,re.S|re.M).group()
(HERE/'tested-types.inc').write_text(macros+'\n#define SNPS_HS_NUM_VREGS 3\n'+types+'\n'+struct+'\n')
(HERE/'function-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'actual_functions':len(functions)}))
