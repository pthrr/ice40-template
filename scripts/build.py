#!/usr/bin/env python3
import argparse
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from amaranth import Elaboratable
from amaranth.back import verilog


def load_config() -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["cue", "export", "data/config/config.cue"],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"✗ Error loading CUE config: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("✗ CUE not found. Install: https://cuelang.org/")
        sys.exit(1)


def get_platform(board: str, config: dict[str, Any]) -> Any:
    board_config = config["boards"][board]
    platform_path = board_config["platform"]
    module_path, class_name = platform_path.rsplit(".", 1)

    module = importlib.import_module(module_path)
    platform_class = getattr(module, class_name)

    return platform_class()


def add_systemverilog_sources(platform: Any, sv_dir: str = "rtl") -> None:
    sv_path = Path(sv_dir)
    if sv_path.exists():
        for sv_file in sv_path.glob("*.sv"):
            print(f"  + {sv_file}")
            with open(sv_file) as f:
                platform.add_file(str(sv_file), f.read())


def build_fpga(design: Elaboratable, board: str) -> bool:
    config = load_config()

    if board not in config["boards"]:
        print(f"✗ Unknown board: {board}")
        print(f"Available: {', '.join(config['boards'].keys())}")
        return False

    try:
        platform = get_platform(board, config)
    except (ImportError, AttributeError) as e:
        print(f"✗ Error loading platform: {e}")
        return False

    add_systemverilog_sources(platform)

    board_build_dir = Path("build/fpga") / board
    os.makedirs(board_build_dir, exist_ok=True)

    board_config = config["boards"][board]
    device = board_config["device"]

    print(f"\nBuilding: {board}")
    print(f"  Device: {device['model']} ({device['package']})")
    print(f"  Output: {board_build_dir}")

    try:
        platform.build(
            design,
            do_build=True,
            build_dir=str(board_build_dir),
            verbose=config["build"]["verbose"],
            debug_verilog=config["build"]["debug_verilog"],
        )
        print("\n✓ Build complete")
        print(f"  Bitstream: {board_build_dir}/top.bin")
        return True
    except Exception as e:
        print(f"\n✗ Build failed: {e}")
        return False


def generate_verilog(design: Elaboratable) -> bool:
    output_path = Path("build/gen/top.v")
    os.makedirs(output_path.parent, exist_ok=True)

    print(f"\nGenerating Verilog: {output_path}")

    output = verilog.convert(design, ports=[], emit_src=True)

    with open(output_path, "w") as f:
        f.write(output)

    print("✓ Generated")

    sv_dir = Path("rtl")
    if sv_dir.exists() and list(sv_dir.glob("*.sv")):
        print("  SystemVerilog files:")
        for sv_file in sv_dir.glob("*.sv"):
            print(f"    - {sv_file}")

    return True


def list_boards() -> None:
    config = load_config()
    print("Available boards:")
    for name, board in config["boards"].items():
        device = board["device"]
        print(f"  {name:20s} {device['model']:12s} ({device['package']})")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build FPGA design")
    parser.add_argument("--board", type=str, default="ice40_hx8k_evn", help="Board name")
    parser.add_argument("--list-boards", action="store_true", help="List boards")
    parser.add_argument("--verilog-only", action="store_true", help="Generate Verilog only")

    args = parser.parse_args()

    if args.list_boards:
        list_boards()
        return 0

    sys.path.insert(0, str(Path(__file__).parent.parent / "hdl"))
    from top import Top

    design = Top()

    success = generate_verilog(design) if args.verilog_only else build_fpga(design, args.board)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
