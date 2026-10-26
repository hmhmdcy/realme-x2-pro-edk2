/* Actual static BDS context owns the reserved page and its publication. */
#define SAMURAI_EUD_GUID_INITIALIZER(a, b, c, d0, d1, d2, d3, d4, d5, d6, d7) \
  { a, b, c, { d0, d1, d2, d3, d4, d5, d6, d7 } }
#define SAMURAI_EUD_GUID_EXPAND(...) SAMURAI_EUD_GUID_INITIALIZER (__VA_ARGS__)
STATIC EFI_GUID mSamuraiEudHandoffGuid = SAMURAI_EUD_GUID_EXPAND (SAMURAI_EUD_GUID_WORDS);

STATIC
VOID
SamuraiEudInvalidateRecord (IN OUT SAMURAI_EUD_OFF_HANDOFF *Handoff)
{
  if (Handoff->Record != NULL) {
    Handoff->Record->commit = 0U;
    MemoryFence ();
  }
}

STATIC
VOID
SamuraiEudReleaseRecord (IN OUT SAMURAI_EUD_OFF_HANDOFF *Handoff, IN BOOLEAN CanFree)
{
  EFI_STATUS Status;

  SamuraiEudInvalidateRecord (Handoff);
  if (!CanFree || (Handoff->Record == NULL) || (gBS == NULL) ||
      (gBS->InstallConfigurationTable == NULL)) {
    return;
  }
  if (Handoff->RecordInstalled) {
    Status = gBS->InstallConfigurationTable (&mSamuraiEudHandoffGuid, NULL);
    if (EFI_ERROR (Status)) {
      return; // Retain an invalid reserved page, never leave a dangling table.
    }
    Handoff->RecordInstalled = FALSE;
  }
  FreePages (Handoff->Record, 1);
  Handoff->Record = NULL;
}

STATIC
EFI_STATUS
SamuraiEudPrepareRecord (IN OUT SAMURAI_EUD_OFF_HANDOFF *Handoff)
{
  EFI_STATUS Status;
  VOID *Existing;

  if ((gST == NULL) || (gBS == NULL) || (gBS->InstallConfigurationTable == NULL)) {
    return EFI_UNSUPPORTED;
  }
  Status = EfiGetSystemConfigurationTable (&mSamuraiEudHandoffGuid, &Existing);
  if (Status != EFI_NOT_FOUND) {
    return EFI_ERROR (Status) ? Status : EFI_ALREADY_STARTED;
  }
  Handoff->Record = AllocateReservedPages (1);
  if (Handoff->Record == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }
  ZeroMem (Handoff->Record, 4096);
  Status = gBS->InstallConfigurationTable (&mSamuraiEudHandoffGuid, Handoff->Record);
  if (EFI_ERROR (Status)) {
    FreePages (Handoff->Record, 1);
    Handoff->Record = NULL;
    return Status;
  }
  Handoff->RecordInstalled = TRUE;
  return EFI_SUCCESS;
}

STATIC
VOID
SamuraiEudPublishRecord (IN OUT SAMURAI_EUD_OFF_HANDOFF *Handoff)
{
  struct samurai_eud_handoff *Record = Handoff->Record;

  if ((Record == NULL) || !Handoff->RecordInstalled || Handoff->Cancelled ||
      !Handoff->Attempted || EFI_ERROR (Handoff->Status) || Handoff->AfterCsr != 0U) {
    SamuraiEudInvalidateRecord (Handoff);
    return;
  }
  ZeroMem (Record, sizeof (*Record));
  Record->version = SAMURAI_EUD_HANDOFF_VERSION;
  Record->bytes = sizeof (*Record);
  Record->flags = SAMURAI_EUD_FLAG_ATTEMPTED | SAMURAI_EUD_FLAG_DIRECT_FIFO_RETIRED;
  if (Handoff->WriteAttempted) {
    Record->flags |= SAMURAI_EUD_FLAG_WRITE_ATTEMPTED;
  }
  Record->arm_csr = Handoff->ArmCsr;
  Record->before_csr = Handoff->BeforeCsr;
  Record->after_csr = Handoff->AfterCsr;
  Record->status = Handoff->Status;
  Record->csr_address = SAMURAI_EUD_HANDOFF_CSR;
  Record->table_address = (UINTN)Record;
  Record->checksum = samurai_eud_handoff_crc (Record);
  MemoryFence ();
  Record->commit = SAMURAI_EUD_HANDOFF_MAGIC;
  MemoryFence ();
}
