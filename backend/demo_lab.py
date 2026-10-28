"""Real MCP client sessions for ToolLens's isolated demonstration servers.

The async context manager is entered and exited in one owner task, avoiding
cross-task anyio cancel-scope errors across FastAPI requests.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DEMOS = ROOT / "demos"
DATA = ROOT / "data" / "lab"
IMAGE = "toollens-mcp-lab:1"
SPECS = {
    "documents_risky": ("Not ve dosya yönetimi", "risky", "documents", "Yol sınırı eksikliği ve yanıltıcı araç açıklaması içeren gerçek not sunucusu."),
    "documents_fixed": ("Not ve dosya yönetimi", "fixed", "documents", "Notları izin verilen klasörde saklayan, okuyan ve arayan düzeltilmiş sürüm."),
    "calculator_risky": ("Hesaplama aracı", "risky", "calculator", "Girdiyi Python ifadesi olarak çalıştıran kasıtlı açıklı hesaplayıcı; yalnız Docker."),
    "calculator_fixed": ("Hesaplama aracı", "fixed", "calculator", "Yalnız aritmetik AST düğümlerini değerlendiren hesaplayıcı."),
}


class LabError(RuntimeError):
    pass


def _spec(demo_id: str) -> tuple[str, str, str, str]:
    if demo_id not in SPECS:
        raise LabError("Bilinmeyen MCP laboratuvarı.")
    return SPECS[demo_id]


def read_source(demo_id):
    _spec(demo_id)
    path=DEMOS/demo_id/'server.py'
    content=path.read_text(encoding='utf-8')
    return {'path':demo_id+'/server.py','content':content,'line_count':len(content.splitlines())}


def _docker_ready() -> dict[str, Any]:
    from .environment import docker_binary
    binary = docker_binary()
    result = {"installed": bool(binary), "running": False, "image_ready": False}
    if not binary:
        return result
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        info = subprocess.run([binary, "info", "--format", "{{.ServerVersion}}"], capture_output=True, timeout=5, creationflags=flags)
        result["running"] = info.returncode == 0
        if result["running"]:
            image = subprocess.run([binary, "image", "inspect", IMAGE], capture_output=True, timeout=5, creationflags=flags)
            result["image_ready"] = image.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        pass
    return result


def _safe_python() -> str:
    candidate = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(candidate) if candidate.is_file() else sys.executable


@dataclass
class LiveSession:
    demo_id: str
    commands: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: asyncio.Task | None = None
    ready: asyncio.Future | None = None
    status: str = "starting"
    tools: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    container_name: str | None = None
    error: str | None = None


_sessions: dict[str, LiveSession] = {}


def list_demos() -> list[dict[str, Any]]:
    docker = _docker_ready()
    records = []
    for demo_id, (name, variant, kind, description) in SPECS.items():
        live = _sessions.get(demo_id)
        risky = variant == "risky"
        ready = not risky or bool(docker["running"] and docker["image_ready"])
        records.append({"id": demo_id, "name": name, "variant": variant, "kind": kind,
                        "description": description, "requires_docker": risky,
                        "available": ready, "status": live.status if live else "stopped",
                        "tools": live.tools if live else [], "path": str(DEMOS / demo_id),
                        "history": live.history[-20:] if live else [],
                        "docker": docker, "error": live.error if live else None,
                        "message": "" if ready else "Docker çalışır durumda ve toollens-mcp-lab:1 imajı hazır olmalı. Riskli sunucu bilgisayarda doğrudan başlatılmaz."})
    return records


def _launch(demo_id: str) -> tuple[str, list[str], dict[str, str], str | None]:
    _, variant, kind, _ = _spec(demo_id)
    source = (DEMOS / demo_id).resolve()
    if not (source / "server.py").is_file():
        raise LabError("Laboratuvar kaynak dosyası bulunamadı.")
    lab_data = DATA / kind
    documents = lab_data / "documents"
    documents.mkdir(parents=True, exist_ok=True)
    if variant == "risky":
        docker = _docker_ready()
        if not docker["running"] or not docker["image_ready"]:
            raise LabError("Riskli MCP yalnız Docker laboratuvarında başlatılır. Docker veya laboratuvar imajı hazır değil.")
        name = "toollens-lab-" + uuid4().hex[:12]
        args = ["run", "--interactive", "--rm", "--name", name,
                "--label", "toollens.lab=true", "--network", "none", "--read-only",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--pids-limit", "64", "--cpus", "1", "--memory", "256m",
                "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=32m",
                "--mount", f"type=bind,source={source},target=/app,readonly",
                "--mount", f"type=bind,source={lab_data.resolve()},target=/lab",
                IMAGE]
        return __import__("backend.environment",fromlist=["docker_binary"]).docker_binary(), args, {}, name
    return _safe_python(), [str(source / "server.py")], {
        "TOOLLENS_DOCUMENTS": str(documents.resolve()), "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }, None


async def _serve(live: LiveSession) -> None:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        command, args, env, container_name = _launch(live.demo_id)
        live.container_name = container_name
        params = StdioServerParameters(command=command, args=args, env=env,
                                       cwd=str(DEMOS / live.demo_id))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as client:
                await asyncio.wait_for(client.initialize(), 20)
                catalog = await asyncio.wait_for(client.list_tools(), 15)
                live.tools = [tool.model_dump(mode="json") for tool in catalog.tools]
                live.status = "running"
                if live.ready and not live.ready.done():
                    live.ready.set_result(True)
                while True:
                    op, payload, future = await live.commands.get()
                    if op == "stop":
                        live.status = "stopping"
                        if not future.done():
                            future.set_result(True)
                        break
                    try:
                        if op == "tools":
                            catalog = await asyncio.wait_for(client.list_tools(), 10)
                            live.tools = [tool.model_dump(mode="json") for tool in catalog.tools]
                            value = live.tools
                        else:
                            result = await asyncio.wait_for(client.call_tool(payload["name"], payload["arguments"]), 15)
                            value = {"id": uuid4().hex, "demo_id": live.demo_id,
                                     "tool": payload["name"], "arguments": payload["arguments"],
                                     "result": result.model_dump(mode="json"), "is_error": bool(result.isError),
                                     "evidence_kind": "mcp_protocol_response",
                                     "note": "Bu kayıt gerçek MCP yanıtıdır. Dosya veya ağ yan etkisini tek başına kanıtlamaz."}
                            live.history.append(value)
                            live.history[:] = live.history[-50:]
                        if not future.done():
                            future.set_result(value)
                    except Exception:
                        if not future.done():
                            future.set_exception(LabError("MCP çağrısı tamamlanamadı veya süre sınırını aştı."))
    except asyncio.CancelledError:
        raise
    except Exception as error:
        live.error = f"MCP oturumu açılamadı ({type(error).__name__}). SDK kurulumunu ve sunucu ortamını kontrol edin."
        if live.ready and not live.ready.done():
            live.ready.set_exception(LabError(live.error))
    finally:
        live.status = "stopped"
        if live.container_name and __import__("backend.environment",fromlist=["docker_binary"]).docker_binary():
            await asyncio.to_thread(subprocess.run, [__import__("backend.environment",fromlist=["docker_binary"]).docker_binary(), "rm", "--force", live.container_name], capture_output=True, timeout=10)
        while not live.commands.empty():
            _, _, pending = live.commands.get_nowait()
            if not pending.done():
                pending.set_exception(LabError("MCP oturumu kapandı."))


async def start_demo(demo_id: str) -> dict[str, Any]:
    _spec(demo_id)
    previous = _sessions.get(demo_id)
    if previous and previous.status in ("starting", "running"):
        raise LabError("Bu MCP laboratuvarı zaten çalışıyor.")
    # Validate policy before spawning anything.
    if SPECS[demo_id][1] == "risky":
        docker = await asyncio.to_thread(_docker_ready)
        if not docker["running"] or not docker["image_ready"]:
            raise LabError("Riskli sunucu için Docker ve toollens-mcp-lab:1 imajı gerekir. Bilgisayarda doğrudan çalıştırılmayacak.")
    live = LiveSession(demo_id)
    live.ready = asyncio.get_running_loop().create_future()
    _sessions[demo_id] = live
    live.task = asyncio.create_task(_serve(live), name="toollens-" + demo_id)
    try:
        await asyncio.wait_for(asyncio.shield(live.ready), 30)
    except Exception:
        live.task.cancel()
        try:
            await live.task
        except BaseException:
            pass
        raise LabError(live.error or "MCP başlatma süresi aşıldı.") from None
    return next(item for item in await asyncio.to_thread(list_demos) if item["id"] == demo_id)


async def _request(demo_id: str, op: str, payload: dict[str, Any]) -> Any:
    _spec(demo_id)
    live = _sessions.get(demo_id)
    if live is None or live.status != "running" or live.task is None or live.task.done():
        raise LabError("Önce MCP sunucusunu başlatın.")
    future = asyncio.get_running_loop().create_future()
    await live.commands.put((op, payload, future))
    try:
        return await asyncio.wait_for(future, 20)
    except asyncio.TimeoutError:
        raise LabError("MCP isteğinin süresi aşıldı.") from None


async def list_tools(demo_id: str) -> list[dict[str, Any]]:
    return await _request(demo_id, "tools", {})


async def call_tool(demo_id: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    live = _sessions.get(demo_id)
    if live is None or name not in {tool["name"] for tool in live.tools}:
        raise LabError("Araç çalışan MCP sunucusunun listesinde yok.")
    if not isinstance(arguments, dict) or len(json.dumps(arguments).encode()) > 64_000:
        raise LabError("Araç argümanları geçersiz veya çok büyük.")
    return await _request(demo_id, "call", {"name": name, "arguments": arguments})


async def stop_demo(demo_id: str) -> dict[str, Any]:
    _spec(demo_id)
    live = _sessions.get(demo_id)
    if live and live.task and not live.task.done():
        if live.status == "running":
            try:
                await _request(demo_id, "stop", {})
                await asyncio.wait_for(asyncio.shield(live.task), 10)
            except Exception:
                live.task.cancel()
        else:
            live.task.cancel()
        try:
            await live.task
        except asyncio.CancelledError:
            pass
    return {"id": demo_id, "status": "stopped"}


async def close_all() -> None:
    for demo_id in list(_sessions):
        await stop_demo(demo_id)


def prepare_lab_image() -> dict[str, Any]:
    """Explicit setup operation, not automatically triggered by opening a page."""
    docker = __import__("backend.environment",fromlist=["docker_binary"]).docker_binary()
    if not docker:
        raise LabError("Docker kurulumu bulunamadı.")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        result = subprocess.run([docker, "build", "--tag", IMAGE, str(DEMOS)], env=__import__("backend.environment",fromlist=["docker_environment"]).docker_environment(),
                                capture_output=True, text=True, timeout=300, creationflags=flags)
    except subprocess.TimeoutExpired:
        raise LabError("Laboratuvar imajı hazırlama süresi aşıldı.") from None
    if result.returncode:
        raise LabError("Docker laboratuvar imajı hazırlanamadı. Docker terminal günlüğünü kontrol edin.")
    return {"image": IMAGE, "ready": True}
