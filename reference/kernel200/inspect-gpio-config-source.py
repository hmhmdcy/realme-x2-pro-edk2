from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
for name in ['drivers/pinctrl/qcom/pinctrl-msm.c','drivers/gpio/gpiolib-cdev.c']:
 s=(k/name).read_text();lines=s.splitlines()
 print(name)
 for i,l in enumerate(lines):
  if (name.endswith('pinctrl-msm.c') and ('.set_config' in l or 'static int msm_config_group_set' in l)) or (name.endswith('gpiolib-cdev.c') and 'gpiod_set_config' in l):print('\n'.join(lines[max(0,i-4):i+12]))
