"""Íconos de LESCOCam exportados de Figma (página Componentes, «Ícono/…»).

Todos son de 24×24 con trazo de 2 px. Se guarda solo el dibujo; el color se
pone al pedirlos (`image://icono/<nombre>?color=%23RRGGBB`), así sirven en
modo claro y oscuro.
"""

_TRAZO = 'stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'

DIBUJOS = {
    "historial": f'<path d="M4 12C3.9969 13.854 4.63786 15.6516 5.81333 17.0854C6.9888 18.5192 8.62577 19.5002 10.4444 19.8607C12.2631 20.2212 14.1505 19.9388 15.784 19.0619C17.4176 18.1849 18.6958 16.7678 19.4001 15.0527C20.1045 13.3377 20.1914 11.4313 19.6458 9.65931C19.1002 7.88735 17.9561 6.3599 16.4091 5.33807C14.862 4.31624 13.0081 3.86347 11.1642 4.05717C9.32031 4.25086 7.60093 5.079 6.3 6.4M4 4V8H8M12 8V12L15 14" {_TRAZO}/>',
    "cerrar": f'<path d="M6 6L18 18M18 6L6 18" {_TRAZO}/>',
    "pausar": f'<path d="M9 6V18M15 6V18" {_TRAZO}/>',
    "borrar-palabra": f'<path d="M12 10L16 14M16 10L12 14M9 6H20V18H9L3 12L9 6Z" {_TRAZO}/>',
    "terminar": f'<path d="M5 12.5L9.5 17L19 7" {_TRAZO}/>',
    "reproducir": '<path d="M8 5L19 12L8 19V5Z" fill="{c}"/>',
    "descargar": f'<path d="M12 4V15M17 10L12 15L7 10M5 20H19" {_TRAZO}/>',
    "copiar": f'<path d="M5 15H4V4H15V5M9 9H20V20H9V9Z" {_TRAZO}/>',
    "pegar": f'<path d="M4 12H15M11 7L16 12L11 17M20 4V20" {_TRAZO}/>',
    "buscar": f'<path d="M20 20L16 16M11 4C7.13401 4 4 7.13401 4 11C4 14.866 7.13401 18 11 18C14.866 18 18 14.866 18 11C18 7.13401 14.866 4 11 4Z" {_TRAZO}/>',
    "ajustes": f'<path d="M4 7H14M18 7H20M4 17H8M12 17H20M16 5V9M10 15V19" {_TRAZO}/>',
    "diccionario": f'<path d="M19 17V21H7C5.89543 21 5 20.1046 5 19V5C5 3.89543 5.89543 3 7 3H19V17ZM5 19C5 17.8954 5.89543 17 7 17H19M9 7H15M9 11H13" {_TRAZO}/>',
    "practica": f'<path d="M12 3C7.02944 3 3 7.02944 3 12C3 16.9706 7.02944 21 12 21C16.9706 21 21 16.9706 21 12C21 7.02944 16.9706 3 12 3ZM12 8C9.79086 8 8 9.79086 8 12C8 14.2091 9.79086 16 12 16C14.2091 16 16 14.2091 16 12C16 9.79086 14.2091 8 12 8Z" {_TRAZO}/>',
    "camara": f'<path d="M3 7H7L9 5H15L17 7H21V19H3V7ZM12 10C10.3431 10 9 11.3431 9 13C9 14.6569 10.3431 16 12 16C13.6569 16 15 14.6569 15 13C15 11.3431 13.6569 10 12 10Z" {_TRAZO}/>',
    "alerta": f'<path d="M12 10V14M12 17V17.5M12 3L22 21H2L12 3Z" {_TRAZO}/>',
    "luz": f'<path d="M9 18H15M10 21H14M12 3C10.7786 2.99359 9.58433 3.3601 8.57679 4.05056C7.56925 4.74102 6.79643 5.72253 6.36161 6.86394C5.92679 8.00534 5.85068 9.25227 6.14344 10.4381C6.43621 11.6239 7.08392 12.6921 8 13.5C8.8 14.3 9 15 9 16H15C15 15 15.2 14.3 16 13.5C16.9161 12.6921 17.5638 11.6239 17.8566 10.4381C18.1493 9.25227 18.0732 8.00534 17.6384 6.86394C17.2036 5.72253 16.4308 4.74102 15.4232 4.05056C14.4157 3.3601 13.2214 2.99359 12 3Z" {_TRAZO}/>',
    "inicio": f'<path d="M4 11L12 4L20 11V20H15V14H9V20H4V11Z" {_TRAZO}/>',
    "escribir": f'<path d="M13.5 6.5L17.5 10.5M4 20H8L19 9L15 5L4 16V20Z" {_TRAZO}/>',
    "hablar": f'<path d="M16 9C16.4256 9.37537 16.7665 9.83701 17 10.3542C17.2335 10.8715 17.3542 11.4325 17.3542 12C17.3542 12.5675 17.2335 13.1285 17 13.6458C16.7665 14.163 16.4256 14.6246 16 15M18.5 6.5C19.9066 7.98577 20.6905 9.95401 20.6905 12C20.6905 14.046 19.9066 16.0142 18.5 17.5M4 10V14H8L13 18V6L8 10H4Z" {_TRAZO}/>',
    "ocultar": f'<path d="M3 3L21 21M10.6 6.1C11.0637 6.03325 11.5315 5.99983 12 6C17 6 21 12 21 12C20.2664 13.1682 19.3933 14.2428 18.4 15.2M6.2 7.6C4.2 9.2 3 12 3 12C3 12 7 18 12 18C13.4 18 14.7 17.6 15.8 17" {_TRAZO}/>',
    "mas": f'<path d="M5 12H5.5M12 12H12.5M19 12H19.5" {_TRAZO}/>',
    "deletrear": '<circle cx="6" cy="10" r="2.5" fill="{c}"/><circle cx="12" cy="10" r="2.5" fill="{c}"/>'
    '<circle cx="18" cy="10" r="2.5" fill="{c}"/>'
    f'<path d="M4 17H20" stroke="{{c}}" stroke-width="2" stroke-linecap="round"/>',
    "mover-vertical": f'<path d="M12 4V20M16 8L12 4L8 8M16 16L12 20L8 16" {_TRAZO}/>',
    "atras": f'<path d="M11 18L4 12L11 6M4 12H20" {_TRAZO}/>',
}


def svg(nombre: str, color: str = "#0d2d6d") -> bytes:
    """Devuelve el SVG del ícono pintado con `color`."""
    dibujo = DIBUJOS[nombre].replace("{c}", color)
    return (
        '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'xmlns="http://www.w3.org/2000/svg">{dibujo}</svg>'
    ).encode()
