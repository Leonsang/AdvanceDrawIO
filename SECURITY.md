# Seguridad

## Reportar una vulnerabilidad

Repórtala en privado desde [Security → Report a vulnerability](https://github.com/Leonsang/AdvanceDrawIO/security/advisories/new),
no en un issue público.

## Modelo de amenaza

AdvanceDrawIO corre en tu máquina como un servidor MCP por stdio: no abre puertos. Sus tools las invoca
un LLM, y ese LLM puede estar influido por contenido no confiable (un documento, un diagrama ajeno, una
página web) que intenta que llame una tool con argumentos maliciosos. Por eso los argumentos de las
tools se tratan como entrada no confiable:

- **Rutas hacia draw.io**: se pasan siempre absolutas al CLI, así una ruta no puede colarse como opción
  de Electron/Chromium. `render` solo acepta archivos que existen.
- **Nombres de salida**: `name` es un nombre de archivo, no una ruta; no se puede escribir fuera de `out_dir`.
- **Spec**: se valida completo antes de dibujar, incluidos los ciclos entre zonas (que colgarían el layout).
- **Sandbox de Chromium**: draw.io corre con sandbox. `--no-sandbox` solo se agrega como root (contenedores
  y CI), o si defines `ADVANCEDRAWIO_NO_SANDBOX=1`.
- **`.drawio` comprimidos**: cada página tiene un tope de 50 MB al descomprimirse.
- **XML**: `ElementTree` no resuelve entidades externas (sin XXE).

## Riesgos aceptados

- **Contenido de terceros sin fijar versión.** El índice de iconos y los 770 ejemplos se descargan de los
  repos de jgraph (ramas `main` y `dev`) por HTTPS, sin hash. Si esos repos se comprometieran, su
  contenido llegaría a tus diagramas y al contexto del LLM. Se cachean en `~/.cache/advancedrawio`.
- **draw.io Desktop en sesiones en la nube.** `scripts/setup-cloud.sh` instala el `.deb` del último
  release de GitHub por HTTPS sin verificar checksum. En tu máquina, instala draw.io desde su sitio oficial.
- **Recursos remotos en un diagrama.** Un spec puede incluir un `style` con `image=https://...`; al abrir
  el diagrama, draw.io pide esa URL. Revisa los specs que no escribiste tú antes de compartir el resultado.
