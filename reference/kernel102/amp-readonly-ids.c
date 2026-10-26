// SPDX-License-Identifier: GPL-2.0
// Only the two OEM revision registers are read. No amplifier register data
// is written. The caller verifies the exact QUP4 and TLMM identities and
// unbinds the native components before using I2C_SLAVE (never FORCE).
#define _DEFAULT_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/gpio.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static volatile sig_atomic_t interrupted;
static void stop(int sig) { (void)sig; interrupted=1; }

static int read_id(int fd, unsigned short addr, unsigned short reg, unsigned char *value)
{
	unsigned char pointer[2] = {reg >> 8, reg & 0xff};
	struct i2c_msg msgs[2] = {
		{.addr=addr,.len=2,.buf=pointer},
		{.addr=addr,.flags=I2C_M_RD,.len=1,.buf=value},
	};
	struct i2c_rdwr_ioctl_data transfer = {.msgs=msgs,.nmsgs=2};
	if (interrupted) { errno=EINTR; return -1; }
	return ioctl(fd,I2C_RDWR,&transfer)==2 ? 0 : -1;
}

int main(int argc,char **argv)
{
	int chip=-1,bus=-1,line=-1,rc=1;
	struct gpiochip_info info;
	struct gpio_v2_line_request request = {
		.offsets={148,37},.consumer="samurai-amp-id-only",.num_lines=2,
		.config={.flags=GPIO_V2_LINE_FLAG_OUTPUT},
	};
	struct gpio_v2_line_values values = {.mask=3,.bits=0};
	if (argc!=3) return 2;
	signal(SIGINT,stop);signal(SIGTERM,stop);
	chip=open(argv[2],O_RDONLY|O_CLOEXEC);
	if (chip<0 || ioctl(chip,GPIO_GET_CHIPINFO_IOCTL,&info)<0) goto out;
	if (strcmp(info.label,"3100000.pinctrl") || info.lines<=148) {errno=ENODEV;goto out;}
	bus=open(argv[1],O_RDWR|O_CLOEXEC);
	if (bus<0) goto out;
	if (ioctl(chip,GPIO_V2_GET_LINE_IOCTL,&request)<0) goto out;
	line=request.fd;
	// OEM reset sequence: physical low for 1ms, high, 20ms to settle.
	usleep(1000);
	if (interrupted) {errno=EINTR;goto out;}
	values.bits=3;
	if (ioctl(line,GPIO_V2_LINE_SET_VALUES_IOCTL,&values)<0) goto out;
	usleep(20000);
	for (unsigned short addr=0x39;addr<=0x3a;addr++) {
		unsigned char r27=0,r37=0;
		// This ordinary ioctl refuses addresses owned by a bound driver.
		if (ioctl(bus,I2C_SLAVE,addr)<0 || read_id(bus,addr,0x01ff,&r27)<0 ||
		    read_id(bus,addr,0x0600,&r37)<0) goto out;
		printf("address=0x%02x rev_01ff=0x%02x rev_0600=0x%02x\n",addr,r27,r37);
	}
	rc=0;
out:
	if (rc) perror("amp ID-only diagnostic");
	if (line>=0) {
		values.bits=0;
		if (ioctl(line,GPIO_V2_LINE_SET_VALUES_IOCTL,&values)<0) {perror("assert reset");rc=1;}
		close(line);
	}
	if (bus>=0) close(bus);
	if (chip>=0) close(chip);
	return rc;
}
