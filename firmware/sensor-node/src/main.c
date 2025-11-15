/*
 * xEdgeSim Sensor Node Firmware
 *
 * Minimal Zephyr RTOS application that:
 * - Generates synthetic sensor samples using deterministic RNG
 * - Outputs JSON-formatted events over UART
 * - Provides deployable artifact for Renode emulation
 *
 * Copyright (c) 2025 xEdgeSim Project
 */

#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/random/random.h>
#include <zephyr/sys/printk.h>
#include <stdio.h>
#include <string.h>

/* Configuration from device tree */
#define RNG_SEED_DEFAULT 12345
#define SAMPLE_INTERVAL_US 1000000  /* 1 second */
#define SENSOR_MIN_VALUE 20.0f
#define SENSOR_MAX_VALUE 30.0f

/* UART device for JSON output */
static const struct device *uart_dev;

/* Virtual time tracking (microseconds) */
static uint64_t current_time_us = 0;

/* RNG state */
static uint32_t rng_seed = RNG_SEED_DEFAULT;
static uint32_t rng_state = RNG_SEED_DEFAULT;
static bool rng_initialized = false;

/**
 * Simple LCG PRNG for deterministic sensor values
 * Uses constants from Numerical Recipes
 */
static uint32_t prng_next(void)
{
	rng_state = rng_state * 1664525 + 1013904223;
	return rng_state;
}

/**
 * Initialize the RNG with seed from device tree
 */
static void init_rng(void)
{
	if (rng_initialized) {
		return;
	}

	/* In production, seed would come from device tree
	 * For now, use hardcoded default
	 *
	 * Note: sys_rand_seed_set() was removed in Zephyr 4.x
	 * The random subsystem is now hardware-based or uses CSPRNGs
	 * For deterministic testing, we'll use a simpler PRNG
	 */
	rng_initialized = true;

	printk("xEdgeSim: RNG initialized with seed %u\n", rng_seed);
}

/**
 * Generate a synthetic sensor sample using deterministic RNG
 *
 * @return Sensor value in range [SENSOR_MIN_VALUE, SENSOR_MAX_VALUE]
 */
static float generate_sensor_sample(void)
{
	uint32_t raw = prng_next();

	/* Map random value to sensor range */
	float range = SENSOR_MAX_VALUE - SENSOR_MIN_VALUE;
	float normalized = (raw % 10000) / 10000.0f;  /* [0.0, 1.0) */
	float value = SENSOR_MIN_VALUE + (normalized * range);

	return value;
}

/**
 * Output a JSON event to UART
 *
 * Format: {"type":"SAMPLE","value":<float>,"time":<uint64>}\n
 *
 * @param event_type Event type string
 * @param value Sensor reading
 * @param time_us Virtual time in microseconds
 */
static void output_json_event(const char *event_type, float value, uint64_t time_us)
{
	char buffer[256];
	int len;

	/* Format JSON (compact, no whitespace) */
	len = snprintf(buffer, sizeof(buffer),
		       "{\"type\":\"%s\",\"value\":%.1f,\"time\":%llu}\n",
		       event_type, (double)value, time_us);

	if (len < 0 || len >= sizeof(buffer)) {
		printk("xEdgeSim: Error formatting JSON\n");
		return;
	}

	/* Send to UART */
	if (uart_dev != NULL) {
		for (int i = 0; i < len; i++) {
			uart_poll_out(uart_dev, buffer[i]);
		}
	} else {
		/* Fallback to printk if UART not available (for testing) */
		printk("%s", buffer);
	}
}

/**
 * Main application entry point
 */
int main(void)
{
	printk("\n=== xEdgeSim Sensor Node ===\n");
	printk("Firmware version: 1.0.0\n");
	printk("Build: %s %s\n", __DATE__, __TIME__);
	printk("Board: nRF52840 DK\n");

	/* Initialize UART for JSON output */
	uart_dev = DEVICE_DT_GET(DT_NODELABEL(uart0));
	if (!device_is_ready(uart_dev)) {
		printk("ERROR: UART device not ready\n");
		uart_dev = NULL;  /* Fall back to printk */
	} else {
		printk("UART0 ready for JSON output\n");
	}

	/* Initialize RNG */
	init_rng();

	printk("Sample interval: %u us\n", SAMPLE_INTERVAL_US);
	printk("Sensor range: %.1f - %.1f\n",
	       (double)SENSOR_MIN_VALUE, (double)SENSOR_MAX_VALUE);
	printk("\nStarting sensor loop...\n\n");

#ifdef CONFIG_XEDGESIM_EMULATION
	/*
	 * xEdgeSim Emulation Mode
	 *
	 * Deterministic behavior for coordinator time-stepping tests:
	 * - Emit all samples immediately on boot (no sleep/delays)
	 * - Pre-assign timestamps at 1-second intervals
	 * - Coordinator will filter/assign events to time steps
	 *
	 * This works with time-stepped execution because events are
	 * emitted immediately, not dependent on virtual time advancement.
	 */
	printk("*** EMULATION MODE: Deterministic sampling ***\n");

	#define NUM_SAMPLES 10

	/* Emit all samples immediately with future timestamps */
	for (int sample_idx = 0; sample_idx < NUM_SAMPLES; sample_idx++) {
		/* Generate deterministic sample value */
		float value = generate_sensor_sample();

		/* Calculate timestamp for this sample (1 second intervals) */
		uint64_t sample_time_us = sample_idx * SAMPLE_INTERVAL_US;

		/* Output JSON event with assigned timestamp */
		output_json_event("SAMPLE", value, sample_time_us);
	}

	printk("*** EMULATION MODE: %d samples emitted, entering idle ***\n", NUM_SAMPLES);

	/* After emitting all samples, sleep forever */
	while (1) {
		k_sleep(K_FOREVER);
	}
#else
	/*
	 * Production Mode
	 *
	 * Real sensor sampling loop for hardware deployment
	 */
	while (1) {
		/* Generate sensor sample */
		float value = generate_sensor_sample();

		/* Output JSON event */
		output_json_event("SAMPLE", value, current_time_us);

		/* Sleep for sample interval */
		k_usleep(SAMPLE_INTERVAL_US);

		/* Advance virtual time */
		current_time_us += SAMPLE_INTERVAL_US;
	}
#endif

	return 0;
}
