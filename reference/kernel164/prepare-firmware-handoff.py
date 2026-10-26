from pathlib import Path
import difflib, hashlib, json, subprocess

repo = Path('/home/cy122/edk2-samurai/repo')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel164')
out = Path('/mnt/e/edk2-samurai-out/kernel164')
out.mkdir(mode=0o700, exist_ok=True)
names = ['Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c',
         'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBootManagerLib.inf']
before = {name: (repo / name).read_text() for name in names}
for name in names:
    assert (repo / name).read_bytes() == subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=repo)
assert not (out / 'source-before-private.json').exists()
(out / 'source-before-private.json').write_text(json.dumps(before, indent=2))
(out / 'other-diff-before-private.patch').write_bytes(subprocess.check_output(
    ['git', 'diff', '--binary', '--', '.'] + [':(exclude)' + name for name in names], cwd=repo))
c = before[names[0]]
c = c.replace('#include <Library/BootLogoLib.h>', '#include <Library/BaseMemoryLib.h>\n#include <Library/BootLogoLib.h>', 1)
c = c.replace('#include <Protocol/SimpleFileSystem.h>', '#include <Protocol/SimpleFileSystem.h>\n#include <Protocol/EFITlmm.h>', 1)
needle = '#ifdef SAMURAI_LINUX_KERNEL\n'
assert needle in c
helpers = '''
#define SAMURAI_PANEL_RESET_CONFIG \\
  EFI_GPIO_CFG (6, 0, GPIO_OUTPUT, GPIO_NO_PULL, GPIO_8MA)

typedef struct {
  EFI_QCOM_TLMM_PROTOCOL  *Tlmm;
  EFI_EVENT              Event;
  BOOLEAN                Attempted;
  EFI_STATUS             Status;
} SAMURAI_PANEL_HANDOFF;

STATIC
VOID
EFIAPI
SamuraiPanelBeforeExitBootServices (
  IN EFI_EVENT  Event,
  IN VOID       *Context
  )
{
  SAMURAI_PANEL_HANDOFF  *Handoff;

  (VOID)Event;
  Handoff = Context;
  if ((Handoff == NULL) || Handoff->Attempted) {
    return;
  }

  Handoff->Attempted = TRUE;
  if ((Handoff->Tlmm == NULL) || (Handoff->Tlmm->ConfigGpio == NULL) ||
      (Handoff->Tlmm->GpioOut == NULL)) {
    Handoff->Status = EFI_UNSUPPORTED;
    return;
  }

  // This group runs while firmware interfaces and timers are still available.
  Handoff->Status = Handoff->Tlmm->ConfigGpio (
                                    SAMURAI_PANEL_RESET_CONFIG,
                                    TLMM_GPIO_ENABLE
                                    );
  if (!EFI_ERROR (Handoff->Status)) {
    Handoff->Status = Handoff->Tlmm->GpioOut (
                                      SAMURAI_PANEL_RESET_CONFIG,
                                      GPIO_LOW_VALUE
                                      );
  }
  DEBUG ((DEBUG_INFO, "[SAMURAI] panel reset before Linux ExitBootServices: %r\\n",
          Handoff->Status));
}

STATIC
EFI_STATUS
SamuraiArmPanelHandoff (
  OUT SAMURAI_PANEL_HANDOFF  *Handoff
  )
{
  EFI_STATUS  Status;

  ZeroMem (Handoff, sizeof (*Handoff));
  Handoff->Status = EFI_NOT_READY;
  Status = gBS->LocateProtocol (
                  &gQcomTlmmProtocolGuid,
                  NULL,
                  (VOID **)&Handoff->Tlmm
                  );
  if (EFI_ERROR (Status)) {
    return Status;
  }
  if ((Handoff->Tlmm->Revision < QCOM_TLMM_PROTOCOL_REVISION) ||
      (Handoff->Tlmm->ConfigGpio == NULL) || (Handoff->Tlmm->GpioOut == NULL)) {
    return EFI_UNSUPPORTED;
  }

  Status = gBS->CreateEventEx (
                  EVT_NOTIFY_SIGNAL,
                  TPL_CALLBACK,
                  SamuraiPanelBeforeExitBootServices,
                  Handoff,
                  &gEfiEventBeforeExitBootServicesGuid,
                  &Handoff->Event
                  );
  if (EFI_ERROR (Status)) {
    Handoff->Event = NULL;
  }
  return Status;
}

STATIC
VOID
SamuraiDisarmPanelHandoff (
  IN OUT SAMURAI_PANEL_HANDOFF  *Handoff
  )
{
  if (Handoff->Event != NULL) {
    if (gBS != NULL) {
      gBS->CloseEvent (Handoff->Event);
    }
    Handoff->Event = NULL;
  }
}

'''
c = c.replace(needle, needle + helpers, 1)
needle = '  EFI_BOOT_MANAGER_LOAD_OPTION     NewOption;\n'
assert c.count(needle) == 1
c = c.replace(needle, needle + '  SAMURAI_PANEL_HANDOFF            PanelHandoff;\n', 1)
needle = '    EfiBootManagerBoot (&NewOption);\n'
assert c.count(needle) == 1
c = c.replace(needle, '''    Status = SamuraiArmPanelHandoff (&PanelHandoff);
    if (EFI_ERROR (Status)) {
      DEBUG ((DEBUG_WARN, "[SAMURAI] panel handoff unavailable: %r\\n", Status));
    }
    EfiBootManagerBoot (&NewOption);
    SamuraiDisarmPanelHandoff (&PanelHandoff);
''', 1)
inf = before[names[1]]
inf = inf.replace('  SimpleInit.dec\n', '  SimpleInit.dec\n  Silicon/Qualcomm/QcomPkg/QcomPkg.dec\n', 1)
inf = inf.replace('  gEfiEndOfDxeEventGroupGuid\n', '  gEfiEndOfDxeEventGroupGuid\n  gEfiEventBeforeExitBootServicesGuid\n', 1)
inf = inf.replace('  gPlatformBootManagerProtocolGuid\n', '  gPlatformBootManagerProtocolGuid\n  gQcomTlmmProtocolGuid\n', 1)
after = dict(zip(names, [c, inf]))
for name, text in after.items():
    (repo / name).write_text(text)
