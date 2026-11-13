# Temporary plasma-nm mobile Wi-Fi KCM fix

This directory is a temporary downstream package for Plasma 6.8.2. It
contains one desktop/UI-layer fix and no Realme-specific logic. The
fix corresponds to upstream merge request
[!695](https://invent.kde.org/plasma/plasma-nm/-/merge_requests/695),
which is still open and is not in a released plasma-nm.

## Root cause

`kcms/kcm_wifi_mobile/ui/main.qml` handled the Wi-Fi switch through
`onCheckedChanged`:

```qml
checked: enabledConnections.wirelessEnabled
onCheckedChanged: {
    handler.enableWireless(checked);
    checked = Qt.binding(() => enabledConnections.wirelessEnabled);
}
```

`FormSwitchDelegate` writes the inherited `checked` property when its
inner switch is toggled, and `EnabledConnections` also changes it when
NetworkManager reports a radio or rfkill change. Both paths can enter
`onCheckedChanged`. The explicit `Qt.binding()` then re-evaluates
`checked` before NetworkManager has necessarily applied the previous
write, so the handler can issue the opposite radio-control request on
the next event. The result is a rapid `wireless-enabled:on/off` loop;
the final state can be `phy0: Soft blocked: yes`, with `wlan0` DOWN.

The desktop Network Management applet in the same plasma-nm tree
already uses the correct user-only pattern:

```qml
onToggled: handler.enableWireless(checked)
```

## Fix

Patch `0001-kcm-mobile-wifi-use-onToggled.patch` does the same in the
mobile Wi-Fi KCM:

```qml
checked: enabledConnections.wirelessEnabled
onToggled: handler.enableWireless(checked)
```

`onToggled` is emitted for the user action forwarded by
`FormSwitchDelegate`; it is not emitted when the bound `checked`
property changes programmatically. The declarative binding remains
the source of truth, so the switch still follows changes made by the
quick-settings panel, `nmcli`, or rfkill.

Upstream MR !695 changes only `onCheckedChanged` to `onToggled` and
keeps the explicit `Qt.binding()`. This local patch also removes the
redundant rebinding: in the on-device harness the upstream variant
settled correctly but briefly changed `checked` false/true/false after
one toggle. The local variant produced only the intended single
transition.

## Verification

A standalone QML harness on the RMX1931 used the same
`PlasmaNM.Handler`, `PlasmaNM.EnabledConnections`, and
`FormCard.FormSwitchDelegate` objects.

- Old handler: one user-like toggle produced 16 `checkedChanged`
  events in about three seconds, ended with `nmcli radio wifi`
  disabled and `phy0: Soft blocked: yes`.
- Fixed handler: one user toggle turned the radio off once; a
  subsequent programmatic `enableWireless(true)` restored the switch
  and the radio, with no extra toggle and no rfkill block.

The patched `kcm_mobile_wifi.so` was built from the 6.8.2 tarball and
installed for loading tests. `kcmshell6 --list` lists
`kcm_mobile_wifi`, and `kcmshell6 kcm_mobile_wifi` opens without QML
errors. A physical touch/click acceptance test on the panel and a
repeated quick-settings toggle test remain user-visible acceptance
steps; they are not claimed here.

Installed test build:

```text
/usr/lib/qt6/plugins/plasma/kcms/systemsettings/kcm_mobile_wifi.so
SHA-256 ed60135ebe9cbc064df19cf146337238512891401a21b7099234f5337052b1f1
```

Rollback copy on the device:

```text
/root/kcm_mobile_wifi.so.orig-20261113
SHA-256 8041319a20aa38c7f084ca65932918eb676ac5eca68d5e5a4055be61592164c7
```

## Build

The package is forked from Alpine aports `community/plasma-nm` at
6.8.2. Build it explicitly for aarch64; the package declares
`arch=all`, so an unpinned build on an x86_64 host is not valid:

```sh
pmbootstrap build --arch aarch64 --lax plasma-nm
```

Install the resulting APK, then restart the Plasma settings process or
reopen the Wi-Fi KCM. Do not restart NetworkManager while the only
remote access is USB NCM.

## Upstream disposition

This belongs to plasma-nm, not to the samurai board package. Prefer
the upstream MR !695 review/merge path and remove this downstream
package when a fixed plasma-nm is available from Alpine. The emergency
`/usr/sbin/samurai-wifi-recover` script remains a recovery tool only,
not the normal fix.
