#!/usr/bin/env python3
"""
run_scenario.py - xEdgeSim Scenario Execution (M3g)

Executes simulation scenarios from YAML configuration files.

Usage:
    python3 sim/harness/run_scenario.py scenarios/my_scenario.yaml
    python3 sim/harness/run_scenario.py scenarios/my_scenario.yaml --seed 123
    python3 sim/harness/run_scenario.py scenarios/my_scenario.yaml --verbose

The script will:
1. Load scenario from YAML
2. Validate configuration
3. Launch all components (Docker, Renode, Python nodes)
4. Run coordinator with specified duration
5. Clean shutdown of all components
6. Report results
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sim.config.scenario import load_scenario
from sim.harness.launcher import SimulationLauncher


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run an xEdgeSim scenario from YAML configuration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run scenario with default seed
  python3 sim/harness/run_scenario.py scenarios/m0_baseline.yaml

  # Override seed for different random behavior
  python3 sim/harness/run_scenario.py scenarios/m0_baseline.yaml --seed 123

  # Verbose output
  python3 sim/harness/run_scenario.py scenarios/m0_baseline.yaml --verbose

For more information, see docs/README-ML-PLACEMENT.md
        """
    )

    parser.add_argument(
        "config",
        type=Path,
        help="Path to scenario YAML file"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Override random seed (default: use seed from YAML)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output (more detailed logging)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate scenario without executing (validate only)"
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point.

    Returns:
        0 on success, 1 on failure
    """
    args = parse_args()

    # Check scenario file exists
    if not args.config.exists():
        print(f"ERROR: Scenario file not found: {args.config}", file=sys.stderr)
        return 1

    try:
        # Load scenario
        print(f"Loading scenario from: {args.config}")
        scenario = load_scenario(str(args.config))

        # Override seed if specified
        if args.seed is not None:
            print(f"Overriding seed: {scenario.seed} → {args.seed}")
            scenario.seed = args.seed

        # Dry run mode - validate only
        if args.dry_run:
            print("\n" + "="*60)
            print("DRY RUN MODE - Validation Only")
            print("="*60)

            launcher = SimulationLauncher(scenario)
            errors = launcher.validate_scenario()

            if errors:
                print("\n✗ Scenario validation FAILED:")
                for error in errors:
                    print(f"  - {error}")
                return 1
            else:
                print("\n✓ Scenario validation PASSED")
                print("\nScenario summary:")
                print(f"  Duration: {scenario.duration_s}s")
                print(f"  Seed: {scenario.seed}")
                print(f"  Time quantum: {scenario.time_quantum_us}us")
                print(f"  Nodes: {len(scenario.nodes)}")
                if scenario.network:
                    print(f"  Network model: {scenario.network.model}")
                if scenario.ml_inference:
                    print(f"  ML placement: {scenario.ml_inference.placement}")
                print("\n(Use without --dry-run to execute)")
                return 0

        # Normal execution mode
        print("\n" + "="*60)
        print("Executing Scenario")
        print("="*60)

        # Create launcher and run
        launcher = SimulationLauncher(scenario)
        result = launcher.run()

        # Report results
        print("\n" + "="*60)
        print("Execution Complete")
        print("="*60)

        if result.success:
            print("\n✓ SUCCESS")
            print(f"\nResults:")
            print(f"  Virtual time: {result.virtual_time_sec:.2f}s")
            print(f"  Wall time: {result.duration_sec:.2f}s")
            speedup = result.virtual_time_sec / result.duration_sec if result.duration_sec > 0 else 0
            print(f"  Speedup: {speedup:.1f}x")
            print(f"\nMetrics written to CSV files (check working directory)")
            return 0
        else:
            print("\n✗ FAILED")
            print(f"\nError: {result.error_message}")
            return 1

    except FileNotFoundError as e:
        print(f"\nERROR: File not found: {e}", file=sys.stderr)
        return 1

    except ValueError as e:
        print(f"\nERROR: Invalid scenario configuration:", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"\nERROR: Unexpected error:", file=sys.stderr)
        print(f"  {type(e).__name__}: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
