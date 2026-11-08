"""Chat de Telegram con un agente local de Cursor en este PC."""

import asyncio
import json
import os
import re
import subprocess
import time
import urllib.parse
from collections.abc import Mapping

BOT_DIR = os.path.dirname(os.path.abspath(__file__))
PC = os.path.expanduser("~")
ESCRITORIO = os.path.join(PC, "Desktop")
KEY_FILE = os.path.join(BOT_DIR, "cursor_api_key.txt")
SESSION_FILE = os.path.join(BOT_DIR, "cursor_session.json")
BRIDGE_FILE = os.path.join(BOT_DIR, "cursor_bridge.json")
TAREA_FILE = os.path.join(BOT_DIR, "cursor_tarea.json")
BRIDGE_LOG = os.path.join(BOT_DIR, "cursor_bridge.log")
MODELO = os.environ.get("CURSOR_MODEL", "composer-2.5").strip() or "composer-2.5"
_TERMINALES = {"finished", "error", "cancelled", "expired"}

CONTEXTO = (
    "Eres el agente de Cursor de Aarón. Te escribe desde Telegram para que actúes "
    "en este PC, no para que te limites a explicar.\n"
    f"El bot está en {BOT_DIR} (bot.py). El escritorio está en {ESCRITORIO}. "
    f"Su carpeta de usuario es {PC}. Con la terminal puedes ir a cualquier disco "
    "(C:, D:, Z: y el resto) cuando lo pida: el bot, el escritorio o el resto del ordenador.\n"
    "Haz el cambio y, al final, di qué has tocado y cómo comprobarlo. "
    "Responde en español, corto, en texto plano.\n"
    "No pegues tokens, contraseñas ni claves.\n"
    "No mates el python que ejecuta bot.py: ese proceso es este chat de Telegram. "
    "Si tocas código del bot que hay que recargar, al terminar ejecuta en el PC:\n"
    f"py \"{os.path.join(BOT_DIR, 'solicitar_reinicio_bot.py')}\"\n"
    "Eso hace que el propio bot.py se reinicie (no lo mates desde fuera).\n"
    "No pares el proceso de main.py salvo que te lo pida con esas palabras."
)

_estado = {
    "client": None,
    "agent": None,
    "run": None,
    "busy": False,
    "olvidar": False,
    "bridge_pid": None,
    "retomando": False,
}
_puentes_abiertos = []


class Ocupado(Exception):
    """Ya hay una petición de Cursor en marcha."""


def hay_clave():
    return bool(_leer_clave())


def texto_sin_clave():
    return (
        "Falta la clave de Cursor en este PC.\n\n"
        "1. Entra en https://cursor.com/dashboard/integrations y crea una API key.\n"
        "2. Pega aquí solo la clave, en un mensaje, o guárdala en una sola línea dentro de:\n"
        f"{KEY_FILE}\n"
        "3. Si la guardas en el archivo, pulsa Reiniciar y vuelve a escribirme."
    )


def guardar_clave_si_viene(texto):
    """Si el mensaje es solo la API key, la guarda y no la reenvía al agente."""
    linea = (texto or "").strip().strip('"').strip("'")
    if not re.fullmatch(r"(?:crsr_|grok_)[A-Za-z0-9_\-]{20,}", linea):
        return False
    with open(KEY_FILE, "w", encoding="utf-8") as archivo:
        archivo.write(linea)
    return True


def trocear(texto, limite=3800):
    limpio = (texto or "").strip() or "Listo."
    partes = []
    while limpio:
        if len(limpio) <= limite:
            partes.append(limpio)
            break
        corte = limpio.rfind("\n", 0, limite)
        if corte < limite // 2:
            corte = limite
        partes.append(limpio[:corte].rstrip())
        limpio = limpio[corte:].lstrip("\n")
    return partes


def _log(mensaje, error=False):
    try:
        import bot
        bot.log_sistema(mensaje, is_error=error)
    except Exception:
        print(mensaje)


