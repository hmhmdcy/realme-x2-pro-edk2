/** @file
  EUD (Embedded USB Debug) COM SerialPortLib for the realme X2 Pro (samurai).

  PRODUCER SIDE ONLY.

  SerialPortWrite() copies bytes into a fixed-address RAM ring buffer.  It does
  not touch the EUD hardware, it does not delay and it does not use gBS.  That
  makes the call safe from any DXE context, which is exactly what the earlier
  blocking implementation was not: with the debug level raised globally the
  inline MMIO and MicroSecondDelay() calls crashed the boot in
  DxeCore/CpuDxe with

      ReplaceTableEntry: splitting block entry with MMU disabled
      Synchronous Exception at ArmCpuDxe.dll+0x34B8

  A single consumer (Platform/Realme/sm8150/EudLogDxe) drains the ring into the
  EUD COM TX FIFO once a host PC has opened the port.  See EudLog.h for the
  ring layout and the memory region that holds it.

  SPDX-License-Identifier: BSD-2-Clause-Patent
**/

#include <Base.h>
#include <Library/BaseLib.h>
#include <Library/SerialPortLib.h>
#include <Library/SynchronizationLib.h>
#include "EudLog.h"

/**
  Make sure the shared ring header is usable.

  Called from every module that links this library (about 160 of them) through
  BaseDebugLibSerialPortConstructor() -> SerialPortInitialize().  Module
  constructors run one after another at TPL_APPLICATION during DXE dispatch, so
  a plain store sequence is enough.  Magic is written last so a half-built
  header is never accepted.
**/
STATIC
VOID
EudLogHeaderInit (
  VOID
  )
{
  EUD_LOG_HEADER  *Hdr;

  Hdr = (EUD_LOG_HEADER *)(UINTN)EUD_LOG_BASE;
  if (Hdr->Magic == EUD_LOG_MAGIC) {
    return;
  }

  Hdr->Size       = EUD_LOG_DATA_SIZE;
  Hdr->Head       = 0;
  Hdr->Tail       = 0;
  Hdr->Drops      = 0;
  Hdr->DropEvents = 0;
  Hdr->Version    = EUD_LOG_VERSION;
  MemoryFence ();
  Hdr->Magic      = EUD_LOG_MAGIC;
}

/**
  Initialize the serial device hardware.  There is no hardware to initialise:
  the EUD block is enabled later by the platform (BDS).
**/
RETURN_STATUS
EFIAPI
SerialPortInitialize (
  VOID
  )
{
  EudLogHeaderInit ();
  return RETURN_SUCCESS;
}

/**
  Append bytes to the shared log ring.

  A write that does not fit is dropped as a whole, so that DEBUG() lines stay
  readable and the loss is visible in the Drops counter.
**/
UINTN
EFIAPI
SerialPortWrite (
  IN UINT8  *Buffer,
  IN UINTN  NumberOfBytes
  )
{
  EUD_LOG_HEADER  *Hdr;
  UINT8           *Data;
  UINT32          Head;
  UINT32          Tail;
  UINT32          Count;
  UINT32          Index;

  if ((Buffer == NULL) || (NumberOfBytes == 0)) {
    return 0;
  }

  Hdr = (EUD_LOG_HEADER *)(UINTN)EUD_LOG_BASE;
  if (Hdr->Magic != EUD_LOG_MAGIC) {
    //
    // Only modules that run before any constructor could get here, and those
    // use FrameBufferSerialPortLib.  Re-check anyway so that a late writer can
    // never scribble into an uninitialised header.
    //
    EudLogHeaderInit ();
    if (Hdr->Magic != EUD_LOG_MAGIC) {
      return NumberOfBytes;
    }
  }

  if (NumberOfBytes > EUD_LOG_DATA_SIZE) {
    Hdr->Drops      += EUD_LOG_DATA_SIZE;
    Hdr->DropEvents += 1;
    return NumberOfBytes;
  }

  Count = (UINT32)NumberOfBytes;
  Data  = (UINT8 *)Hdr + EUD_LOG_DATA_OFFSET;

  //
  // Reserve space.  Producers can call this from different TPLs, so Head has
  // to be advanced with a compare-exchange.  A producer that is preempted
  // between the reservation and the copy can leave a partially written region
  // at the very end of the ring; the drainer is far behind whenever there is
  // real traffic, so this is accepted for a best-effort debug log.
  //
  do {
    Head = Hdr->Head;
    Tail = Hdr->Tail;
    if (((Head - Tail) + Count) > EUD_LOG_DATA_SIZE) {
      Hdr->Drops      += Count;
      Hdr->DropEvents += 1;
      return NumberOfBytes;
    }
  } while (InterlockedCompareExchange32 (&Hdr->Head, Head, Head + Count) != Head);

  for (Index = 0; Index < Count; Index++) {
    Data[(Head + Index) % EUD_LOG_DATA_SIZE] = Buffer[Index];
  }

  MemoryFence ();
  return NumberOfBytes;
}

UINTN
EFIAPI
SerialPortRead (
  OUT UINT8  *Buffer,
  IN  UINTN  NumberOfBytes
  )
{
  return 0;
}

BOOLEAN
EFIAPI
SerialPortPoll (
  VOID
  )
{
  return FALSE;
}

RETURN_STATUS
EFIAPI
SerialPortSetControl (
  IN UINT32  Control
  )
{
  return RETURN_UNSUPPORTED;
}

RETURN_STATUS
EFIAPI
SerialPortGetControl (
  OUT UINT32  *Control
  )
{
  return RETURN_UNSUPPORTED;
}

RETURN_STATUS
EFIAPI
SerialPortSetAttributes (
  IN OUT UINT64              *BaudRate,
  IN OUT UINT32              *ReceiveFifoDepth,
  IN OUT UINT32              *Timeout,
  IN OUT EFI_PARITY_TYPE     *Parity,
  IN OUT UINT8               *DataBits,
  IN OUT EFI_STOP_BITS_TYPE  *StopBits
  )
{
  return RETURN_UNSUPPORTED;
}
