from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Optional, Sequence
from config import load_settings_from_env

_EXTRA_TOKENS = {"vision", "control", "waypoint", "waypoints"}

@dataclass(frozen=True)
class CliArgs:
  # connection mode
  mode: str  # "udp" | "radio" | "swarm"

  # radio specifics
  channel: Optional[str] = None     # for mode="radio"
  channels: Optional[List[str]] = None  # for mode="swarm"

  # feature toggles
  vision: bool = False
  control: bool = False
  waypoints: bool = False

  # runtime toggles
  dry_run: bool = False
  log_level: Optional[str] = None

def _parse_extras(extras: Sequence[str]) -> tuple[bool, bool, bool]:
  """
  Accepts trailing tokens: vision control waypoint
  and turns them into booleans.
  """
  s = {e.lower() for e in extras}
  vision = "vision" in s
  control = "control" in s
  waypoints = ("waypoint" in s) or ("waypoints" in s)

  if control and not vision:
    raise ValueError("`control` requires `vision` (click-to-go needs vision).")

  return vision, control, waypoints


def build_parser() -> argparse.ArgumentParser:
  p = argparse.ArgumentParser(
    prog="fly",
    description="NEST flight CLI (refactor target: thin CLI -> core runner).",
  )

  p.add_argument("--dry-run", action="store_true", help="Run without hardware/camera.")
  p.add_argument("--log-level", default=None, help="Override log level (e.g., INFO, DEBUG).")

  sub = p.add_subparsers(dest="mode", required=True)

  # udp
  p_udp = sub.add_parser("udp", help="Connect via UDP (URI from config).")
  p_udp.add_argument("--vision", action="store_true", help="Enable vision subsystem.")
  p_udp.add_argument("--control", action="store_true", help="Enable click-to-go (requires vision).")
  p_udp.add_argument("--waypoints", action="store_true", help="Enable waypoint logging.")
  p_udp.add_argument("extras", nargs="*", help="Backward compat tokens: vision control waypoint")

  # radio
  p_radio = sub.add_parser("radio", help="Connect via radio using a channel key (e.g., 7/8/9).")
  p_radio.add_argument("channel", help="Radio channel key (e.g., 7, 8, 9).")
  p_radio.add_argument("--vision", action="store_true", help="Enable vision subsystem.")
  p_radio.add_argument("--control", action="store_true", help="Enable click-to-go (requires vision).")
  p_radio.add_argument("--waypoints", action="store_true", help="Enable waypoint logging.")
  p_radio.add_argument("extras", nargs="*", help="Backward compat tokens: vision control waypoint")

  # swarm
  p_swarm = sub.add_parser("swarm", help="Connect to a swarm via multiple radio channels.")
  p_swarm.add_argument("channels", nargs="+", help="Radio channel keys (e.g., 7 8 9).")
  p_swarm.add_argument("--vision", action="store_true", help="Enable vision subsystem.")
  p_swarm.add_argument("--control", action="store_true", help="Enable click-to-go (requires vision).")
  p_swarm.add_argument("--waypoints", action="store_true", help="Enable waypoint logging.")
  p_swarm.add_argument("extras", nargs="*", help="Backward compat tokens: vision control waypoint")

  return p

def parse_args(argv: Optional[Sequence[str]] = None) -> CliArgs:
  p = build_parser()
  ns = p.parse_args(argv)

  # Normalize extras: allow either flags OR tokens.
  extras = getattr(ns, "extras", []) or []
  # Filter extras to only known tokens (ignore random junk)
  token_extras = [e for e in extras if e.lower() in _EXTRA_TOKENS]

  token_vision, token_control, token_waypoints = _parse_extras(token_extras) if token_extras else (False, False, False)

  vision = bool(getattr(ns, "vision", False) or token_vision)
  control = bool(getattr(ns, "control", False) or token_control)
  waypoints = bool(getattr(ns, "waypoints", False) or token_waypoints)

  if control and not vision:
    raise SystemExit("Error: --control requires --vision (click-to-go needs vision).")

  mode = ns.mode
  if mode == "udp":
    return CliArgs(mode="udp",
                   vision=vision,
                   control=control,
                   waypoints=waypoints,
                   dry_run=ns.dry_run,
                   log_level=ns.log_level)

  if mode == "radio":
    return CliArgs(mode="radio",
                   channel=str(ns.channel),
                   vision=vision,
                   control=control,
                   waypoints=waypoints,
                   dry_run=ns.dry_run,
                   log_level=ns.log_level)

  if mode == "swarm":
    return CliArgs(mode="swarm",
                   channels=[str(c) for c in ns.channels],
                   vision=vision,
                   control=control,
                   waypoints=waypoints,
                   dry_run=ns.dry_run,
                   log_level=ns.log_level)

  raise SystemExit(f"Unknown mode: {mode}")

def main(argv=None) -> int:
  args = parse_args(argv)

  settings = load_settings_from_env(
    mode=args.mode,
    dry_run=args.dry_run,
    channel=args.channel,
    channels=args.channels,
    vision=args.vision,
    control=args.control,
    waypoints=args.waypoints,
    log_level=args.log_level,
  )

  from core.runner import run
  return int(run(settings))

if __name__ == "__main__":
  raise SystemExit(main())