def _leer_clave():
    entorno = os.environ.get("CURSOR_API_KEY", "").strip()
    if entorno:
        return entorno
    try:
        with open(KEY_FILE, "r", encoding="utf-8") as archivo:
            linea = archivo.read().strip()
    except OSError:
        return ""
    if not linea or linea.startswith("#"):
        return ""
    return linea


def _leer_sesion():
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if isinstance(datos, dict) and datos.get("agent_id"):
            return datos
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _guardar_sesion(agent_id, briefed):
    with open(SESSION_FILE, "w", encoding="utf-8") as archivo:
        json.dump({"agent_id": agent_id, "briefed": bool(briefed)}, archivo)


def _borrar_sesion():
    try:
        os.remove(SESSION_FILE)
    except OSError:
        pass


def _escribir_json(ruta, datos):
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo)
        archivo.flush()
        os.fsync(archivo.fileno())
    os.replace(temporal, ruta)


def _leer_json(ruta):
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if isinstance(datos, dict):
            return datos
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _proceso_vivo(pid):
    try:
        numero = int(pid)
    except (TypeError, ValueError):
        return False
    if numero <= 0:
        return False
    if os.name == "nt":
        import ctypes

        acceso = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION
        handle = ctypes.windll.kernel32.OpenProcess(acceso, False, numero)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(numero, 0)
    except OSError:
        return False
    return True


def _leer_puente():
    datos = _leer_json(BRIDGE_FILE)
    if datos.get("url") and datos.get("token") and datos.get("pid"):
        return datos
    return {}


def _guardar_puente(url, token, pid):
    _escribir_json(BRIDGE_FILE, {"url": url, "token": token, "pid": int(pid)})
    _estado["bridge_pid"] = int(pid)


def _leer_tarea():
    datos = _leer_json(TAREA_FILE)
    if datos.get("pedido") or datos.get("run_id"):
        return datos
    return {}


def _guardar_tarea(datos):
    _escribir_json(
        TAREA_FILE,
        {
            "agent_id": datos.get("agent_id") or "",
            "run_id": datos.get("run_id") or "",
            "chat_id": datos.get("chat_id"),
            "message_id": datos.get("message_id"),
            "pedido": datos.get("pedido") or "",
            "bridge_pid": datos.get("bridge_pid"),
        },
    )


def _borrar_tarea():
    try:
        os.remove(TAREA_FILE)
    except OSError:
        pass


def tarea_en_curso():
    return dict(_leer_tarea())


def preparar_retoma():
    """Marca que, al arrancar, hay que engancharse a la tarea guardada."""
    if not _leer_tarea():
        return False
    _estado["retomando"] = True
    return True


def asegurar_tarea_en_disco():
    if not os.path.isfile(TAREA_FILE):
        return
    try:
        with open(TAREA_FILE, "rb") as archivo:
            os.fsync(archivo.fileno())
    except OSError:
        pass


def _argv_puente(lanzador):
    if lanzador.lower().endswith(".cmd"):
        base = os.path.dirname(lanzador)
        node = os.path.join(base, "node.exe")
        script = os.path.normpath(os.path.join(base, "..", "dist", "bin", "cursor-sdk-bridge.js"))
        if os.path.isfile(node) and os.path.isfile(script):
            return [node, script, "--workspace", ESCRITORIO]
    return [lanzador, "--workspace", ESCRITORIO]


