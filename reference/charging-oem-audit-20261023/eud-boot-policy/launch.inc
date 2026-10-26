#ifdef SAMURAI_ENABLE_EUD
    Status = SamuraiArmEudOffHandoff ();
    if (EFI_ERROR (Status)) {
      Print (L"[SAMURAI-EUD-OFF] not armed: %r; kernel launch refused\n", Status);
      goto SamuraiKernelBootDone;
    }
#endif
    Status = SamuraiArmPanelHandoff (&PanelHandoff);
    if (EFI_ERROR (Status)) {
      DEBUG ((DEBUG_WARN, "[SAMURAI] panel handoff unavailable: %r\n", Status));
    }
    EfiBootManagerBoot (&NewOption);
    SamuraiDisarmPanelHandoff (&PanelHandoff);
#ifdef SAMURAI_ENABLE_EUD
    SamuraiDisarmEudOffHandoff ();
SamuraiKernelBootDone:
#endif
;
