/*
 * Minimal UART test firmware for xEdgeSim
 *
 * This firmware does ONE thing: spam a known string to UART0
 * to prove the Renode UART capture path works.
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <string.h>

#define DEVICE_NAME "uart0"
#define TEST_MESSAGE "BOOT HELLO 123\n"

static const struct device *uart_dev;

static void uart_write_string(const char *str)
{
	int len = strlen(str);
	for (int i = 0; i < len; i++) {
		uart_poll_out(uart_dev, str[i]);
	}
}

int main(void)
{
	/* Get UART0 device */
	uart_dev = DEVICE_DT_GET(DT_NODELABEL(uart0));

	/* Don't check if ready - just try to use it */
	/* (device_is_ready might fail in emulation but UART still works) */

	/* Infinite loop spamming test message */
	while (1) {
		uart_write_string(TEST_MESSAGE);

		/* Small delay to avoid spam */
		k_msleep(100);
	}

	return 0;
}