def _arrancar_puente():
    """Arranca el puente fuera del proceso del bot, para que un reinicio no lo mate."""
    from cursor_sdk._bridge import BridgeEndpoint, _bridge_subprocess_env, parse_discovery_line
    from cursor_sdk._vendor import resolve_bridge_path

    argv = _argv_puente(resolve_bridge_path())
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    log = open(BRIDGE_LOG, "wb", buffering=0)
    try:
        proceso = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=log,
            env=dict(_bridge_subprocess_env()),
            cwd=ESCRITORIO,
            creationflags=flags,
        )
    except Exception:
        log.close()
        raise
    log.close()
    _puentes_abiertos.append(proceso)
    try:
        endpoint = _esperar_discovery(proceso, parse_discovery_line, BridgeEndpoint)
    except Exception:
        if proceso.poll() is None:
            proceso.kill()
        raise
    pid = endpoint.pid or proceso.pid
    _guardar_puente(endpoint.url, endpoint.auth_token, pid)
    _log(f"Puente de Cursor en marcha, pid {pid}")


def _esperar_discovery(proceso, parse_discovery_line, endpoint_cls):
    deadline = time.monotonic() + 30
    pending = ""
    with open(BRIDGE_LOG, "rb") as archivo:
        while time.monotonic() < deadline:
            chunk = archivo.read()
            if chunk:
                pending += chunk.decode("utf-8", "replace")
                while "\n" in pending:
                    linea, pending = pending.split("\n", 1)
                    parsed = parse_discovery_line(linea + "\n")
                    if parsed is not None:
                        return endpoint_cls.from_discovery(parsed)
                continue
            if proceso.poll() is not None:
                raise RuntimeError(
                    f"El puente de Cursor se cerró al arrancar (código {proceso.returncode})."
                )
            time.sleep(0.05)
    raise TimeoutError("El puente de Cursor no respondió a tiempo.")


async def _puerto_abierto(url):
    if not url:
        return False
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port
    if not port:
        return False
    try:
        _lectura, escritor = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2)
    except Exception:
        return False
    escritor.close()
    try:
        await escritor.wait_closed()
    except Exception:
        pass
    return True


def _etiqueta_tool(tool_call):
    nombre = ""
    ruta = ""

    def recorrer(nodo, profundidad=0):
        nonlocal nombre, ruta
        if profundidad > 4 or not isinstance(nodo, Mapping):
            return
        for clave, valor in nodo.items():
            clave_baja = str(clave).lower()
            if clave_baja in ("name", "toolname", "tool_name") and isinstance(valor, str) and not nombre:
                nombre = valor
            elif clave_baja in ("path", "file_path", "filepath", "target_file") and isinstance(valor, str) and not ruta:
                ruta = os.path.basename(valor.replace("\\", "/"))
            elif isinstance(valor, Mapping):
                recorrer(valor, profundidad + 1)

    recorrer(tool_call)
    bajos = nombre.lower()
    if any(pista in bajos for pista in ("read", "grep", "glob", "search")):
        verbo = "Mirando"
    elif any(pista in bajos for pista in ("edit", "write", "strreplace", "delete", "apply")):
        verbo = "Tocando"
    elif any(pista in bajos for pista in ("shell", "command", "terminal")):
        verbo = "Ejecutando"
    else:
        verbo = nombre or "Trabajando"
    if ruta:
        return f"{verbo} {ruta}"
    return verbo


def _vista(fase, texto):
    cuerpo = (texto or "").strip()
    if len(cuerpo) > 3200:
        cuerpo = "…\n" + cuerpo[-3200:]
    if cuerpo:
        return f"{fase}\n\n{cuerpo}"[:4000]
    return (fase or "⏳ Trabajando…")[:4000]


async def _cerrar_cliente():
    cliente = _estado.get("client")
    _estado["client"] = None
    _estado["agent"] = None
    if cliente is None:
        return
    try:
        await cliente.aclose()
    except Exception:
        pass


async def _soltar_agente():
    agente = _estado.get("agent")
    _estado["agent"] = None
    _borrar_sesion()
    if agente is None:
        return
    try:
        await agente.close()
    except Exception:
        pass


async def cancelar():
    carrera = _estado.get("run")
    if carrera is None:
        return False
    try:
        if carrera.supports("cancel"):
            await carrera.cancel()
            return True
    except Exception as error:
        _log(f"No pude parar Cursor: {error}", error=True)
    return False


