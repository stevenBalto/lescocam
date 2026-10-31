"""Voz del sistema con pyttsx3, en un hilo propio. Si falla, la app sigue sin audio."""
from __future__ import annotations

import queue
import threading
from typing import Callable, Optional

_MARCAS_ESPANOL = ("spanish", "español", "espanol", "es-", "es_", "es-cr", "es-mx", "es-es")


def elegir_voz_espanol(voces) -> Optional[str]:
    """Devuelve el id de la primera voz en español, o None."""
    for v in voces:
        idiomas = " ".join(
            i.decode("utf-8", "ignore") if isinstance(i, bytes) else str(i)
            for i in (getattr(v, "languages", None) or [])
        )
        texto = f"{getattr(v, 'name', '')} {getattr(v, 'id', '')} {idiomas}".lower()
        if any(m in texto for m in _MARCAS_ESPANOL):
            return v.id
    return None


class Voz:
    """hablar(texto) encola y habla sin bloquear; parar() corta y vacía la cola.

    Estado para la UI:
      disponible -> False si pyttsx3 no pudo iniciar (sin audio)
      aviso      -> mensaje corto para mostrar en pantalla (o "")
      al_hablar  -> callback(bool) cuando empieza / termina de sonar
    """

    def __init__(self, fabrica_motor: Optional[Callable[[], object]] = None,
                 al_hablar: Optional[Callable[[bool], None]] = None):
        self._fabrica = fabrica_motor or self._fabrica_por_defecto
        self._al_hablar = al_hablar
        self._cola: "queue.Queue[Optional[str]]" = queue.Queue()
        self._motor = None
        self._candado = threading.Lock()
        self.disponible = True
        self.aviso = ""
        self._listo = threading.Event()
        self._hilo = threading.Thread(target=self._correr, name="voz", daemon=True)
        self._hilo.start()
        self._listo.wait(timeout=5)

    @staticmethod
    def _fabrica_por_defecto():
        import pyttsx3
        return pyttsx3.init()

    def _correr(self) -> None:
        try:
            motor = self._fabrica()
            voz = elegir_voz_espanol(motor.getProperty("voices"))
            if voz is not None:
                motor.setProperty("voice", voz)
            else:
                self.aviso = "Sin voz en español: se usa la voz predeterminada"
            with self._candado:
                self._motor = motor
        except Exception as e:  # pyttsx3 puede fallar de muchas formas según el SO
            self.disponible = False
            self.aviso = f"Audio no disponible ({type(e).__name__})"
            self._listo.set()
            return
        self._listo.set()

        while True:
            texto = self._cola.get()
            if texto is None:
                break
            try:
                self._avisar(True)
                motor.say(texto)
                motor.runAndWait()
            except Exception as e:
                self.disponible = False
                self.aviso = f"Audio no disponible ({type(e).__name__})"
                self._avisar(False)
                break
            if self._cola.empty():
                self._avisar(False)

    def _avisar(self, hablando: bool) -> None:
        if self._al_hablar:
            self._al_hablar(hablando)

    def hablar(self, texto: str) -> bool:
        """Encola texto. Devuelve False si no hay audio o el texto está vacío."""
        texto = (texto or "").strip()
        if not texto or not self.disponible:
            return False
        self._cola.put(texto)
        return True

    def parar(self) -> None:
        """Corta lo que suena y descarta lo pendiente."""
        try:
            while True:
                self._cola.get_nowait()
        except queue.Empty:
            pass
        with self._candado:
            motor = self._motor
        if motor is not None:
            try:
                motor.stop()
            except Exception:
                pass

    def cerrar(self) -> None:
        self.parar()
        self._cola.put(None)
        self._hilo.join(timeout=2)
