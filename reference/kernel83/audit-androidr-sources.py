"""Audit pinned Android R / user-named kernel sources entirely offline.

Source downloads, the Android DT tar and full configuration stay private.
This inspects source text and archived DT properties; it never accesses a device
and does not validate a charging controller or a hardware protection circuit.
"""
from pathlib import Path
import hashlib,json,re,struct,tarfile

OUT=Path('/mnt/e/edk2-samurai-out/kernel83')
ARCHIVE=Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar')
ARCHIVE_SHA='e3329db4f3568252286489abd2ae27b9cbd0c711a2c5d790ebfba80fffc5b56b'
CYBORG='cyborgdc2000/kernel_realme_sm8150'
OFFICIAL='realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source'
rows={}
for name in ['confirmed-repositories.json','charging-source-manifest.json','board-source-manifest.json','board-includes-manifest.json','cyborg-dt-layout.json']:
    data=json.loads((OUT/name).read_text())
    if name=='confirmed-repositories.json':
        data=[dict(f,repo=r['repo'],commit=r['commit']) for r in data['repositories'] for f in r['files']]
    else:data=data['files']
    for row in data:
        key=(row.get('repo',CYBORG),row['path'])
        if key in rows:assert rows[key]['sha256']==row['sha256']
        rows[key]=dict(row,repo=key[0])
for (repo,path),row in rows.items():
    file=OUT/(repo.replace('/','--')+'--'+path.replace('/','--'))
    assert file.stat().st_size==row['bytes']
    assert hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']

def text(repo,path):
    assert (repo,path) in rows
    return (OUT/(repo.replace('/','--')+'--'+path.replace('/','--'))).read_text()
def uncomments(source):
    return re.sub(r'/\*.*?\*/|//[^\n]*','',source,flags=re.S)
def block(source,needle):
    pos=source.index(needle);start=source.index('{',pos);depth=1;end=start+1
    while depth:
        depth+=int(source[end]=='{')-int(source[end]=='}');end+=1
    return source[start+1:end-1]
def scalar(source,key):
    matches=re.findall(re.escape(key)+r'\s*=\s*<\s*([0-9xXa-fA-F]+)\s*>',source)
    assert len(matches)==1,(key,matches)
    return int(matches[0],0)
def compatible(source):return re.search(r'compatible\s*=\s*"([^"]+)"',source)[1]