async def reiniciar_conversacion():
    _estado["olvidar"] = True
    await cancelar()
    if _estado["busy"]:
        return
    _estado["olvidar"] = False
    await _soltar_agente()


async def _cliente(sdk):
    if _estado["client"] is not None:
        return _estado["client"]
    datos = _leer_puente()
    if datos and _proceso_vivo(datos.get("pid")) and await _puerto_abierto(datos.get("url")):
        cliente = sdk.AsyncClient.connect(datos["url"], datos["token"], timeout=None)
        _estado["client"] = cliente
        _estado["bridge_pid"] = int(datos["pid"])
        _log(f"Cursor sigue en el puente {datos['pid']}")
        return cliente
    await asyncio.to_thread(_arrancar_puente)
    datos = _leer_puente()
    if not datos:
        raise RuntimeError("El puente de Cursor arrancó pero no dejó dirección.")
    cliente = sdk.AsyncClient.connect(datos["url"], datos["token"], timeout=None)
    _estado["client"] = cliente
    _estado["bridge_pid"] = int(datos["pid"])
    return cliente


async def _agente(sdk, cliente, clave):
    if _estado["agent"] is not None:
        sesion = _leer_sesion()
        return _estado["agent"], not sesion.get("briefed", False)

    local = sdk.LocalAgentOptions(
        cwd=ESCRITORIO,
        dirs=[BOT_DIR],
        setting_sources=["project", "user"],
        sandbox_options=sdk.SandboxOptions(enabled=False),
        auto_review=False,
    )
    opciones = sdk.AgentOptions(model=MODELO, api_key=clave, local=local)
    sesion = _leer_sesion()
    if sesion.get("agent_id"):
        try:
            agente = await cliente.agents.resume(sesion["agent_id"], opciones)
            _estado["agent"] = agente
            _log(f"Cursor reanudado: {agente.agent_id}")
            return agente, not sesion.get("briefed", False)
        except Exception as error:
            _log(f"No pude reanudar Cursor, abro uno nuevo: {error}", error=True)
            _borrar_sesion()

    agente = await cliente.agents.create(
        model=MODELO,
        api_key=clave,
        name="MiBot Telegram",
        local=local,
    )
    _estado["agent"] = agente
    _guardar_sesion(agente.agent_id, False)
    _log(f"Cursor nuevo: {agente.agent_id}")
    return agente, True


def _componer(texto, presentar):
    if not presentar:
        return texto
    return f"{CONTEXTO}\n\nPetición de Aarón:\n{texto}"


def _datos_tarea(agent_id, run_id, chat_id, message_id, pedido):
    return {
        "agent_id": agent_id,
        "run_id": run_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "pedido": pedido,
        "bridge_pid": _estado.get("bridge_pid"),
    }


def _marcar_briefed(agent_id):
    if not agent_id or _estado.get("olvidar"):
        return
    try:
        _guardar_sesion(agent_id, True)
    except OSError as error:
        _log(f"No pude guardar la sesión de Cursor: {error}", error=True)


def _texto_resultado(resultado, acumulado=""):
    status = getattr(resultado, "status", "")
    if status == "cancelled":
        return "He parado. El siguiente mensaje sigue en la misma conversación."
    if status == "error":
        detalle = (getattr(resultado, "result", "") or acumulado or "").strip()
        if detalle:
            return f"No he podido terminar.\n\n{detalle}"
        return "No he podido terminar esta petición."
    final = (getattr(resultado, "result", "") or acumulado or "").strip()
    return final or "Hecho."


