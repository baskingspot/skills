{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-parts.follows = "baskingspot/flake-parts";
    baskingspot = {
      url = "github:baskingspot/nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    mattware = {
      url = "github:mattrobenolt/nixpkgs";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [ inputs.baskingspot.flakeModules.base ];

      perSystem =
        {
          pkgs,
          system,
          config,
          ...
        }:
        {
          devShells.default = pkgs.mkShell {
            inputsFrom = [ config.devShells.base ];

            packages = [
              inputs.mattware.packages.${system}.skills-ref
              pkgs.python3
              pkgs.ruff
              pkgs.ty
            ];
          };
        };
    };
}
