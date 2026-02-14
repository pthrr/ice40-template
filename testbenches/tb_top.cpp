#include <systemc.h>
#include "Vtop.h"
#include "Vtop___024root.h"
#include "verilated_vcd_sc.h"

SC_MODULE(tb_top) {
    sc_clock clk{"clk", 10, SC_NS, 0.5};
    sc_signal<bool> rst{"rst"};

    Vtop *dut;

    uint32_t prev_count;
    int errors;
    int cycles;

    void run() {
        // Hold reset for several clock cycles
        rst.write(true);
        for (int i = 0; i < 4; i++) {
            wait(clk.posedge_event());
        }
        rst.write(false);

        // Wait for first posedge after reset release
        wait(clk.posedge_event());
        wait(SC_ZERO_TIME);

        // Sample initial count after reset
        prev_count = dut->rootp->top__DOT__count;
        errors = 0;
        cycles = 0;

        while (cycles < 1000) {
            wait(clk.posedge_event());
            wait(SC_ZERO_TIME);

            uint32_t cur_count = dut->rootp->top__DOT__count;
            uint32_t expected = (prev_count + 1) & 0x00FFFFFF;

            if (cur_count != expected) {
                printf("FAIL @ cycle %d: count=%u expected=%u\n",
                       cycles, cur_count, expected);
                errors++;
                if (errors > 10) break;
            }

            prev_count = cur_count;
            cycles++;
        }

        if (errors == 0) {
            printf("PASS: counter incremented correctly for %d cycles\n", cycles);
        } else {
            printf("FAIL: %d errors detected\n", errors);
        }

        sc_stop();
    }

    SC_CTOR(tb_top) : dut(nullptr), prev_count(0), errors(0), cycles(0) {
        dut = new Vtop{"dut"};
        dut->clk(clk);
        dut->rst(rst);

        SC_THREAD(run);
    }

    ~tb_top() {
        delete dut;
    }
};

int sc_main(int argc, char **argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    tb_top tb{"tb_top"};

    // Tracing must be set up after elaboration
    sc_start(SC_ZERO_TIME);

    VerilatedVcdSc *vcd = new VerilatedVcdSc;
    tb.dut->trace(vcd, 99);
    vcd->open("build/sim/tb_top.vcd");

    sc_start();

    vcd->close();
    delete vcd;

    return tb.errors != 0;
}
