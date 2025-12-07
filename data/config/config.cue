package config

boards: {
	ice40_hx8k_evn: {
		platform: "amaranth_boards.ice40_hx8k_b_evn.ICE40HX8KBEVNPlatform"
		device: {
			family:  "iCE40"
			model:   "iCE40HX8K"
			package: "CT256"
		}
		clock: frequency: 12_000_000
	}
	icebreaker: {
		platform: "amaranth_boards.icebreaker.ICEBreakerPlatform"
		device: {
			family:  "iCE40"
			model:   "iCE40UP5K"
			package: "SG48"
		}
		clock: frequency: 12_000_000
	}
	icestick: {
		platform: "amaranth_boards.icestick.ICEStickPlatform"
		device: {
			family:  "iCE40"
			model:   "iCE40HX1K"
			package: "TQ144"
		}
		clock: frequency: 12_000_000
	}
}

build: {
	verbose:        true
	debug_verilog:  true
	optimize:       "speed"
	yosys_opts: []
	nextpnr_opts: []
}

sim: {
	vcd_output: "build/sim"
}