with tarfile.open(ARCHIVE) as tar:
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==ARCHIVE_SHA
    archive={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
archive_nodes=[]
for path,raw in archive.items():
    if path.endswith('/compatible') and any(path.rsplit('/',2)[-2].endswith('@'+addr) for addr in ['5c','55','58']):
        root=path.rsplit('/',1)[0];reg=archive[root+'/reg']
        archive_nodes.append({'path':root,'compatible':raw.rstrip(b'\0').decode(),'reg_cells':list(struct.unpack('>'+str(len(reg)//4)+'I',reg))})
assert len(archive_nodes)==3
policy_node='soc/qcom,spmi@c440000/qcom,pm8150b@2/qcom,qpnp-smb5'
keys=['removed_bat_decidegc','cold_bat_decidegc','little_cold_bat_decidegc','cool_bat_decidegc','little_cool_bat_decidegc','normal_bat_decidegc','warm_bat_decidegc','hot_bat_decidegc','vbatt_num','max_chg_time_sec','input_current_usb_ma','temp_normal_vfloat_mv','normal_vfloat_over_sw_limit','vbatt_hv_thr']
archived_policy={key:struct.unpack('>I',archive[policy_node+'/qcom,'+key])[0] for key in keys}
boards=[]
for repo,directory in [(CYBORG,'qcom'),(OFFICIAL,'19781')]:
    prefix='arch/arm64/boot/dts/'+directory+'/'
    pm=uncomments(text(repo,prefix+'sm8150-pmic-overlay.dtsi'))
    nodes=[]
    for bus,node in [('qupv3_se1_i2c','mp2650-charger@5c'),('qupv3_se15_i2c','bq27541-battery@55'),('qupv3_se15_i2c','oplus_short-ic@58')]:
        body=block(block(pm,'&'+bus),node)
        reg=re.search(r'reg\s*=\s*<([^>]+)>',body)[1]
        nodes.append({'bus':bus,'node':node,'compatible':compatible(body),'reg_cells':[int(x,0) for x in reg.split()],
                      'batt_bq28z610':'qcom,batt_bq28z610;' in body})
    dt=uncomments(text(repo,prefix+'pm8150b.dtsi'))
    policy={key:scalar(dt,'qcom,'+key) for key in keys}
    assert policy==archived_policy
    assert nodes[0]['reg_cells'][0]==0x5c and nodes[1]['reg_cells']==[0x55] and nodes[2]['reg_cells']==[0x58]
    assert nodes[1]['batt_bq28z610']
    overlay=uncomments(text(repo,prefix+'sm8150-mtp-overlay.dts'))
    assert scalar(overlay,'oppo,dtsi_no')==19781
    board={'repo':repo,'directory':prefix,'overlay_project':19781,'nodes':nodes,'policy_raw':policy}
    parser=text(repo,'drivers/power/oppo/oplus_charger.c')
    assert 'chip->limits.removed_bat_decidegc = -batt_removed_degree_negative;' in parser
    assert 'chip->limits.cold_bat_decidegc = -batt_cold_degree_negative;' in parser
    assert 'get_eng_version() == HIGH_TEMP_AGING' in parser
    board['normal_temperature_decidegrees_C']={key:(-policy[key] if key in ['removed_bat_decidegc','cold_bat_decidegc'] else policy[key]) for key in keys[:8]}
    boards.append(board)

equal=[]
for name in ['oplus_short_ic.c','oplus_short_ic.h','oplus_bq27541.c']:
    path='drivers/power/oppo/'+('gauge_ic/' if 'bq27541' in name else 'charger_ic/')+name
    assert rows[(CYBORG,path)]['sha256']==rows[(OFFICIAL,path)]['sha256']
    equal.append({'path':path,'sha256':rows[(CYBORG,path)]['sha256']})

mp_path='drivers/power/oppo/charger_ic/oplus_mp2650.c'
removed=['mp2650_float_voltage_write(WPC_TERMINATION_VOLTAGE);','mp2650_set_prechg_current(WPC_PRECHARGE_CURRENT);','mp2650_charging_current_write_fast(WPC_CHARGE_CURRENT_DEFAULT);','mp2650_set_termchg_current(WPC_TERMINATION_CURRENT);','mp2650_set_rechg_voltage(WPC_RECHARGE_VOLTAGE_OFFSET);']
mp={}
for repo in [CYBORG,OFFICIAL]:
    init=block(uncomments(text(repo,mp_path)),'int mp2650_hardware_init(')
    assert 'mp2650_reset_charger();' in init
    assert 'mp2650_set_complete_charge_timeout(OVERTIME_DISABLED);' in init
    mp[repo]={'source_sha256':rows[(repo,mp_path)]['sha256'],'init_resets_charger':True,'init_disables_safety_timer':True,'WPC_default_calls_present':[call for call in removed if call in init]}
assert mp[CYBORG]['WPC_default_calls_present']==[] and mp[OFFICIAL]['WPC_default_calls_present']==removed

config=text(CYBORG,'arch/arm64/configs/samurai_defconfig')
flags=['CONFIG_OPLUS_SM8150R_CHARGER','CONFIG_OPLUS_SHORT_C_BATT_CHECK','CONFIG_OPLUS_SHORT_HW_CHECK','CONFIG_OPLUS_SHORT_IC_CHECK','CONFIG_OPLUS_SHORT_USERSPACE']
assert all(flag+'=y' in config.splitlines() for flag in flags)
cy_make=text(CYBORG,'drivers/power/oppo/charger_ic/Makefile')
assert 'obj-y\t+= oplus_mp2650.o' in cy_make and 'obj-y\t+= oplus_battery_msm8150Q.o' in cy_make
official_make=text(OFFICIAL,'drivers/power/oppo/charger_ic/Makefile')
branch=official_make.split('else ifeq ($(CONFIG_OPLUS_SM8150R_CHARGER),y)',1)[1].split('else',1)[0]
assert 'oplus_battery_msm8150Q.o' in branch and 'oplus_mp2650.o' in branch
boardconfig=text('cyborgdc2000/android_device_realme_samurai','BoardConfig.mk')
assert 'TARGET_KERNEL_CONFIG := samurai_defconfig vendor/debugfs.config' in boardconfig
assert 'TARGET_KERNEL_SOURCE := kernel/realme/sm8150' in boardconfig

base=text(CYBORG,'drivers/i2c/i2c-core-base.c')
assert 'if (i2c_match_id(driver->id_table, client))' in block(base,'static int i2c_device_match(')
of=text(CYBORG,'drivers/i2c/i2c-core-of.c')
assert 'of_modalias_node(node, info.type, sizeof(info.type))' in of
of_base=block(text(CYBORG,'drivers/of/base.c'),'int of_modalias_node(')
assert "p = strchr(compatible, ',');" in of_base
assert 'strlcpy(modalias, p ? p + 1 : compatible, len);' in of_base
matching=[]
for node,path,id_name in [('bq27541-battery@55','drivers/power/oppo/gauge_ic/oplus_bq27541.c','bq27541-battery'),('oplus_short-ic@58','drivers/power/oppo/charger_ic/oplus_short_ic.c','oplus_short-ic'),('mp2650-charger@5c',mp_path,'mp2650-charger')]:
    driver=text(CYBORG,path)
    dtcomp=next(n['compatible'] for n in boards[0]['nodes'] if n['node']==node)
    ofcomp=re.findall(r'\.compatible\s*=\s*"([^"]+)"',driver)
    assert re.search(r'\{\s*"'+re.escape(id_name)+r'"\s*,',driver)
    assert dtcomp.split(',',1)[1]==id_name
    matching.append({'node':node,'cyborg_DT_compatible':dtcomp,'driver_OF_compatibles':ofcomp,'exact_OF_match':dtcomp in ofcomp,
                     'I2C_id_suffix_match':True,'binding_observed_on_installed_Android':False})

versions={}
for repo in [CYBORG,OFFICIAL]:
    make=text(repo,'Makefile')
    parts={key:re.search('^'+key+r'[ \t]*=[ \t]*(.*)$',make,re.M)[1].strip() for key in ['VERSION','PATCHLEVEL','SUBLEVEL','EXTRAVERSION']}
    versions[repo]='.'.join(parts[key] for key in ['VERSION','PATCHLEVEL','SUBLEVEL'])+parts['EXTRAVERSION']
assert versions[CYBORG]=='4.14.356-openela-rc1' and versions[OFFICIAL]=='4.14.190'
result={'audit':'PASS','kind':'offline pinned source and archived DT comparison','human_context':json.loads((OUT/'confirmed-repositories.json').read_text())['human_context'],'kernel_versions':versions,
        'source_files_verified':len(rows),'archive_sha256':ARCHIVE_SHA,'archived_nodes':archive_nodes,'boards':boards,'identical_sources':equal,'mp2650_hardware_init':mp,
        'config_flags':{flag:'y' for flag in flags},'config_selection':'cyborg unconditional msm8150Q/MP2650 objects; official CONFIG_OPLUS_SM8150R_CHARGER branch selects these objects',
        'matching':matching,'normal_branch_only':True,'exact_backup_build_commit_verified':False,'hardware_identity_verified':False,'charge_control_verified':False,
        'device_interactions_this_session':False,'limitation':'Source values and matches do not establish runtime initialization, independent safety, temperature calibration or negotiated input budget.'}
(OUT/'androidr-source-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS',len(rows),'pinned files; both board policy sets match archived raw properties; identical gauge/short sources; five MP initialization calls differ.')
print('Archived node compatibility:',[(n['path'].rsplit('/',1)[-1],n['compatible']) for n in archive_nodes])
