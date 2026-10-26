from pathlib import Path
import ast

ref=Path(__file__).resolve().parent;old=ref.parent/'kernel199'
names=['collect-front-before.py','inspect-live-resources.py','stage-live-tools.py','prepare-physical-live-native.py','build-live-overlay.py','capture-front-mmcx-repeat.py']
for name in names:
 s=(old/name).read_text().replace('k199','k200').replace('stage=199','stage=200').replace('k200-baseline','k200-camera-baseline')
 s=s.replace("read_text().strip()=='512'", "read_text().strip()=='0'")
 # The common phone-side prefix is historical source, so change its guard explicitly before exec.
 if "exec(compile(common," in s:
  s=s.replace("exec(compile(common,", "common=common.replace(\"read_text().strip()=='512'\",\"read_text().strip()=='0'\");exec(compile(common,")
 if name=='inspect-live-resources.py':s=s.replace("struct.unpack('>6I'", "struct.unpack('>8I'")
 if name=='stage-live-tools.py':
  s=s.replace("assert Path('/var/lib/samurai/k200-modules').is_dir() and not Path('/var/lib/samurai/k200-modules/manifest.json').exists()", "assert not Path('/var/lib/samurai/k200-modules').exists()\nPath('/var/lib/samurai/k200-modules').mkdir(mode=0o700)")
 if name=='build-live-overlay.py':
  s=s.replace("values=dict(RPMHPD_PHANDLE=data['mmcx']['provider_phandle'],", "values=dict(")
 if name=='prepare-physical-live-native.py':
  s=s.replace("g['ctl']==(0 if g['pin']==15 else 1)","g['ctl']==1 and g['level']==0")
 if name=='capture-front-mmcx-repeat.py':
  start=s.index(" original_camss=Path(")
  end=s.index(" report['clock_lookup']",start)
  s=s[:start]+" rebind(True);report['persistent_candidate_rebound']=True;save()\n"+s[end:]
  # Normal permanent module stays installed and loaded; only notifier binding is refreshed.
  start=s.index(' if camss_candidate_loaded:',s.index('\nfinally:'))
  end=s.index(" if Path('/sys/module/imx471')",start)
  s=s[:start]+s[end:]
  start=s.index(' if camss_original_removed:',s.index('\nfinally:'))
  end=s.index(' if camss_refreshed:',start)
  s=s[:start]+" if camss_refreshed:rebind(True)\n"+s[end:]
  s=s.replace("struct.unpack('>6I'", "struct.unpack('>8I'").replace("report['taint']==512", "report['taint']==0")
  # Private per-frame pixel statistics remain in the private summary, not console output.
  s=s.replace("'capture_returncode','frames','camss_original_graph_restored'", "'capture_returncode','camss_original_graph_restored'")
 ast.parse(s);(ref/name).write_text(s)
# Existing sensor-only overlay avoids any replacement of the static CAMSS domain properties.
(ref/'front-probe-overlay.dtso').write_bytes((ref.parent/'kernel196/front-probe-overlay.dtso').read_bytes())
print('K200_STATIC_DT_CAMERA_TEST_SCRIPTS_PREPARED_NO_POWER_DOMAIN_OVERLAY_OR_MODULE_SWAP')
