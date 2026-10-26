"""Actual paired firmware producer and EFI parser; no shared edits/device I/O."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-route-handoff-source-private-01')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
records=json.loads((PRIVATE/'sources-private.json').read_bytes())
for name,row in records.items():assert sha((PRIVATE/name).read_bytes())==row['sha256']
old=HERE.parent/'eud-boot-policy-r2/PlatformBm.c.candidate';original=old.read_text();assert sha(old.read_bytes())=='c1ce63b3cc8df1c44b5351f53d15294505df919915fa8773636054305617cee8'
def replace(text,a,b):
    assert text.count(a)==1,(a,text.count(a));return text.replace(a,b)
source=replace(original,'#include <Library/BaseMemoryLib.h>','#include <Library/BaseMemoryLib.h>\n#include <Library/BaseLib.h>\n#include "samurai-eud-handoff-wire.h"')
source=replace(source,'  EFI_STATUS  CloseStatus;\n} SAMURAI_EUD_OFF_HANDOFF;',
    '  EFI_STATUS  CloseStatus;\n  struct samurai_eud_handoff *Record;\n  BOOLEAN RecordInstalled;\n} SAMURAI_EUD_OFF_HANDOFF;')
needle='STATIC SAMURAI_EUD_OFF_HANDOFF  mSamuraiEudOffHandoff;'
source=replace(source,needle,needle+'\n\n'+(HERE/'firmware-record-functions.inc').read_text())
source=replace(source,'  // Current samurai SerialPortLib only appends RAM.',
    '  SamuraiEudPublishRecord (Handoff);\n\n  // Current samurai SerialPortLib only appends RAM.')
needle='''  Status = gBS->CreateEventEx (
                  EVT_NOTIFY_SIGNAL,
                  TPL_CALLBACK,
                  SamuraiEudBeforeExitBootServices,'''
source=replace(source,needle,'''  Status = SamuraiEudPrepareRecord (Handoff);
  if (EFI_ERROR (Status)) {
    Handoff->Status = Status;
    return Status;
  }

'''+needle)
source=replace(source,'    Handoff->Event  = NULL;\n    Handoff->Status = Status;',
    '    Handoff->Event  = NULL;\n    Handoff->Status = Status;\n    SamuraiEudReleaseRecord (Handoff, TRUE);')
source=replace(source,'  Handoff->Cancelled = TRUE;', '  Handoff->Cancelled = TRUE;\n  SamuraiEudInvalidateRecord (Handoff);')
source=replace(source,'  // Never automatically re-enable EUD on a failed MapKey or loader return.',
    '  SamuraiEudReleaseRecord (Handoff, Handoff->CloseStatus == EFI_SUCCESS);\n\n  // Never automatically re-enable EUD on a failed MapKey or loader return.')
efi_original=(PRIVATE/'efi.c').read_text();efi=replace(efi_original,'#include <linux/efi.h>','#include <linux/efi.h>\n#include <linux/firmware/samurai-eud-handoff.h>')
needle='\t\tif (!match_config_table(guid, table, common_tables) && arch_tables)'
efi=replace(efi,needle,'\t\tsamurai_eud_handoff_config(guid, table);\n\n'+needle)
for name,value in [('PlatformBm.c.candidate',source),('efi.c',efi)]:
    path=HERE/name
    if path.exists():assert path.read_text()==value,name
    else:path.write_text(value)
patch=''.join(difflib.unified_diff(original.splitlines(True),source.splitlines(True),fromfile='a/PlatformBm.c',tofile='b/PlatformBm.c'))
patch+=''.join(difflib.unified_diff(efi_original.splitlines(True),efi.splitlines(True),fromfile='a/drivers/firmware/efi/efi.c',tofile='b/drivers/firmware/efi/efi.c'))
(HERE/'paired-handoff.patch').write_text(patch)
result=dict(prepared=True,source_records=records,original_BDS_sha256=sha(old.read_bytes()),
    files={name:sha((HERE/name).read_bytes()) for name in ['PlatformBm.c.candidate','efi.c','samurai-eud-handoff-wire.h','firmware-record-functions.inc','samurai-eud-handoff.h','samurai-eud-handoff.c','Kconfig.fragment','Makefile.fragment']},
    reserved_page_bytes=4096,wire_record_bytes=64,phone_accessed=False,route_capability_created=False)
(HERE/'source-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(prepared=True,structured_EFI_evidence_only=True,route_capability_created=False)))
