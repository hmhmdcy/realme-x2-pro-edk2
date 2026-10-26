STATIC
VOID
SamuraiEudComPuts (
  IN CONST CHAR8  *Msg
  )
{
  UINTN  Index;
  UINTN  Len;
  UINTN  Offset;
  UINTN  Chunk;
  UINT32 Reg;

  if (Msg == NULL) {
    return;
  }

#ifdef SAMURAI_LINUX_KERNEL
  // A returned loader/BDS wait must not resume direct FIFO writes after EBS.
  if (mSamuraiEudOffHandoff.Attempted) {
    return;
  }
#endif

  MmioWrite32 (0x088E0000U + 0x0000U, 0x90U);
  Reg = MmioRead32 (0x088E0000U + 0x0000U);
  //
  // NOTE: the EUD register block replicates the low byte into all four lanes
  // (writing 1 reads back 0x01010101).  The TX_ID readback is therefore only
  // informational - hardware status bits may also be ORed in (0x90 -> 0x99).
  // Never gate the data writes on an exact match.
  //
  (VOID)Reg;

  Len = 0;
  while (Msg[Len] != 0) {
    Len++;
  }

  //
  // The EUD COM TX FIFO is tiny: sending a whole string in one go truncates it
  // after a few payload bytes (observed: [ID][LEN] + 7 data bytes).  Send the
  // string in small chunks, each with its own [TX_ID][TX_LEN][DATA...] frame,
  // with generous gaps so the FIFO can drain.
  //
  for (Offset = 0; Offset < Len; Offset += 6) {
    Chunk = ((Len - Offset) > 6) ? 6 : (Len - Offset);
    MmioWrite32 (0x088E0000U + 0x0000U, 0x90U);
    MmioWrite32 (0x088E0000U + 0x0004U, (UINT32)Chunk);
    for (Index = 0; Index < Chunk; Index++) {
      MmioWrite32 (0x088E0000U + 0x0008U, (UINT32)(UINT8)Msg[Offset + Index]);
      gBS->Stall (10000);
    }
    gBS->Stall (50000);
  }
}
