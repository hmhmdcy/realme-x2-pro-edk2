# Experiments

Patches here are not part of the reproducible v7.3.1 deployment and must not
be applied to a production image without a new validation round.

- `0009-usb-dwc3-gadget-keep-connect-active-link.patch`: tested on RMX1931;
  U0 system sleep worked, but USB/NCM traffic did not wake the SoC because
  the DWC3 IRQ is a GIC IRQ, not a PDC wake source.  The test was recovered by
  the RTC safety alarm.  Board keep-connect remains disabled; the standard
  DWC3 gadget suspend/resume path is used instead.
- `0010-usb-typec-pmic-attach-wake.patch`: arms the standard PM8150B
  Type-C CC-state, VBUS-change and attach-detach SPMI child IRQs as system
  wake sources when the Type-C node has `wakeup-source`.  The earlier
  revision of this patch is built into the deployed
  `7.3.1-rmx1931-samurai-v731-usbwake #6` Image; the current revision
  (`6ccc...`) has only formatting plus symmetric error-path unwind changes
  and is built into the undeployed `e1e6...` candidate Image.  The
  persistent Type-C DTB remains deployed; three 15-second, one 60-second
  and eight 15-second `s2idle` cycles passed with UDC/NCM recovery.  The
  `typec_wake_near` boundary diagnostic proved the IRQ -> SPMI -> PDC
  path; a physical cable insert or removal during suspend is still the
  required missing acceptance step.  The patch reverses cleanly against
  the WSL source tree used to build the Image.  `checkpatch.pl --strict`
  reports 0 errors and 0 checks; the remaining warning is the expected
  request to split the DT binding documentation into a separate patch.
- `0011-usb-dwc3-qcom-vbus-override-probe.patch`: generic upstream
  Qualcomm fix for OTG + `usb-role-switch` when the default role is
  peripheral.  `dwc3-qcom` did not enable the QSCRATCH `VBUS_VALID`
  override at probe because no role transition occurred, so the first
  device session could lack session-valid.  The patch is included in the
  deployed `...-usbwake-otg` image and applies cleanly to the v7.3.1
  source; physical OTG host/device hardware acceptance is still pending.
- `unudhcpd` DHCP broadcast handling: the package-owned patch in
  `linux-port/packages/unudhcpd/` keeps the DHCP BROADCAST flag and
  sends OFFER/ACK to `255.255.255.255` when the host requests it.
  Windows NCM re-enumeration then obtains `172.16.42.2/24` from
  `172.16.42.1`.
