# Makefile for xEdgeSim Sensor Node Firmware
#
# Simplifies building the Zephyr firmware without remembering west/ninja commands

ZEPHYR_BASE ?= $(HOME)/repos/zephyrproject/zephyr
BUILD_DIR := build
BOARD := nrf52840dk/nrf52840

.PHONY: help build rebuild clean pristine test

help:
	@echo "xEdgeSim Sensor Node Firmware Build"
	@echo ""
	@echo "Targets:"
	@echo "  build      - Incremental build (fast, only rebuilds changed files)"
	@echo "  rebuild    - Same as build"
	@echo "  pristine   - Clean build from scratch"
	@echo "  clean      - Remove build directory"
	@echo "  test       - Run E2E integration test"
	@echo "  info       - Show build information"
	@echo ""
	@echo "Configuration:"
	@echo "  Current mode: $(shell grep 'CONFIG_XEDGESIM_EMULATION' prj.conf | cut -d= -f2)"
	@echo "  Board: $(BOARD)"

build: $(BUILD_DIR)/build.ninja
	@echo "Building firmware..."
	@cd $(BUILD_DIR) && ninja
	@echo ""
	@echo "Build complete:"
	@ls -lh $(BUILD_DIR)/zephyr/zephyr.elf
	@stat -f "  Modified: %Sm" $(BUILD_DIR)/zephyr/zephyr.elf
	@echo ""
	@if strings $(BUILD_DIR)/zephyr/zephyr.elf | grep -q "EMULATION MODE"; then \
		echo "  ✅ Emulation mode: ENABLED"; \
	else \
		echo "  ⚠️  Emulation mode: DISABLED"; \
	fi

rebuild: build

$(BUILD_DIR)/build.ninja:
	@echo "Build directory not initialized. Run 'make pristine' for first build."
	@exit 1

pristine:
	@echo "Pristine build (clean + configure + build)..."
	@if [ ! -d "$(ZEPHYR_BASE)" ]; then \
		echo "Error: ZEPHYR_BASE not found at $(ZEPHYR_BASE)"; \
		echo "Set ZEPHYR_BASE environment variable or edit Makefile"; \
		exit 1; \
	fi
	@rm -rf $(BUILD_DIR)
	@mkdir -p $(BUILD_DIR)
	@cd $(BUILD_DIR) && cmake -DBOARD=$(BOARD) -GNinja ..
	@$(MAKE) build

clean:
	@echo "Cleaning build directory..."
	@rm -rf $(BUILD_DIR)
	@echo "Done."

test:
	@echo "Running E2E integration test..."
	@cd ../.. && ./tests/stages/M3fc/test_e2e_renode.sh

info:
	@echo "Firmware Build Information"
	@echo "=========================="
	@echo "ZEPHYR_BASE: $(ZEPHYR_BASE)"
	@echo "Board: $(BOARD)"
	@echo "Build dir: $(BUILD_DIR)"
	@echo ""
	@if [ -f "$(BUILD_DIR)/zephyr/zephyr.elf" ]; then \
		echo "Current binary:"; \
		ls -lh $(BUILD_DIR)/zephyr/zephyr.elf; \
		stat -f "  Modified: %Sm" $(BUILD_DIR)/zephyr/zephyr.elf; \
		echo ""; \
		if strings $(BUILD_DIR)/zephyr/zephyr.elf | grep -q "EMULATION MODE"; then \
			echo "  Mode: EMULATION"; \
		else \
			echo "  Mode: PRODUCTION"; \
		fi; \
		echo ""; \
		echo "Memory usage:"; \
		arm-zephyr-eabi-size $(BUILD_DIR)/zephyr/zephyr.elf 2>/dev/null || echo "  (size tool not available)"; \
	else \
		echo "No binary found. Run 'make build' first."; \
	fi
