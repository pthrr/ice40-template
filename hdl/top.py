from typing import Optional

from amaranth import Elaboratable, Instance, Module, Signal
from amaranth.build import Platform
from amaranth.hdl import ClockSignal


class Top(Elaboratable):
    def __init__(self, counter_width: int = 24) -> None:
        self.counter_width = counter_width
        self.led = Signal(name="led")

    def elaborate(self, platform: Optional[Platform]) -> Module:
        m = Module()

        count = Signal(self.counter_width, name="count")

        m.submodules.counter = Instance(
            "counter",
            p_WIDTH=self.counter_width,
            i_clk=ClockSignal(),
            i_rst=0,
            i_en=1,
            o_count=count,
        )

        m.d.comb += self.led.eq(count[-1])

        if platform is not None:
            led_pin = platform.request("led", 0)
            m.d.comb += led_pin.o.eq(self.led)

        return m


if __name__ == "__main__":
    from amaranth.back import verilog

    top = Top()
    output = verilog.convert(top, ports=[top.led], emit_src=True)
    print(output)
