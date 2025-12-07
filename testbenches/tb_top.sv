`timescale 1ns / 1ps

module tb_top;
  logic clk;
  logic rst;

  top dut (
      .clk(clk),
      .rst(rst)
  );

  initial begin
    clk = 0;
    rst = 0;
    forever #41.67 clk = ~clk;
  end

  initial begin
    $dumpfile("build/sim/tb_top.vcd");
    $dumpvars(0, tb_top);

    #1000000;

    $display("Simulation complete");
    $finish;
  end
endmodule
