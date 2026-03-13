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

SUCCESS_MARKERS = [
    "Success. Downloaded item",
    "workshop_download_item_finished",
]

# Prompts that require interactive input via stdin
STEAM_GUARD_MARKERS = [
    "Steam Guard code:",
    "Two-factor code:",
    "Steam Mobile Authenticator code:",
]

PASSWORD_MARKERS = [
    "password:",
    "Password:",
    "Enter password",
]

CACHED_LOGIN_MARKERS = [
    "Logging in using cached credentials",
]

# Module-level queue for sending input to the active SteamCMD process
_input_queue: asyncio.Queue[str] = asyncio.Queue()


async def send_steamcmd_input(text: str) -> None:
    """Send a line of input to the active SteamCMD process (password or Steam Guard code)."""
    await _input_queue.put(text)


def find_steamcmd() -> Optional[str]:
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
    Special prefixes on the final line:
      SUCCESS:<path>
      ERROR:<message>
      STEAMGUARD:  — frontend should prompt the user for a code, then call send_steamcmd_input()
    """
    cmd = steamcmd_path or find_steamcmd()
    if not cmd:
        yield f"ERROR:{get_install_instructions()}"
        return

    args = build_steamcmd_args(cmd, app_id, workshop_ids, output_dir, username)

    output_path = Path(output_dir).expanduser().resolve()
    content_path = output_path / "steamapps" / "workshop" / "content" / app_id

    # Drain any leftover inputs from a previous session
    while not _input_queue.empty():
        _input_queue.get_nowait()

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            stdin=asyncio.subprocess.PIPE,
        )

        assert proc.stdout is not None
        assert proc.stdin is not None
        downloaded_count = 0
        error_lines: list[str] = []

        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if not line:
                continue
            yield line

            if any(m in line for m in SUCCESS_MARKERS):
                downloaded_count += 1

            if "ERROR!" in line and "failed" in line.lower():
                error_lines.append(line.strip())

            # Password prompt — cached credentials not found
            if any(marker in line for marker in PASSWORD_MARKERS):
                yield "NEED_PASSWORD:"
                try:
                    pwd = await asyncio.wait_for(_input_queue.get(), timeout=120)
                    proc.stdin.write((pwd + "\n").encode())
                    await proc.stdin.drain()
                except asyncio.TimeoutError:
                    proc.kill()
                    yield "ERROR:Password not provided within 2 minutes"
                    return

            # Steam Guard / 2FA prompt
            if any(marker in line for marker in STEAM_GUARD_MARKERS):
                yield "STEAMGUARD:"
                try:
                    code = await asyncio.wait_for(_input_queue.get(), timeout=120)
                    proc.stdin.write((code + "\n").encode())
                    await proc.stdin.drain()
                except asyncio.TimeoutError:
                    proc.kill()
                    yield "ERROR:Steam Guard code not provided within 2 minutes"
                    return

        await proc.wait()

        if downloaded_count > 0 and not error_lines:
            yield f"SUCCESS:{content_path}"
        else:
            if error_lines:
                msg = error_lines[-1]
                if "No Connection" in msg:
                    msg += " — anonymous login cannot download mods for paid games; enter your Steam username"
                elif "No subscription" in msg:
                    msg += " — your account does not own this game"
                yield f"ERROR:{msg}"
            else:
                yield f"ERROR:SteamCMD exited with code {proc.returncode}"

    except asyncio.CancelledError:
        yield "ERROR:Download cancelled"
    except Exception as e:
        yield f"ERROR:{e}"
