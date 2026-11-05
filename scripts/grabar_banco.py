"""Graba el banco de prueba de palabras (problema 1, fase 1) imitando los videos de CENAREC.

Las tomas son SOLO para medir (nunca plantillas ni entrenamiento). No hace falta
saber LESCO: se mira el video de la izquierda y se imita. Se guardan landmarks
(manos + pose, formato v1), no video. Formato y ubicación: core/banco.py.

Cada persona tiene su lista de 30 palabras (data/reference/banco/<nombre>.txt): 12 del núcleo común
(las graban los 4) + 18 propias, en 3 tandas de 10. Por cada palabra se graban --tomas tomas.
Cada toma dura CAPTURA_S segundos: empezar con las manos abajo (en reposo), hacer
la seña UNA vez y volver a bajar las manos. No se muestra si el motor la reconoce
(para no elegir solo las buenas); solo se avisa si no se ve el cuerpo.

Uso:
    .venv/Scripts/python -m scripts.grabar_banco "Christian Paniagua" --camara-nombre iphone13 [--plan]
        [--camara 0] [--tomas 2] [--luz buena] [--distancia media] [--angulo frente] [--palabras HOLA GRACIAS]

--camara-nombre: con qué cámara grabas (iphone13, hp-windows, hp-linux, huawei...); queda en cada toma.
--plan: cada tanda de 10 palabras cambia sola luz, distancia y ángulo (te dice qué hacer en pantalla).

Tras cada toma muestra lo que lee el motor (para saber si la seña se entiende y por qué no). La toma se
guarda igual, acierte o no. Para el banco final conviene --a-ciegas: no repetir las que fallan inflaría el resultado.

Teclas: ESPACIO graba (cuenta 3 s) · G guarda · R repite · N/B siguiente/anterior palabra
        L cambia la luz · D la distancia · A el ángulo · Q/ESC salir.
Cambia luz, distancia y ángulo entre palabras: eso es lo que mide la variedad.
Retoma donde quedó (cuenta las tomas ya guardadas de esa persona).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

from core import banco
from scripts.evaluar_banco import evaluar_cuadros, resumen_toma
from scripts.extraer_cenarec import VIDEOS, catalogo

CUENTA_S = 3.0
CAPTURA_S = 6.0
COBERTURA_MIN = 0.7   # fracción mínima de cuadros con cuerpo visible
MANOS_MIN = 0.1       # fracción mínima de cuadros con alguna mano (si no, las manos no entraron en cuadro)


def primera_pendiente(persona: str, palabras: list[str], tomas: int, desde: int = 0,
                      raiz: Path = banco.CARPETA) -> Optional[int]:
    """Índice de la primera palabra (desde `desde`, con vuelta) que aún no tiene `tomas` tomas, o None."""
    n = len(palabras)
    for paso in range(n):
        i = (desde + paso) % n
        if banco.contar_tomas(persona, i + 1, raiz) < tomas:
            return i
    return None


def _siguiente(valor: str, opciones: tuple) -> str:
    return opciones[(opciones.index(valor) + 1) % len(opciones)]


def _texto(cv2, img, txt, y, color=(255, 255, 255), esc=0.6):
    txt = banco.sin_tildes(txt)
    cv2.putText(img, txt, (10, y), cv2.FONT_HERSHEY_SIMPLEX, esc, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, txt, (10, y), cv2.FONT_HERSHEY_SIMPLEX, esc, color, 1, cv2.LINE_AA)


class Referencia:
    """Reproduce en bucle el video de CENAREC de la palabra actual."""

    def __init__(self, cv2, cat: dict):
        self.cv2, self.cat, self.cap, self.etiqueta = cv2, cat, None, None

    def _abrir(self, etiqueta: str) -> None:
        if self.cap is not None:
            self.cap.release()
        self.etiqueta = etiqueta
        d = self.cat.get(etiqueta)
        self.cap = self.cv2.VideoCapture(str(VIDEOS / d["archivo"])) if d else None

    def cuadro(self, etiqueta: str, alto: int):
        cv2 = self.cv2
        if etiqueta != self.etiqueta:
            self._abrir(etiqueta)
        panel = np.full((alto, int(alto * 16 / 9) // 1, 3), 40, np.uint8)
        if self.cap is None:
            cv2.putText(panel, "sin video de referencia", (20, alto // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (200, 200, 200), 1)
            return panel
        ok, img = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, img = self.cap.read()
        if not ok:
            return panel
        h, w = img.shape[:2]
        f = min(panel.shape[1] / w, alto / h)
        img = cv2.resize(img, (max(1, int(w * f)), max(1, int(h * f))))
        y0, x0 = (alto - img.shape[0]) // 2, (panel.shape[1] - img.shape[1]) // 2
        panel[y0:y0 + img.shape[0], x0:x0 + img.shape[1]] = img
        cv2.putText(panel, "imita este video", (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
        return panel

    def cerrar(self) -> None:
        if self.cap is not None:
            self.cap.release()


def _dibujar_manos(cv2, frame, cuadro) -> None:
    alto, ancho = frame.shape[:2]
    for puntos, _, _ in cuadro.manos:
        for x, y, _ in puntos:
            cv2.circle(frame, (int(x * ancho), int(y * alto)), 3, (0, 255, 0), -1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("persona", help='nombre de quien graba, p. ej. "Christian Paniagua"')
    ap.add_argument("--camara", type=int, default=0, help="número de la cámara en el sistema (0, 1...)")
    ap.add_argument("--camara-nombre", required=True, help="nombre de la cámara que usas (iphone13, hp-windows, hp-linux, huawei...)")
    ap.add_argument("--plan", action="store_true", help="cambia luz/distancia/ángulo por tanda de 10 palabras")
    ap.add_argument("--lista", type=Path, help="archivo de palabras (por defecto, el de tu nombre en data/reference/banco/)")
    ap.add_argument("--tomas", type=int, default=2, help="tomas por palabra (2)")
    ap.add_argument("--luz", choices=banco.LUCES, default="buena")
    ap.add_argument("--distancia", choices=banco.DISTANCIAS, default="media")
    ap.add_argument("--angulo", choices=banco.ANGULOS, default="frente")
    ap.add_argument("--palabras", nargs="+", help="solo estas etiquetas (por defecto, toda la lista del banco)")
    ap.add_argument("--a-ciegas", action="store_true", help="no mostrar lo que lee el motor tras cada toma")
    ap.add_argument("--destino", type=Path, default=banco.CARPETA)
    a = ap.parse_args(argv)

    try:
        todas = banco.leer_lista(a.lista or banco.lista_de(a.persona))
    except ValueError as e:
        print(e)
        return 1
    palabras = [p for p in todas if not a.palabras or p in a.palabras]
    if not palabras:
        print("Ninguna palabra coincide con la lista del banco.")
        return 1
    persona = banco.limpiar_persona(a.persona)
    orden = {p: todas.index(p) + 1 for p in palabras}
    cat = catalogo()
    faltan = [p for p in palabras if p not in cat]
    if faltan:
        print(f"Sin video de CENAREC (se graba igual, sin referencia): {faltan}\n"
              "  Bajarlos: .venv/Scripts/python -m scripts.descargar_cenarec --lista data/reference/banco/<tu nombre>.txt")

    i = primera_pendiente(persona, palabras, a.tomas, 0, a.destino)
    if i is None:
        print(f"{persona} ya tiene {a.tomas} tomas de las {len(palabras)} palabras. Nada que grabar.")
        return 0

    import cv2
    from core.camara import abrir_camara, leer_espejado
    from core.cuerpo import DetectorCuerpo

    try:
        cap = abrir_camara(a.camara)
    except RuntimeError:
        print(f"No se pudo abrir la cámara {a.camara}: cerrá la app de escritorio, que está usando la cámara.")
        return 1
    detector = DetectorCuerpo()
    comparador = None
    if not a.a_ciegas:
        from core import senas_db
        comparador = senas_db.comparador()
    resultado = None
    ref = Referencia(cv2, cat)
    luz, distancia, angulo = a.luz, a.distancia, a.angulo
    tanda_txt, i_previa = "", None
    ventana = "LESCOCam banco de prueba"
    fase, t0, cuadros, cobertura, aviso = "espera", 0.0, [], 0.0, ""
    guardadas = 0
    try:
        while True:
            frame = leer_espejado(cap)
            if frame is None:
                print("La cámara dejó de responder.")
                break
            alto, ancho = frame.shape[:2]
            ahora = time.monotonic()
            cuadro = detector.procesar(frame, ahora)
            vista = frame.copy()
            _dibujar_manos(cv2, vista, cuadro)
            etiqueta = palabras[i]
            if a.plan and i != i_previa:
                (luz, distancia, angulo), instruccion, n_tanda = banco.plan_de(todas.index(etiqueta))
                tanda_txt = f"TANDA {n_tanda}/3: {instruccion}"
            i_previa = i
            hechas = banco.contar_tomas(persona, orden[etiqueta], a.destino)

            if fase == "cuenta":
                resto = CUENTA_S - (ahora - t0)
                if resto <= 0:
                    fase, t0, cuadros = "captura", ahora, []
                else:
                    cv2.putText(vista, str(int(resto) + 1), (ancho // 2 - 30, alto // 2 + 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 255, 255), 6)
                    _texto(cv2, vista, "manos abajo, en reposo", alto - 40, (0, 255, 255), 0.5)
            if fase == "captura":
                cuadros.append(cuadro)
                cv2.circle(vista, (ancho - 25, 25), 10, (0, 0, 255), -1)
                _texto(cv2, vista, "haz la sena UNA vez y baja las manos", alto - 40, (0, 0, 255), 0.5)
                if ahora - t0 >= CAPTURA_S:
                    cobertura = banco.cobertura_cuerpo(cuadros)
                    manos = banco.cobertura_manos(cuadros)
                    fase = "revisar"
                    if cobertura < COBERTURA_MIN:
                        aviso = f"se te ve el cuerpo en {cobertura:.0%} de la toma: encuadra hombros y manos (R repetir)"
                    elif manos < MANOS_MIN:
                        aviso = "no se detectaron tus manos: que entren en cuadro al subirlas (R repetir)"
                    else:
                        aviso = ""
                    resultado = evaluar_cuadros(cuadros, palabras[i], comparador) if comparador and not aviso else None
                    if resultado:
                        print(f"  {palabras[i]}: {resumen_toma(resultado)[0]}", flush=True)
            if fase == "revisar":
                _texto(cv2, vista, aviso or "toma lista: G guardar | R repetir", alto - 40,
                       (0, 165, 255) if aviso else (0, 255, 0), 0.5)
                if resultado:
                    txt, estado = resumen_toma(resultado)
                    _texto(cv2, vista, txt, alto - 70, {"ok": (0, 255, 0), "mal": (0, 0, 255), "nada": (0, 165, 255)}[estado], 0.5)

            hombros_ok = cuadro.pose is not None and cuadro.pose[11, 3] > 0.5 and cuadro.pose[12, 3] > 0.5
            _texto(cv2, vista, f"hombros {'OK' if hombros_ok else 'NO SE VEN'} | manos detectadas: {len(cuadro.manos)}",
                   75, (0, 255, 0) if hombros_ok and cuadro.manos else (0, 165, 255), 0.5)
            _texto(cv2, vista, f"{etiqueta} ({i + 1}/{len(palabras)})  tomas {hechas}/{a.tomas}  [{persona}]", 25)
            if tanda_txt:
                _texto(cv2, vista, tanda_txt, 100, (255, 255, 0), 0.5)
            _texto(cv2, vista, f"luz {luz} (L) | distancia {distancia} (D) | angulo {angulo} (A)", 50, (0, 255, 255), 0.5)
            _texto(cv2, vista, "ESPACIO grabar | G guardar | R repetir | N/B palabra | Q salir", alto - 12, esc=0.45)
            cv2.imshow(ventana, np.hstack([ref.cuadro(etiqueta, alto), vista]))

            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), 27):
                break
            if tecla == ord("l"):
                luz = _siguiente(luz, banco.LUCES)
            elif tecla == ord("d"):
                distancia = _siguiente(distancia, banco.DISTANCIAS)
            elif tecla == ord("a"):
                angulo = _siguiente(angulo, banco.ANGULOS)
            elif tecla == ord(" ") and fase in ("espera", "revisar"):
                fase, t0, aviso, resultado = "cuenta", ahora, "", None
            elif tecla == ord("r") and fase in ("revisar", "espera"):
                fase, aviso = "espera", ""
            elif tecla == ord("g") and fase == "revisar" and not aviso:
                ruta = banco.guardar_toma(cuadros, etiqueta, orden[etiqueta], persona, luz, distancia, angulo,
                                          a.destino, camara=a.camara_nombre)
                guardadas += 1
                print(f"  {etiqueta}: guardada {ruta.name} ({luz}/{distancia}/{angulo}, {len(cuadros)} cuadros)",
                      flush=True)
                fase, cuadros = "espera", []
                if banco.contar_tomas(persona, orden[etiqueta], a.destino) >= a.tomas:
                    i2 = primera_pendiente(persona, palabras, a.tomas, i + 1, a.destino)
                    if i2 is None:
                        print("Listo: todas las palabras tienen sus tomas.")
                        break
                    i = i2
            elif tecla == ord("n") and fase == "espera":
                i = (i + 1) % len(palabras)
            elif tecla == ord("b") and fase == "espera":
                i = (i - 1) % len(palabras)
    finally:
        cap.release()
        ref.cerrar()
        detector.cerrar()
        cv2.destroyAllWindows()
    total = sum(banco.contar_tomas(persona, orden[p], a.destino) for p in palabras)
    print(f"Guardadas en esta sesión: {guardadas}. Total de {persona}: {total} tomas en {a.destino / persona}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