async def _esperar_con_progreso(sdk, cliente, carrera, al_progreso):
    """Espera un run que ya estaba en el puente y va contando por Telegram."""

    async def mirar():
        acumulado = ""
        fase = "🔄 Sigo con la tarea después del reinicio…"
        ultimo = 0.0
        try:
            async for event in cliente.observe_run(carrera.id):
                update = event.interaction_update
                if isinstance(update, sdk.TextDeltaUpdate) and update.text:
                    acumulado += update.text
                elif isinstance(update, sdk.ToolCallStartedUpdate):
                    fase = "🔧 " + _etiqueta_tool(update.tool_call)
                else:
                    continue
                ahora = time.monotonic()
                if ahora - ultimo < 2:
                    continue
                ultimo = ahora
                await _avisar(al_progreso, _vista(fase, acumulado))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            _log(f"No pude seguir el directo de Cursor: {error}", error=True)

    aviso = asyncio.create_task(mirar())
    try:
        return await carrera.wait()
    finally:
        aviso.cancel()
        try:
            await aviso
        except asyncio.CancelledError:
            pass
        except Exception:
            pass


async def _una_vez(texto, al_progreso, *, chat_id=None, message_id=None, pedido=None, aviso_inicial="⏳ Abriendo Cursor en el PC…"):
    import cursor_sdk as sdk

    clave = _leer_clave()
    if not clave:
        return texto_sin_clave()

    pedido_guardado = pedido if pedido is not None else texto
    await _avisar(al_progreso, aviso_inicial)
    cliente = await _cliente(sdk)
    agente, presentar = await _agente(sdk, cliente, clave)
    _guardar_tarea(_datos_tarea(agente.agent_id, "", chat_id, message_id, pedido_guardado))
    acumulado = ""
    fase = "⏳ Trabajando…"
    ultimo = 0.0

    async def on_delta(update):
        nonlocal acumulado, fase, ultimo
        if isinstance(update, sdk.TextDeltaUpdate) and update.text:
            acumulado += update.text
        elif isinstance(update, sdk.ToolCallStartedUpdate):
            fase = "🔧 " + _etiqueta_tool(update.tool_call)
        else:
            return
        ahora = time.monotonic()
        if ahora - ultimo < 2:
            return
        ultimo = ahora
        await _avisar(al_progreso, _vista(fase, acumulado))

    carrera = await agente.send(
        _componer(texto, presentar),
        sdk.SendOptions(on_delta=on_delta, local=sdk.LocalSendOptions(force=True)),
    )
    _estado["run"] = carrera
    _guardar_tarea(_datos_tarea(agente.agent_id, carrera.id, chat_id, message_id, pedido_guardado))
    _log(f"Cursor run {carrera.id} agent {agente.agent_id}")
    resultado = await carrera.wait()
    _borrar_tarea()
    if resultado.status == "finished" and presentar:
        _marcar_briefed(agente.agent_id)
    return _texto_resultado(resultado, acumulado)


async def _puente_de_la_tarea_vivo(tarea):
    datos = _leer_puente()
    if not datos:
        return False
    if int(datos.get("pid") or 0) != int(tarea.get("bridge_pid") or 0):
        return False
    if not _proceso_vivo(datos.get("pid")):
        return False
    return await _puerto_abierto(datos.get("url"))


