"""Seal the existing five-file candidate and validate only its local source form."""
from pathlib import Path
import difflib,hashlib,json,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'phosh-connection-source-r8/release-files/phosh'
FILES=['src/battery-manager.c','src/top-panel.c','src/ui/top-panel.ui','src/phosh.gresources.xml','data/icons/external-power-connected-symbolic.svg']
sha=lambda b:hashlib.sha256(b).hexdigest()
patch='';pins={}
for name in FILES:
    before=(BASE/name).read_bytes() if (BASE/name).exists() else b''
    after=(HERE/'candidate'/name).read_bytes()
    pins[name]={'base_sha256':sha(before) if before else None,'candidate_sha256':sha(after),'bytes':len(after)}
    patch+=''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='a/'+name if before else '/dev/null',tofile='b/'+name))
original=(BASE/FILES[0]).read_text();candidate=(HERE/'candidate'/FILES[0]).read_text()
callback=original[original.index('static void\non_property_changed ('):original.index('\n\nstatic void\non_up_client_new_ready (')]
assert callback in candidate
assert not any(call in candidate for call in ['up_device_refresh','g_timeout_add','g_source_set_ready_time','/sys/','/proc/','g_usleep'])
assert 'G_BUS_NAME_WATCHER_FLAGS_AUTO_START' in candidate
ui=ET.parse(HERE/'candidate/src/ui/top-panel.ui')
icon=ui.find(".//object[@id='external_power_icon']");revealer=ui.find(".//object[@id='external_power']")
assert icon is not None and icon.attrib['class']=='PhoshStatusIcon'
assert revealer.find("property[@name='child']").text=='external_power_icon'
assert revealer.find('child') is None # PhoshRevealer already owns its internal GtkRevealer.
assert revealer.find("property[@name='transition-duration']").text=='0'
assert icon.find("property[@name='visible']").text=='0'
asset=ET.parse(HERE/'candidate/src/phosh.gresources.xml').find(".//file[@alias='external-power-connected-symbolic.svg']")
assert asset is not None and asset.text=='../data/icons/external-power-connected-symbolic.svg'
svg=ET.parse(HERE/'candidate/data/icons/external-power-connected-symbolic.svg').getroot()
assert svg.attrib['viewBox']=='0 0 16 16'
(HERE/'external-power-marker.patch').write_text(patch,newline='\n')
result={'files':pins,'old_battery_callback_unchanged':True,'no_refresh_polling_sysfs':True,'owner_autostart_preserves_existing_activation':True,
        'UI_child_uses_existing_PhoshRevealer_property':True,'marker_animation_milliseconds':0,'Gtk_instantiation_or_complete_build_performed':False,
        'patch_sha256':sha(patch.encode()),'default_build_or_device_actions':False}
(HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'patch_sha256':result['patch_sha256'],'manager_sha256':pins[FILES[0]]['candidate_sha256']}))
