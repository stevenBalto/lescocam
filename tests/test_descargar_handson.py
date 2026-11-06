from scripts.descargar_handson import nombre_archivo, tarjetas

PAGINA = '''
<div class="video-lazy-load" data-video-id="1135063115"
     data-thumbnail-url="https://i.vimeocdn.com/x" title="Haga clic para reproducir: autonomía">
<div class="video-lazy-load" data-video-id="42"
     data-thumbnail-url="https://i.vimeocdn.com/y" title="Haga clic para reproducir: a veces">
'''


def test_tarjetas_saca_id_y_palabra():
    assert tarjetas(PAGINA) == [("1135063115", "autonomía"), ("42", "a veces")]


def test_tarjetas_pagina_vacia():
    assert tarjetas("<html></html>") == []


def test_nombre_archivo_limpia_y_lleva_el_id():
    assert nombre_archivo("42", "a veces") == "a_veces_42.mp4"
    assert nombre_archivo("7", "autonomía") == "autonomía_7.mp4"
    assert nombre_archivo("9", "???") == "sin_nombre_9.mp4"
