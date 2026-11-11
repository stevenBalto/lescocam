# Sesión 2026-11-11 — Banco de las 4 personas y rediseño del motor de palabras

**Área:** Backend (core / data / scripts / tests)
**Quién:** Christian Paniagua

## Objetivo de la sesión
- Cerrar la fase 1 del problema 1 (banco de prueba de las 4 personas) y resolver la fase 2 (aumentación en landmarks).

## Lo que se hizo
- **Fase 1 cerrada:** 240 tomas (4 personas, 4 cámaras), punto de partida: top-1 40.4 %, top-3 58.3 %, errónea 0 %. Resumen en `data/banco/resultado_inicial.json`.
- **Aumentación en landmarks (rotación 3D, escala, amplitud, velocidad, ruido, pérdida de mano, espejo):** no mejoró el banco (40.4 → 42.5 % top-1, inconsistente). Descartada y borrada; la conclusión está en `hiloEquipo/problema-1-christian-paniagua.md`.
- **Rediseño del motor (`core/palabras.py`, `VERSION_DESCRIPTOR` 3):** giro de 180° si la nariz queda bajo los hombros, reposo relativo por brazo en el `Segmentador` (campo nuevo `CuadroPalabra.reposo`), `PESO_FORMA` y `PESO_NO_DOMINANTE` en 1.0, margen relativo (d2 ≥ 1.18·d1), `DISTANCIA_MAX` 5, control de duración (`DURACION_RELATIVA_MIN` 0.5). `senas_db.leer()` devuelve `duraciones`. `senas.db` regenerada. `evaluar_palabras.py` tiene `--extraccion` (por defecto `recorte`).
- **Resultado en el banco:** top-1 64.2 %, top-3 79.6 %, dice bien 27.9 %, errónea 0.4 %, sin seña 4.2 %. Validación cruzada: mitad A 25.8 → 60.8, mitad B 55.0 → 67.5. CENAREC sin regresión.
- Cache de CENAREC de las 85 palabras extraída con recorte (`data/dictionary/cenarec/extraccion/recorte/`, no se versiona).

## Lo que faltó por hacer
- [ ] **Avisar al equipo del cambio de contrato** (`senas.db` v3 ya no es compatible con v2): la app móvil (Flutter) tiene que implementar el giro de 180° (con margen `MARGEN_CABEZA_ABAJO` 0.05: nariz.y menos promedio de y de hombros > 0.05), el reposo relativo, los pesos de `meta`, el margen relativo y el control de duración.
- [ ] **`core/cuerpo.py` (`buscar_en_recortes`, problema 3) usa `REPOSO_Y = 0.85` fijo y la pose SIN girar**: con la imagen girada 180° el criterio de "brazo abajo" queda invertido, y tampoco usa el reposo relativo. Aplicar `cabeza_abajo` ahí (revisión de código, hallazgo 3; avisar a Steven).
- [ ] Un `Segmentador` reusado entre videos sin `reiniciar()` mezcla la ventana de reposo si `t` retrocede. Hoy nadie lo hace; llamar `reiniciar()` si hace falta.
- [ ] Aceptar más palabras correctas: top-1 64 % pero se dice bien solo 28 %. Probar más plantillas de otras personas (Hands-On, `--handson`) o el modelo de la fase 4.
- [ ] Steven conserva 13 % sin seña (tomas largas o sin volver al reposo); revisar `DURACION_MAX` con el abecedario (no hay cache).
- [ ] Nadie grabó con el Huawei; las tomas de Christian son todas luz buena, distancia media y de frente.
- [ ] Fases 3–5 del problema 1 (ASL Citizen, entrenar el modelo, integrar y medir).

## Decisiones y notas
- Las tomas de Christian con el iPhone (Iriun) estaban giradas 180°: eso explicaba su 16.7 % y el "atractor HOY". El motor lo corrige ahora como robustez permanente.
- Se probó y descartó: z-score por columna, corrección de plantillas "hub", media en vez de mínimo, recortar subida y bajada, cambiar BANDA/MUESTRAS/FRACCION_ACTIVA/CARA_RADIO, bajar `Y_REPOSO` fijo.
- Las 4 personas hacen las señas ~0.19 anchos de hombro más arriba que la persona de CENAREC; corregir ese corrimiento empeoraba, no se aplicó.
- Trabajo hecho con subagentes genéricos porque la sesión abrió en la carpeta padre y no cargó los agentes del proyecto (conviene abrir Claude Code dentro de `lescocam`).

## Revisión antes del push
- Revisión de código (Sonnet, esfuerzo alto): sin hallazgos graves. Se corrigieron: margen del giro (antes sin margen: una persona agachada podía activarlo por cuadro), empate exacto d1 = d2 = 0 (ya no se acepta), encabezado de `core/palabras.py` completo para la app (ventana de reposo, `DISTANCIA_MAX` 5) y docstring de `reconocedor_palabras.py`. 338 pruebas pasan; banco sin cambios (64.2 % top-1).

## Siguiente paso
- Fase 3 del problema 1 (datos de ASL Citizen) o, antes, avisar al equipo del cambio de contrato de `senas.db`.
