# Lámina de montaje

*La filosofía visual de la identidad de AdvanceDrawIO.*

Un buen diagrama de arquitectura no se decora: se monta. Cada pieza llega a su sitio por una regla
(una zona, una capa, un paso numerado) y la belleza sale de que esas reglas concuerden. La identidad
toma prestado el lenguaje de las láminas técnicas, los planos de montaje y los cuadernos de
agrimensor: papel oscuro, retícula tenue, cotas pequeñas y una sola línea que lleva la mirada de la
estructura al plano.

**Composición.** Dos mitades que cuentan una transformación. A la izquierda, el nombre y lo que
promete. A la derecha, un spec JSON (estructura sin coordenadas) que un tronco convierte en un plano:
una zona punteada, tarjetas en columnas como las que produce ELK, edges ortogonales y una leyenda de
capas, una de ellas apagada. Todo cae sobre la misma retícula y dentro de los márgenes.

**Color.** Un libro de cuentas, no un estado de ánimo. Fondo tinta, blanco hueso para las pocas
palabras, el naranja de draw.io como única señal (el flujo principal y sus pasos) y un verde azulado
para lo que acompaña. Los grises llevan la estructura (retícula, rieles, regla) en valores escalonados.

**Tipografía.** Una serif refinada (Instrument Serif) para el nombre, grande y con aire; una monoespaciada
sobria (Geist Mono) para rótulos, código y cotas, pequeña y espaciada. Ambas con licencia OFL, reducidas
a los glifos usados y embebidas en el SVG.

## Regenerar

```bash
pip install fonttools
python media/banner.py                     # banner.svg y social-preview.svg
# PNG para Settings → Social preview de GitHub (1280×640), con Chromium headless:
chromium --headless --hide-scrollbars --window-size=1280,640 \
  --screenshot=media/social-preview.png media/social-preview.svg
```
