#ifdef SAMURAI_ENABLE_EUD
// Boot-only policy: retire the firmware-owned EUD before Linux can bind USB.
// This is not a runtime role/PHY API. The BDS path has already enabled and
// polled this exact 32-bit register while firmware services are available.
#define SAMURAI_EUD_CSR_ADDRESS  0x088E1014U

typedef struct {
  EFI_EVENT   Event;
  BOOLEAN     Attempted;
  BOOLEAN     Cancelled;
  BOOLEAN     WriteAttempted;
  UINT32      ArmCsr;
  UINT32      BeforeCsr;
  UINT32      AfterCsr;
  EFI_STATUS  Status;
  EFI_STATUS  CloseStatus;
} SAMURAI_EUD_OFF_HANDOFF;

// Static storage: even a failed CloseEvent cannot leave a stack context alive.
STATIC SAMURAI_EUD_OFF_HANDOFF  mSamuraiEudOffHandoff;

STATIC
BOOLEAN
SamuraiEudCsrKnown (
  IN UINT32  Value
  )
{
  // Match full words only; 0x01010101 was read twice on this board.
  return (Value == 0U) || (Value == 1U) || (Value == 0x01010101U);
}

STATIC
VOID
EFIAPI
SamuraiEudBeforeExitBootServices (
  IN EFI_EVENT  Event,
  IN VOID       *Context
  )
{
  SAMURAI_EUD_OFF_HANDOFF  *Handoff;

  (VOID)Event;
  Handoff = Context;
  if ((Handoff == NULL) || Handoff->Cancelled || Handoff->Attempted) {
    return;
  }

  // BeforeEBS also runs on a bad MapKey. Never repeat the write on EFI retry.
  Handoff->Attempted = TRUE;
  Handoff->BeforeCsr = MmioRead32 (SAMURAI_EUD_CSR_ADDRESS);
  Handoff->AfterCsr  = Handoff->BeforeCsr;
  if (!SamuraiEudCsrKnown (Handoff->BeforeCsr)) {
    Handoff->Status = EFI_COMPROMISED_DATA;
  } else {
    if (Handoff->BeforeCsr != 0U) {
      Handoff->WriteAttempted = TRUE;
      MmioWrite32 (SAMURAI_EUD_CSR_ADDRESS, 0U);
    }

    Handoff->AfterCsr = MmioRead32 (SAMURAI_EUD_CSR_ADDRESS);
    Handoff->Status   = (Handoff->AfterCsr == 0U) ? EFI_SUCCESS : EFI_DEVICE_ERROR;
  }

  // Current samurai SerialPortLib only appends RAM. This is an observation,
  // not a veto: a VOID BeforeEBS notification cannot stop EFI from booting.
  DEBUG ((DEBUG_ERROR,
          "[SAMURAI-EUD-OFF] attempted=%u write=%u arm=%08x before=%08x after=%08x status=%r\n",
          Handoff->Attempted, Handoff->WriteAttempted, Handoff->ArmCsr,
          Handoff->BeforeCsr, Handoff->AfterCsr, Handoff->Status));
}

STATIC
EFI_STATUS
SamuraiArmEudOffHandoff (
  VOID
  )
{
  SAMURAI_EUD_OFF_HANDOFF  *Handoff;
  EFI_STATUS              Status;

  Handoff = &mSamuraiEudOffHandoff;
  if ((Handoff->Event != NULL) || Handoff->Attempted) {
    return EFI_ALREADY_STARTED;
  }

  ZeroMem (Handoff, sizeof (*Handoff));
  Handoff->Status      = EFI_NOT_READY;
  Handoff->CloseStatus = EFI_NOT_READY;
  if ((gBS == NULL) || (gBS->CreateEventEx == NULL)) {
    Handoff->Status = EFI_UNSUPPORTED;
    return Handoff->Status;
  }

  Handoff->ArmCsr = MmioRead32 (SAMURAI_EUD_CSR_ADDRESS);
  if (!SamuraiEudCsrKnown (Handoff->ArmCsr)) {
    Handoff->Status = EFI_COMPROMISED_DATA;
    return Handoff->Status;
  }

  Status = gBS->CreateEventEx (
                  EVT_NOTIFY_SIGNAL,
                  TPL_CALLBACK,
                  SamuraiEudBeforeExitBootServices,
                  Handoff,
                  &gEfiEventBeforeExitBootServicesGuid,
                  &Handoff->Event
                  );
  if (EFI_ERROR (Status)) {
    Handoff->Event  = NULL;
    Handoff->Status = Status;
  }

  return Status;
}

STATIC
VOID
SamuraiDisarmEudOffHandoff (
  VOID
  )
{
  SAMURAI_EUD_OFF_HANDOFF  *Handoff;

  Handoff = &mSamuraiEudOffHandoff;
  // If the kernel loader returns without EBS, withdraw this policy before
  // BDS tries anything else. A failed close leaves an inert static context.
  Handoff->Cancelled = TRUE;
  if (Handoff->Event != NULL) {
    if ((gBS != NULL) && (gBS->CloseEvent != NULL)) {
      Handoff->CloseStatus = gBS->CloseEvent (Handoff->Event);
      if (EFI_ERROR (Handoff->CloseStatus)) {
        return;
      }
    }

    Handoff->Event = NULL;
  }

  // Never automatically re-enable EUD on a failed MapKey or loader return.
}
#endif // SAMURAI_ENABLE_EUD

