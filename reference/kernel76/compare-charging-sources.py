from pathlib import Path
import hashlib, json, re, subprocess, tarfile

OUT = Path('/mnt/e/edk2-samurai-out/kernel76/charging-research')
VENDOR = '/mnt/e/Realme X2 Pro移植主线Linux/sources/realme-downstream.git'
COMMIT = '9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
def git_source(path):
    raw = subprocess.check_output(['git','--git-dir='+VENDOR,'cat-file','-p',COMMIT+':'+path])
    dest = OUT/('stock--'+path.replace('/','--'))
    dest.write_bytes(raw)
    return dest

paths = [
 'drivers/power/oppo/charger_ic/Makefile',
 'drivers/power/oppo/Makefile',
 'drivers/power/oppo/charger_ic/oppo_battery_msm8150_pro.c',
 'drivers/power/oppo/oppo_charger.c',
 'drivers/power/oppo/oppo_charger.h',
 'drivers/power/supply/qcom/qpnp-smb5.c',
 'drivers/power/supply/qcom/smb5-lib.c',
 'Makefile',
]
record = {'stock':[], 'related':[], 'live':{}, 'upstream_smbx':[]}
kernel = Path('/home/cy122/x2pro-linux/linux')
for path in ['drivers/power/supply/qcom_smbx.c','Documentation/devicetree/bindings/power/supply/qcom,pmi8998-charger.yaml']:
    p = kernel/path
    if p.exists():
        record['upstream_smbx'].append({'path':path,'matches':[{'line':i+1,'text':l} for i,l in enumerate(p.read_text().splitlines()) if re.search(r'compatible|SMB[25]|smb[25]|pm8150|pmi8998|pmi632|\.data\s*=',l)]})
for path in paths:
    try:
        dest = git_source(path)
        lines = dest.read_text(errors='replace').splitlines()
        selected = set()
        for i,line in enumerate(lines):
            if re.search(r'oppo_get_chg_ops|OPPO_MP2650|vbatt_num.*2|oppo_chg_check_tbatt_is_good|oppo_chg_check_vbatt_is_good', line):
                selected.update(range(max(0,i-3),min(len(lines),i+10)))
        if path.endswith('Makefile'):
            selected.update(range(min(8,len(lines))))
        record['stock'].append({'path':path,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'excerpts':[{'line':i+1,'text':lines[i]} for i in sorted(selected)][:130]})
    except Exception as exc:
        record['stock'].append({'path':path,'error':str(exc)})

for name in ['oppo-ace--msm-4.14--arch--arm64--boot--dts--19081--sm8150-mtp.dtsi',
             'oppo-ace--msm-4.14--arch--arm64--boot--dts--19081--pm8150b.dtsi',
             'oneplus--arch--arm64--boot--dts--qcom--pm8150b.dtsi',
             'oppo-ace--msm-4.14--Makefile','oneplus--Makefile','mainline--Makefile']:
    p = OUT/name
    lines = p.read_text(errors='replace').splitlines()
    selected = set(range(min(8,len(lines)))) if name.endswith('--Makefile') else set()
    for i,line in enumerate(lines):
        if re.search(r'&qupv3_se(?:1|15)_i2c|mp2650-charger|bq27541-battery|batt_bq28|vbatt_num|temp_bat|mps_otg_en-gpio|temp_normal_vfloat_mv|temp_normal_fastchg_current_ma',line):
            selected.update(range(max(0,i-2),min(len(lines),i+8)))
    record['related'].append({'saved':name,'excerpts':[{'line':i+1,'text':lines[i]} for i in sorted(selected)]})

archive = '/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar'
with tarfile.open(archive) as tar:
    props = {m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
nodes = json.loads((OUT/'local-safety-inspection.json').read_text())['live_nodes']
for node in nodes:
    row = {p[len(node)+1:]:v.hex() for p,v in props.items() if p.rsplit('/',1)[0] == node and p.endswith(('/reg','/compatible','/status'))}
    row['ancestor_statuses'] = {p:props[p].rstrip(b'\0').decode() for i in range(2,len(node.split('/'))) if (p:='/'.join(node.split('/')[:i])+'/status') in props}
    record['live'][node] = row
(OUT/'source-comparison.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'stock_count':len(record['stock']), 'related_count':len(record['related']), 'live':record['live'], 'upstream_smbx':record['upstream_smbx']},indent=2))
