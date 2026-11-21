#!/bin/sh
set +e
echo ===DMESG_CORE===
dmesg --ctime 2>/dev/null | grep -iE 'mp2650|tcpm|tcpci|typec|charger|charging|battery|bq28|apsd|vbus|power.supply|usb-input|samurai-usb' | grep -viE 'qcom_q6v5_pas|Q6 ready' | tail -120
echo ===DMESG_LAST===
dmesg --ctime 2>/dev/null | tail -30
echo ===DAILY===
ls -ld /root/charging-daily-20261028-01-before 2>&1
du -sh /root/charging-daily-20261028-01-before 2>&1
find /root/charging-daily-20261028-01-before -maxdepth 2 -print 2>&1 | sort
ls -laR /root/charging-daily-20261028-01-before 2>&1
echo ===END===
