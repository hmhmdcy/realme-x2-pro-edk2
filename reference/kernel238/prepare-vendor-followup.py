from pathlib import Path
import ast
R=Path(__file__).resolve().parent
source=(R/'native-vendor-audit.py').read_text().replace('k238-vendor-audit','k238-vendor-followup').replace('k238-vendor-readonly','k238-vendor-followup-readonly')
old="wanted=re.compile(r'gnss|gps|loc_launcher|xtra|izat|location_api|loc_api|loc_core|gps\\.utils',re.I)"
new="wanted=re.compile(r'^(gps\\.conf|sap\\.conf|liblbs_core\\.so|libqmi_cci\\.so|libqmi_common_so\\.so|libqti_vndfwk_detect\\.so|libloc_net_iface\\.so|libloc_socket\\.so)$',re.I)"
assert source.count(old)==1;source=source.replace(old,new)
marker=" wanted=re.compile"
extra=""" existence={}
 for name in ['etc/gps.conf','etc/sap.conf','lib64/liblbs_core.so','lib64/libqmi_cci.so','lib64/libqmi_common_so.so','lib64/libqti_vndfwk_detect.so','lib64/libloc_net_iface.so','lib64/libloc_socket.so']:
  p=mount/name;existence[name]=dict(exists=p.exists(),symlink=p.is_symlink(),is_regular=p.is_file() and not p.is_symlink(),target=os.readlink(p) if p.is_symlink() else None)
 (out/'exact-paths-private.json').write_text(json.dumps(existence,indent=2)+'\\n')
 listing={p.name:dict(directory=p.is_dir() and not p.is_symlink(),symlink=p.is_symlink(),target=os.readlink(p) if p.is_symlink() else None) for p in (mount/'etc').iterdir()}
 (out/'etc-root-listing-private.json').write_text(json.dumps(listing,indent=2)+'\\n')
 nested=[]
 for p in (mount/'etc').rglob('*'):
  if p.name in ['gps.conf','sap.conf']:
   nested.append(str(p.relative_to(mount)));select(p)
 (out/'nested-gps-sap-paths-private.json').write_text(json.dumps(nested,indent=2)+'\\n')
"""
assert source.count(marker)==1;source=source.replace(marker,extra+marker)
source=source.replace("before=digest(block)","before=digest(block)\n assert before==(root/'k238-vendor-audit/vendor-before-private.sha256').read_text().split()[0]")
start=(R/'start-vendor-audit.py').read_text().replace('native-vendor-audit.py','native-vendor-followup.py').replace('k238-vendor-audit','k238-vendor-followup').replace('vendor-launch','vendor-followup-launch')
start=start.replace("assert not p.exists();p.mkdir(mode=0o700)","assert p.is_dir()")
poll=(R/'poll-vendor-audit.py').read_text().replace('k238-vendor-audit','k238-vendor-followup').replace('vendor-audit-validation.json','vendor-followup-validation.json').replace('vendor-poll','vendor-followup-poll')
export=(R/'export-vendor.py').read_text().replace('k238-vendor-audit','k238-vendor-followup').replace('vendor-source-private','vendor-followup-source-private').replace('vendor-native-manifest-private.json','vendor-followup-native-manifest-private.json').replace('vendor-export-validation.json','vendor-followup-export-validation.json')
for name,text in [('native-vendor-followup.py',source),('start-vendor-followup.py',start),('poll-vendor-followup.py',poll),('export-vendor-followup.py',export)]:
 ast.parse(text);p=R/name;assert not p.exists();p.write_text(text)
print('Prepared exact source/config presence and LBS core dependency followup, first source retained')
