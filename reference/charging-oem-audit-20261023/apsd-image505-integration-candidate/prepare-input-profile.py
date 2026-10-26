"""Activate the backend only in the explicit same-Image EUD-off profile."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
composition=json.loads((HERE/'composition.json').read_bytes());row=composition['external_input_module_sources']['samurai-usb-input.c'];old=ROOT/row['origin'];assert sha(old)==row['sha256']
source=old.read_text();before='static bool apsd_backend;';after='static bool apsd_backend = IS_ENABLED(CONFIG_USB_DWC3_SAMURAI_APSD_EUD_OFF_CLIENT);'
assert source.count(before)==1;changed=source.replace(before,after);assert changed.replace(after,before)==source
target=HERE/'samurai-usb-input.c.candidate';assert not target.exists();target.write_text(changed)
kernel=json.loads((HERE/'kernel-build-r2-result.json').read_bytes());assert kernel['passed'] and kernel['build']['required_configs']['USB_DWC3_SAMURAI_APSD_EUD_OFF_CLIENT']=='y'
result=dict(prepared=True,original_source_sha256=sha(old),candidate=dict(origin=target.relative_to(ROOT).as_posix(),sha256=sha(target),bytes=target.stat().st_size),
 only_default_initializer_changed=True,all_function_bodies_and_budget_math_exact=True,
 default_enabled_only_with_explicit_same_Image_profile=True,explicit_module_parameter_optout_retained=True,
 original_service_unchanged=True,register_board_and_all_PD_route_PHY_first_off_checks_retained=True,installed=False)
with (HERE/'input-profile-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(prepared=True,function_bodies_changed=0,old_service_retained=True)))
