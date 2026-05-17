from __future__ import annotations

import subprocess


class BrowserRunningError(RuntimeError):
    def __init__(self, running: list[str]) -> None:
        names = ", ".join(running)
        super().__init__(f"Quit these browsers before continuing: {names}")
        self.running = running


def running_browsers(names: list[str] | None = None) -> list[str]:
    """Return the requested browser process names that are currently running."""
    names = names or ["Firefox", "Safari"]
    running: list[str] = []
    for name in names:
        result = subprocess.run(
            ["pgrep", "-x", name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            running.append(name)
    return running


def require_browsers_stopped(names: list[str] | None = None) -> None:
    running = running_browsers(names)
    if running:
        raise BrowserRunningError(running)
