/** @file
  Replay the samurai EUD log ring buffer into the EUD COM TX FIFO.

  The ring is written by every module that links EudSerialPortLib; its layout
  and its fixed physical address are described in
  Platform/Realme/sm8150/Library/EudSerialPortLib/EudLog.h.  Because the address
  is fixed this driver needs no shared library state and is the single
  consumer.

  Why the replay loops: the host PC cannot open the EUD COM port until it has
  run eudtool com-up, and there is no dependable register that tells the
  firmware when the host is listening, so the drainer does not guess.  It
  rewinds the consumer tail to the oldest byte still in the ring and sends the
  whole ring again, pausing between passes, so a host that attaches at any point
  during the replay window still receives a complete copy.

  Each pass is delimited by marker lines that are sent directly, not from the
  ring, so pass boundaries stay readable even when the ring content ends in the
  middle of a line.  The end marker carries the duration and byte count, which
  is how the real drain rate is measured on hardware.

  Pacing: the fixed 200 us per byte and 2 ms per frame timing that is proven on
  this hardware.  Polling the TX status bit was tried on 2026-10-07 and made
  things worse: INT_STATUS_1 bit 1 does not behave like a usable FIFO room
  indicator here (it looks like an interrupt status bit that stays asserted), so
  the drainer wrote bursts as fast as it could and the TX FIFO truncated them -
  the capture came back with bytes missing in the middle of strings.  Do not
  switch back to status polling on this unit without proving the semantics first.

  SPDX-License-Identifier: BSD-2-Clause-Patent
**/

#include <Uefi.h>
#include <Library/BaseLib.h>
#include <Library/DebugLib.h>
#include <Library/IoLib.h>
#include <Library/PrintLib.h>
#include <Library/TimerLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/UefiDriverEntryPoint.h>
#include "../Library/EudSerialPortLib/EudLog.h"

//
// EUD register map, from the stock kernel driver drivers/soc/qcom/eud.c
//
#define EUD_BASE              0x088E0000U
#define EUD_REG_CSR_EUD_EN    0x1014U
#define EUD_REG_COM_TX_ID     0x0000U
#define EUD_REG_COM_TX_LEN    0x0004U
#define EUD_REG_COM_TX_DAT    0x0008U

#define EUD_COM_UART_ID       0x90U

//
// The TX FIFO truncates a longer burst, so keep the 6-byte chunk and the
// pacing that are proven on this hardware.
//
#define EUD_COM_CHUNK         6U
#define EUD_COM_BYTE_DELAY    200U
#define EUD_COM_FRAME_DELAY   2000U

#define EUD_DRAIN_TICK_MS     10U

//
// Hard cap on how long one timer tick may spend pushing bytes.  Two 6-byte
// frames fit in this budget, which is the rate the previous version already
// used on hardware.
//
#define EUD_DRAIN_BUDGET_US   6000U

#define EUD_REPLAY_WINDOW_MS  600000U
#define EUD_REPLAY_PAUSE_MS   2000U

STATIC EFI_EVENT  mDrainEvent       = NULL;
STATIC UINT64     mPerfFreq         = 0;
STATIC BOOLEAN    mEudSeen          = FALSE;
STATIC BOOLEAN    mWindowClosed     = FALSE;
STATIC BOOLEAN    mOverflowReported = FALSE;
STATIC BOOLEAN    mPassActive       = FALSE;
STATIC UINT32     mEudUptimeMs      = 0;
STATIC UINT32     mPauseMs          = 0;
STATIC UINT32     mPassCount        = 0;
STATIC UINT32     mPassBytes        = 0;
STATIC UINT32     mPassStartMs      = 0;

STATIC
VOID
EudLogPrint (
  IN CONST CHAR16  *Text
  )
{
  if ((gST == NULL) || (gST->ConOut == NULL)) {
	return;
  }

  gST->ConOut->OutputString (gST->ConOut, (CHAR16 *)Text);
}

//
// Send a NUL terminated string that is not part of the ring (marker lines).
//
STATIC
VOID
EudSendString (
  IN CONST CHAR8  *Str
  )
{
  UINT8  *Data;
  UINTN  Len;
  UINTN  Offset;
  UINTN  Chunk;
  UINTN  Index;

  Data = (UINT8 *)(UINTN)Str;
  Len  = AsciiStrLen (Str);

  for (Offset = 0; Offset < Len; Offset += EUD_COM_CHUNK) {
	Chunk = Len - Offset;
	if (Chunk > EUD_COM_CHUNK) {
	  Chunk = EUD_COM_CHUNK;
	}

	MmioWrite32 (EUD_BASE + EUD_REG_COM_TX_ID, EUD_COM_UART_ID);
	MmioWrite32 (EUD_BASE + EUD_REG_COM_TX_LEN, (UINT32)Chunk);
	for (Index = 0; Index < Chunk; Index++) {
	  MmioWrite32 (EUD_BASE + EUD_REG_COM_TX_DAT, (UINT32)Data[Offset + Index]);
	  MicroSecondDelay (EUD_COM_BYTE_DELAY);
	}

	MicroSecondDelay (EUD_COM_FRAME_DELAY);
  }
}

