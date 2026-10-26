# Native DWC3 → USB-input system-PM ordering

This independent, uninstalled candidate adds one stateless system-PM dependency
before the USB input power supply is published. It starts from the frozen flat
consumer source `ee0f0806…27878a88` and preserves the actual R8 decoder
`a17caa2c…6d548fd`. It includes no future IRQ implementation. No Image, device,
budget policy or deployment tool is changed.

## Proven source-level gap

The old provider's `samurai_usb_suspend()` / `samurai_usb_stop()` set `paused=true`
and clear `udc_valid` (flat source:197–222). Its setter clears `udc_valid` before
returning `-EBUSY` while paused (139–157). Resume clears validity again before
unpausing. These conservative semantics remain byte-for-byte unchanged.

The fixed DWC core obtains this supply by `usb-psy-name`, a notifier and
`power_supply_get_by_name()` (`core.c`:2177–2274). Neither path creates a device
link. The generic lookup holds a class-device reference/use count; it does not
order PM. Existing R8 charger links are charger→input/protection/gauge, not
DWC→input. The input's runtime software node contains its `reg` property and no
DWC consumer phandle. No relevant DWC→this-provider link is established by these
fixed sources. This is a source audit, not a live device-link inventory.

A concrete permitted sequence is:

1. Input suspend pauses the provider and invalidates the old allowance.
2. With no dependency ordering, DWC resume runs first. Original gadget resume
   calls soft-connect (`gadget.c`:5013–5018). A real reset/configuration can
   deliver a new draw request through `composite_reset()` (2318),
   `set_config()` (1059), or configured `composite_resume()` (2645).
3. Original `dwc3_vbus_draw_work()` calls the real provider setter while it is
   still paused: `-EBUSY`, validity remains false. DWC only logs the error; it
   does not retry (core:2183–2188).
4. Input resume clears validity and unpauses. A DWC notifier that already owns
   the supply returns immediately (core:2198–2199); this notification does not
   replay the rejected allowance. With no later draw event, the actual a17
   decoder leaves an online SDP/FLOAT allowance at `-ENODATA` (103–105), not an
   invented 100mA fallback.

The candidate excludes the callback ordering in step 2: provider resume completes
before DWC resume; DWC suspend completes before provider suspend. It does **not**
join arbitrary system-workqueue vbus work. Already-queued work can still execute
while the provider is paused and be rejected. There is no cached-permission
replay, runtime-PM dependency, new retry or assurance of enumeration/recovery.
This is not an established cause or fix of r5 or the ordinary attach-icon delay.

## Exact narrow implementation

`samurai_usb_link_native_consumer()` checks both real controller paths:

- Legacy `/soc@0/usb@a6f8800/usb@a600000`, compatible `snps,dwc3`.
- Flat `/soc@0/usb@a600000`, compatible `qcom,snps-dwc3`.

Each must be available and have exactly
`usb-psy-name="samurai-usb-input"`. Two matching native controllers are rejected.
No matching native node retains the existing non-native observer path. A selected
node without its actual platform device, or a currently unregistered device,
returns `-EPROBE_DEFER`. The referenced platform device itself is the consumer;
neither a legacy wrapper nor the PSY class device is substituted. Selection does
not trust the user-settable `native_retained` parameter.

Before `devm_power_supply_register()`, the probe adds
`device_link_add(consumer, provider, DL_FLAG_STATELESS)` and registers its cleanup
action. Link rejection (including a reverse dependency rejected by the existing
driver core) returns `-EINVAL`; this API does not reveal which failure caused
NULL. Cleanup-action registration failure undoes the link and reference before
any PSY publication. No `DL_FLAG_PM_RUNTIME`, `RPM_ACTIVE`, managed flag, power
transition or current authorization is added.

The action stores endpoint device references, **not a raw link pointer**. It
calls `device_link_remove(consumer, supplier)` and then `put_device(consumer)`.
The fixed core performs that pair lookup under its link write lock; if consumer
`device_del()` already purged the link, removal is a no-op. Each successful add
has one remove, including an add which shares an existing link: other references
are not removed by this caller. The supplier device remains valid during its
own devres action. LIFO order is existing stop → PSY release → link/remove+put →
input allocation release.

`device_is_registered()` is a current check, **not** a lifetime lock against
concurrent platform `device_del()`. Physical USB cable removal does not destroy
this board's controller platform device. Explicit platform destruction and
recreation is not dynamically tracked; a purged pair is not rebuilt. The purge
fixture verifies endpoint cleanup and reference safety, not complete platform
hotplug or concurrent recreation support. No notifier framework is added.

The existing post-publication `samurai_usb_stop` devm-action allocation failure
remains an old boundary: a PSY may already have been seen by DWC before that old
failure unwinds. This patch does not claim all old probe failure paths are safe.
Its new fallible work finishes before publication.

## Why STATELESS orders this exact kernel

Fixed `drivers/base/core.c` initializes a stateless link to `DL_STATE_NONE`
(960–961), adds both endpoint lists and reorders the consumer (973–989).
`drivers/base/power/main.c` waits on all non-DORMANT, non-sync-only supplier links
(278–298) and consumer links (334–356). Normal resume calls the supplier wait at
1144; normal suspend calls the consumer wait at 1950. NONE participates in these
waits. The same source rejects reverse dependency cycles (core:843–847).

Raw-link deletion after purge is explicitly forbidden in core:1035–1036.
Endpoint removal is the existing alternative (1054–1070), also used by generic
PHY release. This uses system-PM ordering only; the existing runtime-PM policy
and every old budget/PM/poll/retention function remain unchanged.

## Verification and current delivery stage

`prepare.py` binds source hashes, emits the complete patch and actual function
extracts, and proves all 12 old functions other than probe remain byte-identical.
The header is byte-identical to a17. The only old function body changed is probe,
with one pre-publication call to the new helper.

`run-tests.py` passed 21 new cases with ASan/UBSan and `-Wall -Wextra -Werror`.
It executes actual new cleanup/link functions, the complete actual probe body,
unchanged provider PM/setter functions and the original DWC vbus work. OF,
driver-core/devres, PSY and workqueue interfaces are fake boundaries; neither
real kernel probe nor asynchronous system PM was run. Cases cover both native
paths, no native path, invalid/ambiguous selection, deferred/missing consumers,
link/action/publication failure, LIFO cleanup, already-purged/shared links,
parameter independence, unchanged old post-publication failure, lost-permission
ordering and the already-queued-work limitation. Old budget, IRQ and other
matrices were not rerun. The test ELF/logs are in the private output directory,
not this source leaf.

At this source-review stage no kernel object/module build has been requested or
run for this candidate. A later authorized private single-module build must use
the original284 guard and exact #502 config/symvers. No module was installed or
loaded and no device/SDK/Git operation occurred.
