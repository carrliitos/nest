from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .settings import (
  FeatureFlags,
  RadioSettings,
  RunSettings,
  Settings,
  SwarmSettings,
  VisionSettings,
)


def _project_root() -> Path:
  # Assumes this file is at: src/config/__init__.py
  # project root is two levels up from src/
  return Path(__file__).resolve().parents[2]


def load_settings_from_env(
  *,
  mode: str,
  dry_run: bool,
  channel: Optional[str],
  channels: Optional[list[str]],
  vision: bool,
  control: bool,
  waypoints: bool,
  log_level: Optional[str] = None,
) -> Settings:
  """
  Single source of truth for config loading.
  Later we need to extend this to merge yaml + env + CLI.
  """
  load_dotenv()  # ONLY here (not in drones/vision/swarm modules)

  root = _project_root()
  logs_dir = Path(os.getenv("NEST_LOGS_DIR", str(root / "logs")))
  data_dir = Path(os.getenv("NEST_DATA_DIR", str(root / "data")))
  cache_dir = Path(os.getenv("NEST_CACHE_DIR", str(root / "cache")))

  # Radio URIs
  # Example:
  #   RADIO_CHANNEL_7=radio://0/7/2M/E7E7E7E707
  #   RADIO_CHANNEL_8=radio://0/8/2M/E7E7E7E708
  #   RADIO_CHANNEL_9=radio://0/9/2M/E7E7E7E709
  uri_by_channel = {
    "7": os.getenv("RADIO_CHANNEL_7", "").strip(),
    "8": os.getenv("RADIO_CHANNEL_8", "").strip(),
    "9": os.getenv("RADIO_CHANNEL_9", "").strip(),
  }

  run = RunSettings(
    project_root=root,
    logs_dir=logs_dir,
    data_dir=data_dir,
    cache_dir=cache_dir,
    log_level=(log_level or os.getenv("NEST_LOG_LEVEL", "INFO")).upper(),
  )

  radio = RadioSettings(uri_by_channel=uri_by_channel)

  swarm = SwarmSettings(
    enabled=(mode == "swarm"),
    channels=channels if mode == "swarm" else None,
  )

  # Vision inputs
  cam_index_env = os.getenv("NEST_CAMERA_INDEX", "").strip()
  camera_index = int(cam_index_env) if cam_index_env else None
  camera_url = os.getenv("NEST_CAMERA_URL", "").strip() or None

  vision_settings = VisionSettings(
    enabled=bool(vision),
    control_enabled=bool(control),
    camera_index=camera_index,
    camera_url=camera_url,
    aruco_dict_name=os.getenv("NEST_ARUCO_DICT", "DICT_4X4_50"),
    marker_size_m=float(os.getenv("NEST_MARKER_SIZE_M", "0.040")),
    show_window=os.getenv("NEST_VISION_SHOW_WINDOW", "1") not in {"0", "false", "False"},
  )

  features = FeatureFlags(waypoints=bool(waypoints))

  # Resolve URI (for radio mode)
  uri: Optional[str] = None
  if mode == "radio":
    if not channel:
      raise ValueError("mode=radio requires channel")
    uri = radio.uri_by_channel.get(str(channel), "")
    uri = uri.strip() or None
    if not dry_run and not uri:
      raise ValueError(f"No URI configured for channel={channel}. Set RADIO_CHANNEL_{channel} in .env")

  # UDP mode: URI might come from env; keep simple for now.
  if mode == "udp":
    uri = os.getenv("CF_URI_UDP", "").strip() or None
    if not dry_run and not uri:
      raise ValueError("No CF_URI_UDP configured for udp mode.")

  return Settings(
    mode=mode,
    dry_run=bool(dry_run),
    run=run,
    radio=radio,
    swarm=swarm,
    vision=vision_settings,
    features=features,
    uri=uri,
  )
