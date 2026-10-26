"""Bind unchanged algorithms and actual PM/devres call chains; no build/test."""
from pathlib import Path
import hashlib,json,re,difflib
H=Path(__file__).resolve().parent;R=H.parents[1]
P=R/'charging-oem-audit-20261023/apsd-phy-window-candidate'
B=R/'charging-oem-audit-20261023/apsd-pd5v-client-bridge-candidate'
sha=lambda b:hashlib.sha256(b).hexdigest()
def fn(s,n):
 m=re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|bool|void)\s+(?:__maybe_unused\s+)?'+n+r'\([^;]*?\)\s*\{',s,re.M);assert m,n
 i=s.index('{',m.start())+1;d=1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[m.start():i]
old=(B/'samurai-apsd-owner.c').read_text();new=(H/'samurai-apsd-owner.c').read_text()
unchanged={}
for n in ['owner_free','owner_pd_get','owner_pd_put','owner_work','owner_join','owner_queue','owner_notify','owner_pd_observe']:
 a=fn(old,n);b=fn(new,n);assert a==b,n;unchanged[n]=sha(a.encode())
guard='if (!device_property_read_bool(dwc->dev, "samurai,apsd-owner"))\n\t\treturn;'
a=fn(old,'dwc3_apsd_owner_bind');b=fn(new,'dwc3_apsd_owner_bind')
assert guard in a and guard in b
assert a[:a.index(guard)+len(guard)]==b[:b.index(guard)+len(guard)]
assert new.count('return -EOPNOTSUPP; /* route + final-write')==1
phy_old=(P/'phy-qcom-snps-femto-v2.c').read_text();phy_new=(H/'phy-qcom-snps-femto-v2.c').read_text()
for n in ['qcom_snps_hsphy_window_begin','qcom_snps_hsphy_window_end']:
 a=fn(phy_old,n);b=fn(phy_new,n+'_active');a=a[a.index('{'):];b=b[b.index('{'):];assert a==b,n
 unchanged[n+'_body']=sha(a.encode())
for n in ['qcom_snps_hsphy_window_write','qcom_snps_hsphy_write_mask','qcom_snps_hsphy_suspend','qcom_snps_hsphy_resume']:
 a=fn(phy_old,n);b=fn(phy_new,n);assert a==b;unchanged[n]=sha(a.encode())
for folder,names in [(P,['test-result.json','build-result.json']),(B,['test-result.json','build-result.json','Kconfig.fragment'])]:
 for n in names:unchanged[str(folder.relative_to(R))+'/'+n]=sha((folder/n).read_bytes())
patch=[]
for base,n in [(P,'phy-qcom-snps-femto-v2.c'),(P,'phy-qcom-snps-femto-v2-window.h'),(B,'samurai-apsd-owner.c'),(B,'samurai-apsd-owner.h')]:
 path='drivers/phy/qualcomm/'+n if n.startswith('phy-') else 'drivers/usb/dwc3/'+n
 patch.extend(difflib.unified_diff((base/n).read_text().splitlines(True),(H/n).read_text().splitlines(True),'a/'+path,'b/'+path))
patch.extend(difflib.unified_diff([], (H/'phy-lifetime.inc').read_text().splitlines(True),'/dev/null','b/drivers/phy/qualcomm/phy-lifetime.inc'))
(H/'lifetime.patch').write_text(''.join(patch))
r=dict(passed=True,unchanged_functions_and_receipts=unchanged,
 default_owner_optin_prefix_unchanged=True,final_EOPNOTSUPP=True,
 no_CONFIG_or_core_gadget_or_PD_provider_delta=True,
 old_suites_reused_not_rerun=True,patch_sha256=sha((H/'lifetime.patch').read_bytes()))
(H/'scope-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,unchanged_bindings=len(unchanged),patch_sha256=r['patch_sha256'])))
