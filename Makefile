.PHONY: help init env lint test scenario-vib

help:
	@echo "xEdgeSim top-level Makefile"
	@echo "Available targets:"
	@echo "  init          - initialise environment (virtualenv, etc.)"
	@echo "  env           - print environment info"
	@echo "  lint          - placeholder for code quality checks"
	@echo "  test          - placeholder for tests"
	@echo "  scenario-vib  - placeholder to run vibration monitoring scenario"

init:
	./scripts/setup_env.sh

env:
	@echo "Python: $$(command -v python3 || echo 'not found')"
	@echo "Docker: $$(command -v docker || echo 'not found')"

lint:
	@echo "[xEdgeSim] No linting configured yet (P0)."

test:
	@echo "[xEdgeSim] No tests configured yet (P0)."

scenario-vib:
	@echo "[xEdgeSim] Vibration monitoring scenario runner not yet implemented."
