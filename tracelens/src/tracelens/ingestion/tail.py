"""tail -f sobre ficheros (Fase 2): soporte a logrotate."""

from __future__ import annotations

import asyncio
import os
from typing import Awaitable, Callable

import aiofiles

OnLine = Callable[[str], Awaitable[None]]


async def tail_file(
    path: str,
    on_line: OnLine,
    stop_event: asyncio.Event,
    poll_interval: float = 1.0,
) -> None:
    """Lee líneas nuevas de un fichero, como `tail -f`.

    Empieza en el final del fichero; termina cuando `stop_event` se pone o
    cuando el fichero desaparece (reabierto si vuelve). Soporta logrotate:
    si el fichero se trunca (tamaño < posición actual) se reinicia desde 0.
    """
    f = None
    pos = 0
    try:
        while not stop_event.is_set():
            if f is None:
                try:
                    f = await aiofiles.open(path, "r", errors="replace")
                    pos = os.stat(path).st_size
                    await f.seek(pos)
                except FileNotFoundError:
                    await asyncio.sleep(poll_interval)
                    continue
            try:
                line = await f.readline()
            except OSError:
                # logrotate: fichero renombrado/eliminado; reabrir.
                await f.close()
                f = None
                continue
            if line:
                pos += len(line)
                await on_line(line)
                continue
            # EOF: detectar truncación/rotación.
            try:
                st = os.stat(path)
            except FileNotFoundError:
                await f.close()
                f = None
                continue
            if st.st_size < pos:
                await f.seek(0)
                pos = 0
            await asyncio.sleep(poll_interval)
    finally:
        if f is not None:
            try:
                await f.close()
            except OSError:
                pass
