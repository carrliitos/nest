from __future__ import annotations

import json
import logging
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from config.settings import Settings

def _setup_logging(level: str) -> None:
  lvl = getattr(logging, level.upper(), logging.INFO)
  logging.basicConfig(level=lvl, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",)

def _safe_asdict(obj: Any) -> Any:
  """
  Best-effort conversion for writing settings snapshots.
  Works well for dataclasses and Path objects.
  """
  if is_dataclass(obj):
    return {k: _safe_asdict(v) for k, v in asdict(obj).items()}

  if isinstance(obj, dict):
    return {k: _safe_asdict(v) for k, v in obj.items()}

  if isinstance(obj, (list, tuple)):
    return [_safe_asdict(v) for v in obj]

  if isinstance(obj, Path):
    return str(obj)

  return obj

def _write_settings_snapshot(settings: Settings, out_dir: Path) -> None:
  out_dir.mkdir(parents=True, exist_ok=True)
  snapshot_path = out_dir / "settings.json"
  snapshot_path.write_text(json.dumps(_safe_asdict(settings), indent=2), encoding="utf-8")

def run(settings: Settings) -> int:
  """
  Orchestrates the application lifecycle:
    - configure logging
    - create run output directories
    - init drone/swarm/vision subsystems (if enabled)
    - run the UI/scenario loop
    - shutdown cleanly

  Returns:
    0 on success, non-zero on error.
  """
  _setup_logging(settings.run.log_level)
  log = logging.getLogger("core.runner")

  # Always snapshot resolved config for reproducibility.
  _write_settings_snapshot(settings, settings.run.logs_dir)

  if settings.dry_run:
    log.info("Dry-run enabled: skipping hardware + vision initialization.")
    return 0

  drone = None
  drone_logs = None
  swarm = None
  detector = None
  detector_thread = None

  try:
    # Lazy imports so CI/tests can import runner without cflib/cv2 present.
    from drones.drone_connection import DroneConnection
    from drones.drone_log import DroneLogs

    log.info("Initializing drone connection (mode=%s)...", settings.mode)
    drone = DroneConnection(mode=settings.mode, channel=settings.uri or settings.swarm.channels)

    log.info("Initializing telemetry logging...")
    drone_logs = DroneLogs(drone)

    if settings.mode == "swarm":
      from swarm.swarm_command import SwarmCommand

      log.info("Initializing swarm controller...")
      # Adjust constructor args to match your SwarmCommand after relocation.
      swarm = SwarmCommand(channels=settings.swarm.channels)

    if settings.vision.enabled:
      from threading import Thread
      from vision.vision import DetectorRT

      log.info("Starting vision detector thread...")
      detector = DetectorRT(
        # NOTE: These needs to be aligneed with DetectorRT after relocation.
        camera_index=settings.vision.camera_index,
        camera_url=settings.vision.camera_url,
        marker_size_m=settings.vision.marker_size_m,
        aruco_dict_name=settings.vision.aruco_dict_name,
        show_window=settings.vision.show_window,
      )
      detector_thread = Thread(target=detector.run, daemon=True)
      detector_thread.start()

    # Temporary: until old command.py is split, this will live at src/core/command.py
    # and keep the class name Command the same.
    from core.command import Command  # transitional location

    log.info("Launching command/UI loop...")
    cmd = Command(
      drone=drone,
      logs=drone_logs,
      swarm=swarm,
      vision=settings.vision.enabled,
      control=settings.vision.control_enabled,
      waypoint=settings.features.waypoints,
    )

    if detector is not None:
      cmd.set_detector(detector, detector_thread)

    cmd.run()  # blocks until user exit
    log.info("Run completed normally.")
    return 0

  except Exception as e:
    log.exception("Fatal error in runner: %s", e)
    return 1

  finally:
    log.info("Shutting down subsystems...")

    # Vision
    try:
      if detector is not None:
        detector.stop()  # implement if you don’t have it yet
      if detector_thread is not None and detector_thread.is_alive():
        detector_thread.join(timeout=2.0)
    except Exception:
      log.exception("Error during vision shutdown.")

    # Swarm
    try:
      if swarm is not None:
        swarm.close()  # implement/align to SwarmCommand API
    except Exception:
      log.exception("Error during swarm shutdown.")

    # Drone / logs
    try:
      if drone_logs is not None:
        drone_logs.close()  # if you add one; otherwise remove
    except Exception:
      log.exception("Error during log shutdown.")

    try:
      if drone is not None:
        drone.close()  # align to DroneConnection API
    except Exception:
      log.exception("Error during drone shutdown.")
