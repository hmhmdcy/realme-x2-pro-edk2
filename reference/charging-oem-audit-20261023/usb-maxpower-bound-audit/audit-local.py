"""Read cached exact Image-associated source/startup records only."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1];ROOT=REF.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SRC=REF/'charging-session-20261023/dwc-r2-independent-review'
manifest=json.loads((SRC/'callback-source-manifest.json').read_text())
inputs=[]
for name in ['configfs.c','composite.c']:
 path=SRC/('source--drivers--usb--gadget--'+name)
 entry=next(e for e in manifest if e['path']=='drivers/usb/gadget/'+name)
 assert sha(path)==entry['sha256'] and entry['byte_equal_to_image_source_commit']
 inputs.append(dict(path=str(path),sha256=sha(path),byte_equal_to_image_source_commit=True))
cached=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-hotplug-r2/usb-services-before-private.json')
services=json.loads(cached.read_text());rollback=REF/'charging-management-20261023/usb-startup-rollback-result.json'
restored=json.loads(rollback.read_text())
rows=[]
for target in ['/usr/local/sbin/samurai-usb','/usr/sbin/samurai-usb']:
 entry=services[target];text=entry['text']
 h=hashlib.sha256(text.encode()).hexdigest();assert h==entry['sha256']
 assert next(x['sha256'] for x in restored['restored'] if x['path']==target)==h
 matches=[dict(line=i,text=line) for i,line in enumerate(text.splitlines(),1) if 'configs/c.1/MaxPower' in line]
 assert len(matches)==1 and 'echo 100 >' in matches[0]['text']
 guards=[dict(line=i,text=line) for i,line in enumerate(text.splitlines(),1) if 'if [ ! -d "$g" ]' in line]
 rows.append(dict(target=target,sha256=h,cached=str(cached),restored_receipt_sha256=sha(rollback),MaxPower=matches,creation_guard=guards))
repo=[]
for name in ['linux-port/scripts/samurai-usb.sh','linux-port/packages/samurai-platform/usr_sbin_samurai-usb']:
 path=ROOT/name;text=path.read_text()
 repo.append(dict(path=str(path),sha256=sha(path),matches=[dict(line=i,text=line) for i,line in enumerate(text.splitlines(),1) if 'configs/c.1/MaxPower' in line],
 same_as_cached_targets=[e['target'] for e in rows if e['sha256']==sha(path)]))
r=dict(scope='exact local source audit, no live device claim',sources=inputs,startups=rows,repository_sources=repo,
 findings=dict(bound_store_allowed=True,store_function='gadget_config_desc_MaxPower_store',store_lines=[532,545],
 store_operations=['kstrtou16','range DIV_ROUND_UP(val,8)<=0xff','cfg->c.MaxPower=val','return len'],
 store_calls_UDC_reset=False,store_calls_vbus_draw=False,store_checks_bound=False,
 immediate_native_budget_update_by_store_itself=False,
 only_future_descriptor_cache=False,guarantees_native100_until_physical_reconnect=False,
 counterexample='bound/configured 100 -> write MaxPower500 -> USB suspend -> composite_resume reads mutated cdev->config->MaxPower and calls vbus_draw500 without any physical reconnect',
 resume_lines=[2609,2652],resume_MaxPower_read_line=2632,resume_vbus_draw_lines=[2645,2649],
 set_config_MaxPower_lines=[1038,1059],descriptor_encode_lines=[529,548],
 startup_creation_only=True,startup_echo_change_alone_migrates_existing_initramfs_gadget=False),
 current_startup_identity_boundary='Cached latest restored startup pins only; root must use its own current device identity before any mutation. This audit did not re-read phone.',
 proposed_minimum='Persist only reviewed one-line creator change without executing startup; write volatile MaxPower only in a separately proven real physical-off window, then validate fresh host descriptor/configuration/native callback. No UDC unbind is required by this store, but online write cannot promise delayed native budget.',
 phone_accessed=False,SSH_invoked=False,USB_invoked=False,SDK_invoked=False,Git_invoked=False,storage_helper_called=False,build_or_test_run=False,existing_files_modified=False)
(HERE/'result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(startups=rows,repository_sources=repo),indent=2))
