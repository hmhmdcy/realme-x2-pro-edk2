"""Connect the existing DWC owner to the pinned PHY client API, default off."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-pd5v-client-bridge-candidate';PHY=HERE.parent/'apsd-phy-withdrawal-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
old_delivery=json.loads((OLD/'delivery.json').read_bytes());phy_delivery=json.loads((PHY/'delivery.json').read_bytes())
assert phy_delivery['passed']
for name in ['phy-qcom-snps-femto-v2.c','phy-qcom-snps-femto-v2-window.h','provider-lifetime.inc']:
    assert sha((PHY/name).read_bytes())==phy_delivery['files'][name]['sha256']
def replace(s,a,b):
    assert s.count(a)==1,a;return s.replace(a,b)
source=(OLD/'samurai-apsd-owner.c').read_text();header=(OLD/'samurai-apsd-owner.h').read_text();config=(OLD/'Kconfig.fragment').read_text()
source=replace(source,'after physical off. Route/PHY-withdrawal/final-transfer coverage is absent:',
    'after physical off. PHY withdrawal is connected; route/final-transfer coverage is absent:')
source=replace(source,'\tstruct qcom_snps_hsphy_window_result phy;','\tstruct qcom_snps_hsphy_window_result phy;\n\tstruct qcom_snps_hsphy_window_client *phy_client;')
marker='static u64 owner_now_ms(void)'
source=replace(source,marker,(HERE/'phy-client-functions.inc').read_text()+'\n\n'+marker)
source=replace(source,'/* A real PD5V lease alone is insufficient. Trusted EUD-off route, PHY\n * provider withdrawal and final-transfer revalidation remain unimplemented.',
    '/* A real PD5V lease and bound PHY client are insufficient. Trusted EUD-off\n * route and final-transfer revalidation remain unimplemented.')
source=replace(source,'return -EOPNOTSUPP; /* route + PHY withdrawal + final-write contract absent */',
    'return -EOPNOTSUPP; /* route + final-write contract absent */')
source=replace(source,'qcom_snps_hsphy_window_end(o->dwc->usb2_generic_phy[0],','qcom_snps_hsphy_window_end(o->phy_client,')
source=replace(source,'qcom_snps_hsphy_window_begin(o->dwc->usb2_generic_phy[0], &o->phy)',
    'qcom_snps_hsphy_window_begin(o->phy_client, &o->phy)')
start=source.index('static int owner_enter_windows(');position=source.index('\n\tret = pm_runtime_get_if_active',start)
source=source[:position]+'\n\tif (!o->phy_client)\n\t\treturn -ENODEV;\n'+source[position:]
source=replace(source,'\tif (owner_aborted(o))\n\t\treturn;\n\tret = owner_read(o);',
    '''\tif (owner_aborted(o))
\t\treturn;
\tret = owner_phy_resolve(o);
\tif (ret == -EAGAIN) {
\t\towner_queue(o, msecs_to_jiffies(1000));
\t\treturn;
\t}
\tif (ret) {
\t\to->primary_error = ret;
\t\tif (owner_restore(o, READ_ONCE(o->retiring)))
\t\t\towner_quarantine(o);
\t\treturn;
\t}
\tret = owner_read(o);''')
source=replace(source,'\tprotocol_history = o->once;',
    '\tif (owner_phy_release(o))\n\t\towner_quarantine(o);\n\tprotocol_history = o->once;')
header=replace(header,' DWC3_APSD_PD = 32,',' DWC3_APSD_PD = 32,\n DWC3_APSD_PHY = 64,')
config=replace(config,'Missing PD/route and EUD/PHY lifetime\n\t  coverage refuses every hardware attempt.',
    'Missing route and final-transfer\n\t  coverage refuses every hardware attempt; PHY withdrawal is joined.')
config=replace(config,'Missing route/PHY/transfer gates still deny every APSD command.',
    'Missing route/transfer gates still deny every APSD command.')
files={'samurai-apsd-owner.c':source,'samurai-apsd-owner.h':header,'Kconfig.fragment':config}
patch=''
for name,value in files.items():
    (HERE/name).write_text(value)
    prefix='drivers/usb/dwc3/'
    patch+=''.join(difflib.unified_diff((OLD/name).read_text().splitlines(True),value.splitlines(True),fromfile='a/'+prefix+name,tofile='b/'+prefix+name))
(HERE/'phy-client.patch').write_text(patch)
(HERE/'phy-qcom-snps-femto-v2-window.h').write_bytes((PHY/'phy-qcom-snps-femto-v2-window.h').read_bytes())
result=dict(prepared=True,source_files={name:sha((OLD/name).read_bytes()) for name in files},
    PHY_delivery_sha256=sha((PHY/'delivery.json').read_bytes()),PHY_header_sha256=sha((HERE/'phy-qcom-snps-femto-v2-window.h').read_bytes()),
    files={name:sha(value.encode()) for name,value in files.items()},phone_accessed=False,attempt_gate_enabled=False)
(HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(prepared=True,phone_accessed=False)))