async def _continuar_guardada(tarea, al_progreso):
    import cursor_sdk as sdk

    pedido = str(tarea.get("pedido") or "").strip()
    run_id = str(tarea.get("run_id") or "")
    if await _puente_de_la_tarea_vivo(tarea) and run_id:
        cliente = await _cliente(sdk)
        try:
            carrera = await cliente.agents.get_run(run_id)
        except Exception as error:
            _log(f"No pude enganchar la tarea {run_id}: {error}", error=True)
            carrera = None
        if carrera is not None and carrera.status not in _TERMINALES:
            _estado["run"] = carrera
            await _avisar(al_progreso, "🔄 Sigo con la tarea después del reinicio…")
            resultado = await _esperar_con_progreso(sdk, cliente, carrera, al_progreso)
            _borrar_tarea()
            if resultado.status == "finished":
                _marcar_briefed(carrera.agent_id or tarea.get("agent_id"))
            return _texto_resultado(resultado, "")
        if carrera is not None and carrera.status in _TERMINALES:
            _borrar_tarea()
            if carrera.status == "finished":
                _marcar_briefed(carrera.agent_id or tarea.get("agent_id"))
            return _texto_resultado(carrera, "")

    if not pedido:
        _borrar_tarea()
        return "Se cortó la tarea con el reinicio y no tengo el texto para retomarla."
    _log("La tarea de Cursor se cortó con el reinicio. La retomo.")
    await _avisar(al_progreso, "🔄 La tarea se cortó con el reinicio. La retomo donde estaba.")
    aviso = (
        "El bot de Telegram se reinició y la ejecución anterior se cortó. "
        "Sigue exactamente donde lo dejaste. No repitas lo que ya esté hecho.\n\n"
        f"Petición original de Aarón:\n{pedido}"
    )
    return await _una_vez(
        aviso,
        al_progreso,
        chat_id=tarea.get("chat_id"),
        message_id=tarea.get("message_id"),
        pedido=pedido,
        aviso_inicial="⏳ Retomando la tarea en Cursor…",
    )


async def _avisar(al_progreso, texto):
    if al_progreso is None:
        return
    try:
        await al_progreso(texto)
    except Exception:
        pass


def _olvidar_si_no_empezo():
    if not str(_leer_tarea().get("run_id") or ""):
        _borrar_tarea()


def _mensaje_de_fallo(error):
    if isinstance(error, ImportError):
        return "Falta el paquete cursor-sdk. En el PC: py -m pip install cursor-sdk"
    from cursor_sdk import CursorAgentError

    if isinstance(error, CursorAgentError):
        _log(
            f"Cursor no arrancó: {error.message} retryable={error.is_retryable}",
            error=True,
        )
        if getattr(error, "is_retryable", False):
            return "Cursor no ha podido empezar ahora. Prueba otra vez en un momento."
        mensaje = str(getattr(error, "message", error))
        if "api" in mensaje.lower() and "key" in mensaje.lower():
            return texto_sin_clave()
        return f"No he podido empezar: {mensaje}"
    _log(f"Fallo hablando con Cursor: {error}", error=True)
    return f"Se ha cortado la conexión con Cursor: {error}"


async def _cerrar_si_fallo(error):
    if isinstance(error, ImportError):
        return
    await _cerrar_cliente()


async def consultar(texto, al_progreso=None, *, chat_id=None, message_id=None):
    pedido = (texto or "").strip()
    if not pedido:
        return "Dime qué quieres que arregle o cambie."
    if _estado["busy"] or _estado.get("retomando"):
        raise Ocupado()
    _estado["busy"] = True
    try:
        try:
            return await _una_vez(pedido, al_progreso, chat_id=chat_id, message_id=message_id, pedido=pedido)
        except Exception as error:
            _olvidar_si_no_empezo()
            await _cerrar_si_fallo(error)
            return _mensaje_de_fallo(error)
    finally:
        _estado["busy"] = False
        _estado["run"] = None
        if _estado.get("olvidar"):
            _estado["olvidar"] = False
            await _soltar_agente()


async def reanudar_tarea(al_progreso=None):
    """Tras un reinicio, espera la tarea que seguía en el puente o la retoma."""
    _estado["retomando"] = False
    tarea = _leer_tarea()
    if not tarea:
        return None
    if _estado["busy"]:
        return None
    _estado["busy"] = True
    try:
        try:
            return await _continuar_guardada(tarea, al_progreso)
        except Exception as error:
            _olvidar_si_no_empezo()
            await _cerrar_si_fallo(error)
            return _mensaje_de_fallo(error)
    finally:
        _estado["busy"] = False
        _estado["run"] = None
        _estado["retomando"] = False
        if _estado.get("olvidar"):
            _estado["olvidar"] = False
            await _soltar_agente()
