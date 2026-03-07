#!/usr/bin/env python3
import logging
import sys
from importlib.metadata import entry_points
from pathlib import Path

logger = logging.getLogger(__name__)


def setup_logging(name: str, verbose: bool = False) -> None:
    """Configure logging with console and file handlers."""
    log_dir = Path("build/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{name}.log"

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
    logger.info("%s session started", name.capitalize())


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
