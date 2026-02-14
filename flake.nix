{
  description = "iCE40 FPGA development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python312
            uv
            go-task
            cue
            verilator
            systemc
            gtkwave
            yosys
            sby
            z3
            nextpnr
            icestorm
            ruff
            verible
            git
          ];

          shellHook = ''
            [ ! -d .venv ] && uv sync --quiet
            export SYSTEMC_INCLUDE="${pkgs.systemc}/include"
            export SYSTEMC_LIBDIR="${pkgs.systemc}/lib"
          '';
        };
      }
    );
}
