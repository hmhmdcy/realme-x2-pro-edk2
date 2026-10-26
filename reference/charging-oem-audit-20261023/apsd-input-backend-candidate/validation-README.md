# R7 APSD transport: offline validation

The author's wrapper, four-function include, API header, decoder and generator
were not edited. The tested wrapper is `fc7c42cf…427d7`, include
`ef6baeee…f4ff2`, API `00d5659e…cee94`. The actual unchanged R7 status reader
and budget getter were extracted and compared with the R7 source before
testing. The actual candidate stop/suspend/resume functions and whole include
were executed in the host fixture; no backend algorithm was reimplemented.

Ten new actual-function groups passed ASan/UBSan and Werror:

- Two new seven-register reads, exact order/raw output, increasing serial;
  all 14 read failure positions, unequal snapshots and untouched output.
- All-off/all-on wire presence and each missing prerequisite; a source/error
  state may still report wire presence while the ordinary budget rejects it.
  Presence does not authorize PD, route or APSD.
- Null output, serial overflow and paused/joining guards reject before I/O.
- Epoch zero/duplicate/stale rejection; failed, paused or joining calls consume
  the epoch, including no retry after resume and no wrap to an old epoch.
- Actual `regmap_write_bits` inline uses `force=true`; an already-set command
  bit does not skip the masked write. Other command bits are preserved.
- Default-false behavior, optional registration failure retaining the normal
  budget observer, duplicate-start short circuit, withdraw outside the callback
  lock, late callback zero-I/O, and actual stop/resume preserving both counters.
  Resume clears the old native UDC allowance rather than inventing 100 mA.

The regmap test extracts the actual Image-associated `regmap_write_bits`
inline and substitutes only its bus boundary. A successful RMW can require a
read followed by one write; this is not a claim of one total bus transaction.
An error before the physical write can mean zero writes, and still consumes
the attempt. The fake boundary tests establish callback behavior, not PMIC
hardware completion or real PD/route permission.

Only `samurai-usb-input.o` was privately compiled using the original
source-float cached W=1 command plus Werror. The private command defines the
new owner option so the real external registration interface is compiled;
neither the original nor shared config was changed. It passed with zero
diagnostics, object SHA
`0fe22a56dc7568228f77d9d913bbed937eb2b8d6d0e8966228ee83d17f07d840`.
The original source-float module/object/command/config, generated headers,
source files and shared config/header snapshots were identical before/after.
No make, SDK, module/Image link, installation or device access was performed.
The unique private object directory is retained and the build runner refuses
replay. Existing R7/FLOAT and owner suites were not rerun.

The transport remains optional and disabled by default. No real PD/route
lease or EUD/PHY removal coverage is supplied by this backend. The separate
DWC owner still refuses every real attempt at its explicit missing-coverage
gate. A new provider instance starts its own serial counter, whereas the
owner preserves physical-session history; that can conservatively return
ESTALE until a genuine detach. It is not permission to reset or retry an
attempt. A future enabled owner must review provider-instance identity with
the real lease and component lifetime integration.

`test-result.json` and `object-build-result.json` bind the exact source bytes,
commands and original-input snapshots. `validation-delivery.json` binds this
limited validation addition; it does not freeze or replace the author's
separate review or any live boot transaction.
