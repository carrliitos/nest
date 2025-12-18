from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class RunSettings:
  project_root: Path
  logs_dir: Path
  data_dir: Path
  cache_dir: Path
  log_level: str = "INFO"


@dataclass(frozen=True)
class RadioSettings:
  # Map "7"/"8"/"9" -> Crazyflie URI string
  uri_by_channel: Dict[str, str]


@dataclass(frozen=True)
class SwarmSettings:
  enabled: bool = False
  channels: Optional[List[str]] = None  # e.g., ["7", "8", "9"]


@dataclass(frozen=True)
class VisionSettings:
  enabled: bool = False
  control_enabled: bool = False

  camera_index: Optional[int] = None
  camera_url: Optional[str] = None

  aruco_dict_name: str = "DICT_4X4_50"
  marker_size_m: float = 0.040
  show_window: bool = True


@dataclass(frozen=True)
class FeatureFlags:
  waypoints: bool = False


@dataclass(frozen=True)
class Settings:
  mode: str      # "udp" | "radio" | "swarm"
  dry_run: bool

  run: RunSettings
  radio: RadioSettings
  swarm: SwarmSettings
  vision: VisionSettings
  features: FeatureFlags

  # Resolved connection target (if applicable)
  uri: Optional[str] = None
