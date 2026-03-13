"""SteamCMD-based downloader for Workshop items."""

import asyncio
import shutil
import platform
from pathlib import Path
from typing import Optional, AsyncIterator


STEAMCMD_PATHS = {
    "Darwin": [
        "/usr/local/bin/steamcmd.sh",
        "/opt/homebrew/bin/steamcmd.sh",
        Path.home() / "steamcmd" / "steamcmd.sh",
        "/usr/local/bin/steamcmd",
        "/opt/homebrew/bin/steamcmd",
    ],
    "Linux": [
        "/usr/bin/steamcmd",
        "/usr/games/steamcmd",
        Path.home() / "steamcmd" / "steamcmd.sh",
    ],
    "Windows": [
        Path("C:/steamcmd/steamcmd.exe"),
        Path.home() / "steamcmd" / "steamcmd.exe",
    ],
}

# Lines that indicate a successful download
SUCCESS_MARKERS = [
    "Success. Downloaded item",
    "workshop_download_item_finished",
]

# Lines that indicate a failure
FAILURE_MARKERS = [
    "ERROR!",
    "Download item",
    "Failed to download",
    "Timeout downloading",
]


def find_steamcmd() -> Optional[str]:
    """Find steamcmd binary on the system."""
    # On macOS prefer steamcmd.sh
    if platform.system() == "Darwin":
        found = shutil.which("steamcmd.sh") or shutil.which("steamcmd")
    else:
        found = shutil.which("steamcmd")
    if found:
        return found

    system = platform.system()
    for path in STEAMCMD_PATHS.get(system, []):
        if Path(path).exists():
            return str(path)
    return None


def get_install_instructions() -> str:
    system = platform.system()
    if system == "Darwin":
        return "Install via Homebrew: brew install steamcmd  (runs as steamcmd.sh)"
    elif system == "Linux":
        return (
            "Install via package manager:\n"
            "  Ubuntu/Debian: sudo apt install steamcmd\n"
            "  Or download from: https://developer.valvesoftware.com/wiki/SteamCMD"
        )
    else:
        return "Download from: https://developer.valvesoftware.com/wiki/SteamCMD"


def build_steamcmd_args(
    cmd: str,
    app_id: str,
    workshop_ids: list[str],
    output_dir: str,
    username: str = "anonymous",
) -> list[str]:
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    args = [
        cmd,
        "+@ShutdownOnFailedCommand", "1",
        "+@NoPromptForPassword", "1",
        "+force_install_dir", str(output_path),
        "+login", username,
    ]
    for wid in workshop_ids:
        args += ["+workshop_download_item", app_id, wid]
    args.append("+quit")
    return args


async def stream_download(
    app_id: str,
    workshop_ids: list[str],
    output_dir: str,
    steamcmd_path: Optional[str] = None,
    username: str = "anonymous",
) -> AsyncIterator[str]:
    """
    Async generator that yields SteamCMD output lines.
    Yields strings — each is a line of output.
    Final line is either "SUCCESS:<path>" or "ERROR:<message>".
    """
    cmd = steamcmd_path or find_steamcmd()
    if not cmd:
        yield f"ERROR:{get_install_instructions()}"
        return

    args = build_steamcmd_args(cmd, app_id, workshop_ids, output_dir, username)

    output_path = Path(output_dir).expanduser().resolve()
    content_path = output_path / "steamapps" / "workshop" / "content" / app_id

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        assert proc.stdout is not None
        downloaded_count = 0

        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if not line:
                continue
            yield line

            if any(m in line for m in SUCCESS_MARKERS):
                downloaded_count += 1

        await proc.wait()

        if proc.returncode == 0 or downloaded_count > 0:
            yield f"SUCCESS:{content_path}"
        else:
            yield f"ERROR:SteamCMD exited with code {proc.returncode}"

    except asyncio.CancelledError:
        yield "ERROR:Download cancelled"
    except Exception as e:
        yield f"ERROR:{e}"
