from pathlib import Path


def sv_sources() -> list[Path]:
    """Return paths to SystemVerilog source files from this package."""
    pkg_dir = Path(__file__).parent

    # When installed from wheel: rtl/ is inside the package (via force-include)
    rtl_in_pkg = pkg_dir / "rtl"
    if rtl_in_pkg.exists():
        return list(rtl_in_pkg.glob("*.sv"))

    # When running from source (editable install): rtl/ is a sibling of the package
    rtl_sibling = pkg_dir.parent / "rtl"
    if rtl_sibling.exists():
        return list(rtl_sibling.glob("*.sv"))

    return []
