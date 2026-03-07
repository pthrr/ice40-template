import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ice40_template"))

from amaranth.back import verilog
from top import Top


def test_top_elaborates() -> None:
    dut = Top(counter_width=8)
    output = verilog.convert(dut, ports=[], emit_src=True)
    assert "module top" in output
    print("✓ Top elaborates")


if __name__ == "__main__":
    test_top_elaborates()
    print("\n✓ All tests passed")