STATIC
VOID
WriteFrame (
  IN UINT32  Offset,
  IN UINT32  Count
  )
{
  EUD_LOG_HEADER  *Hdr;
  UINT8           *Data;
  UINT32          Index;

  Hdr  = (EUD_LOG_HEADER *)(UINTN)EUD_LOG_BASE;
  Data = (UINT8 *)Hdr + EUD_LOG_DATA_OFFSET;

  MmioWrite32 (EUD_BASE + EUD_REG_COM_TX_ID, EUD_COM_UART_ID);
  MmioWrite32 (EUD_BASE + EUD_REG_COM_TX_LEN, Count);
  for (Index = 0; Index < Count; Index++) {
	MmioWrite32 (EUD_BASE + EUD_REG_COM_TX_DAT, (UINT32)Data[(Offset + Index) % EUD_LOG_DATA_SIZE]);
	MicroSecondDelay (EUD_COM_BYTE_DELAY);
  }

  MicroSecondDelay (EUD_COM_FRAME_DELAY);
}

//
// Oldest byte that is still inside the ring.  Rewinding the consumer tail to
// it makes the next pass resend everything that has not been overwritten yet.
//
STATIC
UINT32
RingOldest (
  IN UINT32  Head
  )
{
  return Head - MIN (Head, EUD_LOG_DATA_SIZE);
}

VOID
EFIAPI
EudLogDrainNotify (
  IN EFI_EVENT  Event,
  IN VOID       *Context
  )
{
  EUD_LOG_HEADER  *Hdr;
  CHAR8           Line[96];
  UINT64          Start;
  UINT64          BudgetTicks;
  UINT32          Head;
  UINT32          Tail;
  UINT32          Avail;
  UINT32          Chunk;

  //
  // Nothing to do until BDS has enabled EUD.
  //
  if ((MmioRead32 (EUD_BASE + EUD_REG_CSR_EUD_EN) & 0xFFU) != 1U) {
	mEudSeen     = FALSE;
	mPassActive  = FALSE;
	mEudUptimeMs = 0;
	mPauseMs     = 0;
	return;
  }

  Hdr = (EUD_LOG_HEADER *)(UINTN)EUD_LOG_BASE;

  if (!mEudSeen) {
	mEudSeen     = TRUE;
	mEudUptimeMs = 0;
  } else {
	mEudUptimeMs += EUD_DRAIN_TICK_MS;
  }

  if (mPauseMs > 0) {
	mPauseMs = (mPauseMs > EUD_DRAIN_TICK_MS) ? (mPauseMs - EUD_DRAIN_TICK_MS) : 0;
	if (mPauseMs > 0) {
	  return;
	}
  }

  if (!mPassActive) {
	mPassActive  = TRUE;
	mPassBytes   = 0;
	mPassStartMs = mEudUptimeMs;
	mPassCount++;
	Hdr->Tail    = RingOldest (Hdr->Head);

	AsciiSPrint (Line, sizeof (Line), "\r\n=== EUD ring pass %d ===\r\n", (INT32)mPassCount);
	EudSendString (Line);
  }

  //
  // Push for at most the tick budget, so a full ring cannot stall the menu.
  //
  BudgetTicks = (mPerfFreq * EUD_DRAIN_BUDGET_US) / 1000000ULL;
  Start       = GetPerformanceCounter ();

  do {
	Head  = Hdr->Head;
	Tail  = Hdr->Tail;
	Avail = Head - Tail;
	if (Avail == 0) {
	  break;
	}

	Chunk = (Avail > EUD_COM_CHUNK) ? EUD_COM_CHUNK : Avail;
	WriteFrame (Tail, Chunk);
	mPassBytes += Chunk;
	MemoryFence ();
	Hdr->Tail = Tail + Chunk;
  } while ((GetPerformanceCounter () - Start) < BudgetTicks);

  Head = Hdr->Head;
  if (Hdr->Tail == Head) {
	mPassActive = FALSE;

	AsciiSPrint (
	  Line,
	  sizeof (Line),
	  "--- pass %d: %d byte(s) in %d ms ---\r\n",
	  (INT32)mPassCount,
	  (INT32)mPassBytes,
	  (INT32)(mEudUptimeMs - mPassStartMs)
	  );
	EudSendString (Line);

	if (mEudUptimeMs < EUD_REPLAY_WINDOW_MS) {
	  mPauseMs = EUD_REPLAY_PAUSE_MS;
	} else if (!mWindowClosed) {
	  mWindowClosed = TRUE;
	  EudSendString ("--- replay window closed, pass-through only ---\r\n");
	}
  }

  if ((!mOverflowReported) && (Hdr->Drops != 0)) {
	mOverflowReported = TRUE;
	EudLogPrint (L"[EUD-LOG] ring overflowed, replay is lossy\r\n");
	DEBUG ((
	  DEBUG_ERROR,
	  "[EUD-LOG] ring overflowed: %u byte(s) in %u event(s) dropped\r\n",
	  Hdr->Drops,
	  Hdr->DropEvents
	  ));
  }
}

EFI_STATUS
EFIAPI
EudLogDxeEntry (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  EFI_STATUS  Status;

  mPerfFreq = GetPerformanceCounterProperties (NULL, NULL);
  if (mPerfFreq == 0) {
	mPerfFreq = 1000000U;
  }

  Status = gBS->CreateEvent (
				  EVT_TIMER | EVT_NOTIFY_SIGNAL,
				  TPL_CALLBACK,
				  EudLogDrainNotify,
				  NULL,
				  &mDrainEvent
				  );
  if (EFI_ERROR (Status)) {
	return EFI_SUCCESS;
  }

  Status = gBS->SetTimer (
				  mDrainEvent,
				  TimerPeriodic,
				  (UINT64)EUD_DRAIN_TICK_MS * 10000U
				  );
  if (EFI_ERROR (Status)) {
	return EFI_SUCCESS;
  }

  return EFI_SUCCESS;
}
