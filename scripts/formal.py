#!/usr/bin/env python3
import argparse
import logging
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with console and file handlers."""
    log_dir = Path("build/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "formal.log"

    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="a"),
            logging.StreamHandler(sys.stderr) if verbose else logging.NullHandler(),
        ],
    )

    logger.info("=" * 80)
    logger.info("Formal verification session started")


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


def discover_sources() -> tuple[list[Path], list[Path]]:
    """Discover Amaranth-generated Verilog and SV RTL sources."""
    gen_dir = Path("build/gen")
    gen_files = sorted(gen_dir.glob("*.v")) if gen_dir.exists() else []

    if not gen_files:
        logger.error("No generated Verilog found in %s. Run 'task verilog' first.", gen_dir)
        print(f"No generated Verilog found in {gen_dir}. Run 'task verilog' first.")
        sys.exit(1)

    sv_files = collect_sv_sources()

    logger.info("Discovered %d generated Verilog files", len(gen_files))
    logger.info("Discovered %d SystemVerilog RTL files", len(sv_files))

    return gen_files, sv_files


def generate_sby(
    gen_files: list[Path],
    sv_files: list[Path],
    prove_depth: int,
    cover_depth: int,
) -> Path:
    """Generate a .sby file for SymbiYosys."""
    sby_dir = Path("build/formal")
    sby_dir.mkdir(parents=True, exist_ok=True)
    sby_path = sby_dir / "top.sby"

    all_files = list(gen_files) + list(sv_files)

    script_lines = []
    for f in all_files:
        if f.suffix == ".sv":
            script_lines.append(f"read -sv -formal {f.name}")
        else:
            script_lines.append(f"read -formal {f.name}")
    script_lines.append("prep -top top")

    files_lines = [str(f) for f in all_files]

    sections = [
        "[tasks]",
        "prove",
        "cover",
        "",
        "[options]",
        "prove: mode prove",
        f"prove: depth {prove_depth}",
        "cover: mode cover",
        f"cover: depth {cover_depth}",
        "",
        "[engines]",
        "smtbmc z3",
        "",
        "[script]",
        *script_lines,
        "",
        "[files]",
        *files_lines,
        "",
    ]

    sby_content = "\n".join(sections)

    sby_path.write_text(sby_content)
    logger.info("Generated .sby file: %s", sby_path)
    logger.debug("SBY content:\n%s", sby_content)

    return sby_path


def run_sby(sby_path: Path) -> bool:
    """Run SymbiYosys on the generated .sby file."""
    for task in ("prove", "cover"):
        print(f"\nRunning formal {task}...")
        logger.info("Running sby task: %s", task)

        cmd = ["sby", "-f", str(sby_path), task]
        logger.debug("Command: %s", " ".join(cmd))

        result = subprocess.run(cmd)
        if result.returncode != 0:
            logger.error("Formal %s FAILED (exit code %d)", task, result.returncode)
            print(f"Formal {task} FAILED")
            return False

        logger.info("Formal %s PASSED", task)
        print(f"Formal {task} PASSED")

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Run formal verification with SymbiYosys")
    parser.add_argument("--prove-depth", type=int, default=20, help="BMC depth for prove (default: 20)")
    parser.add_argument("--cover-depth", type=int, default=260, help="BMC depth for cover (default: 260)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)
    logger.info("Arguments: %s", vars(args))

    gen_files, sv_files = discover_sources()

    print("Formal verification sources:")
    for f in gen_files:
        print(f"  [gen] {f}")
    for f in sv_files:
        print(f"  [rtl] {f}")

    sby_path = generate_sby(gen_files, sv_files, args.prove_depth, args.cover_depth)

    success = run_sby(sby_path)

    if success:
        logger.info("Formal verification completed successfully")
        print("\nAll formal checks PASSED")
    else:
        logger.error("Formal verification failed")

    logger.info("Log file: build/logs/formal.log")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
