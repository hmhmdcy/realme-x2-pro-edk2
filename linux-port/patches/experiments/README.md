# Experiments

Patches here are not part of the reproducible v7.3.1 deployment and must not
be applied to a production image without a new validation round.

- `0009-usb-dwc3-gadget-keep-connect-active-link.patch`: tested on RMX1931;
  U0 system sleep worked, but USB/NCM traffic did not wake the SoC because
  the DWC3 IRQ is a GIC IRQ, not a PDC wake source.  The test was recovered by
  the RTC safety alarm.  Deployment stays on the U3-only keep-connect policy.