patch = '''Subject: [PATCH] samurai: hold panel reset before Linux leaves boot services

The Linux GPIO controller may probe after SMMU initialization, leaving a
visible firmware-to-native display transition. Arm a one-shot notification
only around the validated mainline Linux boot option. Use the Qualcomm
TLMM protocol to assert this board's GPIO6 reset in the BeforeExitBootServices
group, while firmware interfaces are still available. Keep the panel held
until the native Linux panel driver runs its normal initialization.
If image loading returns without exiting boot services, close the event
without touching the GPIO. Protocol or event errors preserve normal boot.

---

'''
for name in names:
    patch += 'diff --git a/' + name + ' b/' + name + '\n'
    patch += ''.join(difflib.unified_diff(before[name].splitlines(True), after[name].splitlines(True), fromfile='a/' + name, tofile='b/' + name))
(ref / 'before-exit-panel-reset.patch').write_text(patch)
report = dict(stage=164, kernel_build_kept=163, modified_files=names,
              before_sha256={name: hashlib.sha256(text.encode()).hexdigest() for name, text in before.items()},
              after_sha256={name: hashlib.sha256(text.encode()).hexdigest() for name, text in after.items()},
              uses_before_exit_group_not_post_shutdown_protocol_calls=True,
              kernel_boot_option_only=True, callback_once_per_boot_attempt=True,
              gpio6_reset_only=True, no_panel_power_rail_changes=True,
              normal_image_and_cmdline_loading_preserved=True, deployed=False,
              physical_bug_fixed=False)
(ref / 'source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
