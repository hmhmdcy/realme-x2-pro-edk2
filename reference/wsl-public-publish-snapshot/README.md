# WSL `public-publish` kernel source snapshot

This directory preserves five source files from the WSL recovery tree's
`public-publish` kernel commit `2f4b40575722f37f22140f2f5a99e0124fea092c`.
They are archival sources, not a patch series for the current
`codex/standard-arm64-v7.3.1` branch, whose history has no direct common
ancestor with `public-publish` and whose versions of these files differ.

Sources:

- `drivers/power/supply/mp2650_charger.c`
- `drivers/usb/dwc3/dwc3-qcom.c`
- `drivers/usb/typec/tcpm/qcom/qcom_pmic_typec.c`
- `drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.c`
- `drivers/usb/typec/tcpm/qcom/qcom_pmic_typec_port.h`

No build or hardware test is implied by inclusion here.