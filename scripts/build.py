#!/usr/bin/env python3
import argparse
import importlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from amaranth import Elaboratable
from amaranth.back import verilog

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with console and file handlers."""
    log_dir = Path("build/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "build.log"

    # Set logging level based on verbosity
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="a"),
            logging.StreamHandler(sys.stderr) if verbose else logging.NullHandler(),
        ],
    )

    logger.info("=" * 80)
    logger.info("Build session started")


def load_config() -> dict[str, Any]:
    logger.debug("Loading configuration from data/config/config.cue")
    try:
        result = subprocess.run(
            ["cue", "export", "data/config/config.cue"],
            capture_output=True,
            text=True,
            check=True,
        )
        config = json.loads(result.stdout)
        logger.info("Configuration loaded successfully")
        logger.debug("Config: %s", json.dumps(config, indent=2))
        return config
    except subprocess.CalledProcessError as e:
        logger.error("Failed to load CUE config: %s", e.stderr)
        print(f"✗ Error loading CUE config: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        logger.error("CUE binary not found in PATH")
        print("✗ CUE not found. Install: https://cuelang.org/")
        sys.exit(1)


def get_platform(board: str, config: dict[str, Any]) -> Any:
    logger.debug("Loading platform for board: %s", board)
    board_config = config["boards"][board]
    platform_path = board_config["platform"]
    module_path, class_name = platform_path.rsplit(".", 1)

    logger.debug("Importing platform: %s from %s", class_name, module_path)
    module = importlib.import_module(module_path)
    platform_class = getattr(module, class_name)

    platform = platform_class()
    logger.info("Platform loaded: %s", platform_path)
    return platform


def add_systemverilog_sources(platform: Any, sv_dir: str = "rtl") -> None:
    sv_path = Path(sv_dir)
    if sv_path.exists():
        sv_files = list(sv_path.glob("*.sv"))
        logger.info("Adding %d SystemVerilog source files from %s", len(sv_files), sv_dir)
        for sv_file in sv_files:
            logger.debug("Adding file: %s", sv_file)
            print(f"  + {sv_file}")
            with open(sv_file) as f:
                platform.add_file(str(sv_file), f.read())
    else:
        logger.debug("SystemVerilog directory not found: %s", sv_dir)


def build_fpga(design: Elaboratable, board: str) -> bool:
    logger.info("Starting FPGA build for board: %s", board)
    config = load_config()

    if board not in config["boards"]:
        logger.error("Unknown board: %s", board)
        logger.info("Available boards: %s", list(config["boards"].keys()))
        print(f"✗ Unknown board: {board}")
        print(f"Available: {', '.join(config['boards'].keys())}")
        return False

    try:
        platform = get_platform(board, config)
    except (ImportError, AttributeError) as e:
        logger.error("Failed to load platform: %s", e, exc_info=True)
        print(f"✗ Error loading platform: {e}")
        return False

    add_systemverilog_sources(platform)

    board_build_dir = Path("build/fpga") / board
    os.makedirs(board_build_dir, exist_ok=True)
    logger.debug("Build directory: %s", board_build_dir)

    board_config = config["boards"][board]
    device = board_config["device"]

    logger.info("Building for device: %s (%s)", device["model"], device["package"])
    print(f"\nBuilding: {board}")
    print(f"  Device: {device['model']} ({device['package']})")
    print(f"  Output: {board_build_dir}")

    try:
        logger.debug(
            "Starting platform build with verbose=%s, debug_verilog=%s",
            config["build"]["verbose"],
            config["build"]["debug_verilog"],
        )
        platform.build(
            design,
            do_build=True,
            build_dir=str(board_build_dir),
            verbose=config["build"]["verbose"],
            debug_verilog=config["build"]["debug_verilog"],
        )
        logger.info("Build completed successfully")
        logger.info("Bitstream location: %s/top.bin", board_build_dir)
        print("\n✓ Build complete")
        print(f"  Bitstream: {board_build_dir}/top.bin")
        return True
    except Exception as e:
        logger.error("Build failed: %s", e, exc_info=True)
        print(f"\n✗ Build failed: {e}")
        return False


def generate_verilog(design: Elaboratable) -> bool:
    output_path = Path("build/gen/top.v")
    os.makedirs(output_path.parent, exist_ok=True)

    logger.info("Generating Verilog to: %s", output_path)
    print(f"\nGenerating Verilog: {output_path}")

    logger.debug("Converting Amaranth design to Verilog")
    output = verilog.convert(design, ports=[], emit_src=True)

    logger.debug("Writing Verilog output (%d bytes)", len(output))
    with open(output_path, "w") as f:
        f.write(output)

    logger.info("Verilog generation complete")
    print("✓ Generated")

    sv_dir = Path("rtl")
    if sv_dir.exists() and list(sv_dir.glob("*.sv")):
        sv_files = list(sv_dir.glob("*.sv"))
        logger.info("Found %d SystemVerilog files in %s", len(sv_files), sv_dir)
        print("  SystemVerilog files:")
        for sv_file in sv_files:
            logger.debug("SystemVerilog file: %s", sv_file)
            print(f"    - {sv_file}")

    return True


def list_boards() -> None:
    logger.info("Listing available boards")
    config = load_config()
    print("Available boards:")
    for name, board in config["boards"].items():
        device = board["device"]
        logger.debug("Board: %s - %s (%s)", name, device["model"], device["package"])
        print(f"  {name:20s} {device['model']:12s} ({device['package']})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build FPGA design")
    parser.add_argument("--board", type=str, default="ice40_hx8k_evn", help="Board name")
    parser.add_argument("--list-boards", action="store_true", help="List boards")
    parser.add_argument("--verilog-only", action="store_true", help="Generate Verilog only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Initialize logging
    setup_logging(verbose=args.verbose)
    logger.info("Arguments: %s", vars(args))

    if args.list_boards:
        list_boards()
        return 0

    sys.path.insert(0, str(Path(__file__).parent.parent / "hdl"))
    from top import Top

    design = Top()

    success = generate_verilog(design) if args.verilog_only else build_fpga(design, args.board)

    if success:
        logger.info("Build process completed successfully")
    else:
        logger.error("Build process failed")

    logger.info("Log file: build/logs/build.log")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
