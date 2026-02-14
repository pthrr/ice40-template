module counter #(
    parameter int WIDTH = 8
) (
    input  logic             clk,
    input  logic             rst,
    input  logic             en,
    output logic [WIDTH-1:0] count
);

  always_ff @(posedge clk) begin
    if (rst) count <= '0;
    else if (en) count <= count + 1'b1;
  end

`ifdef FORMAL
  reg f_past_valid = 0;
  always_ff @(posedge clk) f_past_valid <= 1;

  // After reset, counter must be zero
  always_ff @(posedge clk) if (f_past_valid && $past(rst)) assert (count == '0);

  // When enabled and not in reset, counter increments
  always_ff @(posedge clk)
    if (f_past_valid && !$past(rst) && $past(en))
      assert (count == $past(count) + 1'b1);

  // When disabled and not in reset, counter holds
  always_ff @(posedge clk)
    if (f_past_valid && !$past(rst) && !$past(en))
      assert (count == $past(count));

  // Cover: counter reaches max value
  always_ff @(posedge clk) cover (count == {WIDTH{1'b1}});
`endif

endmodule
