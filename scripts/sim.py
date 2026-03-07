#!/usr/bin/env python3
import argparse
import logging
import os
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with console and file handlers."""
    log_dir = Path("build/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "sim.log"

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
    logger.info("Simulation session started")


def generate_verilog() -> bool:
    logger.info("Generating Verilog from Amaranth design")
    print("Generating Verilog from Amaranth...")
    cmd = ["uv", "run", "python", "scripts/build.py", "--verilog-only"]
    logger.debug("Running command: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode == 0:
        logger.info("Verilog generation successful")
    else:
        logger.error("Verilog generation failed with code %d", result.returncode)
    return result.returncode == 0


def collect_sv_sources(sv_dir: str = "rtl") -> list[Path]:
    """Collect SystemVerilog files from local rtl/ and installed packages."""
    sv_files: list[Path] = []

    sv_path = Path(sv_dir)
    if sv_path.exists():
        sv_files.extend(sv_path.glob("*.sv"))

    eps = entry_points(group="amaranth.sv_sources")
    for ep in eps:
        try:
            fn = ep.load()
            sv_files.extend(fn())
        except Exception as exc:
            logger.warning("Failed to load SV sources from %s: %s", ep.name, exc)

    return sv_files


def run_verilator(testbench: str, top_module: str = "top") -> bool:
    logger.info("Starting Verilator simulation: testbench=%s, top_module=%s", testbench, top_module)
    build_dir = Path("build/sim")
    build_dir.mkdir(parents=True, exist_ok=True)
    obj_dir = build_dir / "obj_dir"
    logger.debug("Simulation build directory: %s", build_dir)

    gen_verilog = Path("build/gen/top.v")
    rtl_files = collect_sv_sources()
    tb_file = Path(f"testbenches/{testbench}.cpp")

    logger.debug("Generated Verilog: %s (exists=%s)", gen_verilog, gen_verilog.exists())
    logger.debug("Testbench file: %s (exists=%s)", tb_file, tb_file.exists())
    logger.debug("RTL files: %d files found", len(rtl_files))

    if not gen_verilog.exists():
        logger.error("Generated Verilog not found: %s", gen_verilog)
        print("✗ Generated Verilog not found. Run verilog generation first.")
        return False

    if not tb_file.exists():
        logger.error("Testbench file not found: %s", tb_file)
        print(f"✗ Testbench {tb_file} not found")
        return False

    print(f"\nRunning Verilator simulation: {testbench}")
    print(f"  Testbench: {tb_file}")
    print(f"  RTL files: {len(rtl_files)} SystemVerilog files")

    systemc_include = os.environ.get("SYSTEMC_INCLUDE", "")
    systemc_libdir = os.environ.get("SYSTEMC_LIBDIR", "")

    if not systemc_include or not systemc_libdir:
        logger.error("SYSTEMC_INCLUDE/SYSTEMC_LIBDIR not set. Run inside nix develop.")
        print("✗ SYSTEMC_INCLUDE/SYSTEMC_LIBDIR not set. Run inside 'nix develop'.")
        return False

    verilator_cmd = [
        "verilator",
        "--sc",
        "--trace",
        "--exe",
        "-Wall",
        "-Wno-fatal",
        "--top-module",
        top_module,
        "-CFLAGS",
        f"-I{systemc_include}",
        "-LDFLAGS",
        f"-L{systemc_libdir} -lsystemc",
        "-Mdir",
        str(obj_dir),
        str(tb_file),
        str(gen_verilog),
        *[str(f) for f in rtl_files],
    ]

    logger.debug("Verilator command: %s", " ".join(verilator_cmd))

    try:
        logger.info("Running Verilator compilation")
        result = subprocess.run(verilator_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("Verilator compilation failed with code %d", result.returncode)
            logger.error("Verilator stderr: %s", result.stderr)
            print(f"✗ Verilator failed:\n{result.stderr}")
            return False

        logger.info("Verilator compilation successful")
        print("✓ Verilator compilation successful")

        logger.info("Building simulation with make")
        print("Building simulation...")
        result = subprocess.run(
            ["make", "-C", str(obj_dir), "-f", f"V{top_module}.mk"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error("Make failed with code %d", result.returncode)
            logger.error("Make stderr: %s", result.stderr)
            print(f"✗ Make failed:\n{result.stderr}")
            return False

        logger.info("Make build successful")
        print("✓ Build successful")

        sim_exe = obj_dir / f"V{top_module}"
        logger.debug("Simulation executable: %s", sim_exe)
        if not sim_exe.exists():
            logger.error("Simulation executable not found: %s", sim_exe)
            print(f"✗ Simulation executable not found: {sim_exe}")
            return False

        logger.info("Running simulation executable")
        print("\nRunning simulation...")
        result = subprocess.run([str(sim_exe)], capture_output=True, text=True)

        if result.returncode == 0:
            logger.info("Simulation completed successfully")
            logger.debug("Simulation stdout: %s", result.stdout)
            print("✓ Simulation completed")
            print(result.stdout)

            vcd_file = build_dir / f"{testbench}.vcd"
            if vcd_file.exists():
                logger.info("VCD file generated: %s", vcd_file)
                print(f"  VCD: {vcd_file}")
            else:
                logger.warning("VCD file not found: %s", vcd_file)
            return True
        else:
            logger.error("Simulation failed with code %d", result.returncode)
            logger.error("Simulation stderr: %s", result.stderr)
            print(f"✗ Simulation failed:\n{result.stderr}")
            return False

    except FileNotFoundError:
        logger.error("Verilator binary not found in PATH")
        print("✗ Verilator not found. Install via Nix: nix develop")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Verilator simulation")
    parser.add_argument("--testbench", "-t", default="tb_top", help="Testbench name")
    parser.add_argument("--skip-gen", action="store_true", help="Skip Verilog generation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Initialize logging
    setup_logging(verbose=args.verbose)
    logger.info("Arguments: %s", vars(args))

    if not args.skip_gen and not generate_verilog():
        logger.error("Verilog generation step failed")
        return 1

    success = run_verilator(args.testbench)

    if success:
        logger.info("Simulation process completed successfully")
    else:
        logger.error("Simulation process failed")

    logger.info("Log file: build/logs/sim.log")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
