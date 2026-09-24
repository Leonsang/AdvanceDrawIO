# Revisión objetiva

Cada diagrama que sale de `build_diagram`, `build_from_mermaid` o `build_from_example` trae un campo
`revision`: un puntaje de 0 a 100 y la lista de problemas, cada uno con su arreglo sugerido. Lo
calcula `lint.py` leyendo la geometría del `.drawio` final, sin mirar la imagen. También está
disponible como tool (`lint_diagram(path)`) y en el CLI.

```json
{"archivo": "plataforma-recaudo.drawio", "nodos": 12, "edges": 12, "puntaje": 92, "aprobado": true,
 "problemas": [{"tipo": "proporcion_extrema", "ratio": 4.2,
                "arreglo": "Cambia 'direction' (RIGHT<->DOWN) o agrupa etapas en zonas..."}]}
```

## Reglas

| Problema | Cuándo | Penalización |
|---|---|---|
| `solape` | Dos nodos se pisan. Es un bug de layout, no del spec. | 30 (y no aprueba) |
| `edge_cruza_nodo` | El recorrido de un edge atraviesa un nodo que no es su origen ni su destino. | 8 por nodo cruzado |
| `nodo_aislado` | Un nodo sin edges. | 5 |
| `zona_casi_vacia` | Una zona (no `external`) con un solo elemento. | 5 |
| `demasiados_nodos` | Más de 25 nodos. | 15 |
| `proporcion_extrema` | El lado largo supera 3,5 veces el corto (con más de 6 nodos). | 8, o 20 si pasa de 5 |

Se **aprueba** con 85 o más y sin solapes. El CI construye todos los ejemplos y falla si alguno de
modo spec queda por debajo (`scripts/galeria.py --min-score 85`).

Las tablas (celdas con `childLayout`, como las de un ER) cuentan como un solo nodo, y el título, la
leyenda y las notas no cuentan.

## Lo que no ve

Un 100 no garantiza un buen diagrama. El linter no detecta:

- una zona que flota porque todos sus edges están en capas ocultas;
- huecos grandes o nodos de una misma zona muy separados;
- un flujo principal que no se puede seguir con el dedo;
- nombres genéricos ("Servicio 1") o técnicos para un público de negocio.

Por eso el agente mira también el PNG que devuelve cada build. El proceso y el playbook están en [agent.md](../src/advancedrawio/agent.md).

## El ciclo en la práctica

Así se corrigieron los ejemplos de la [galería](galeria/README.md), siguiendo el playbook del agente:

| Ejemplo | Antes | Cambio | Después |
|---|---|---|---|
| Plataforma de datos de recaudo | 92 · proporción 4,2 | `direction: DOWN` | 100 |
| Plataforma IA GCP | 80 · proporción 7,3 | `direction: DOWN` | 100 |
| Multiagente GCP | 80 · proporción 5,7 | `direction: DOWN` | 100 |
| Cómo funciona | 92 · proporción 4,7 | `DOWN` y la revisión como paso del pipeline | 100 |
| AWS serverless | 75 · zona casi vacía, proporción 5,6 | fusionar `AWS Cloud` con la región, capas secundarias visibles, fan-out en EventBridge y una columna menos | 92 · proporción 4,8 |

En AWS, `DOWN` empeoró la proporción (9,6) porque la cadena es larga y lineal, así que se volvió a
`RIGHT`, como dice el playbook cuando una iteración empeora. Lo que sí funcionó fue cambiar la forma
del flujo en vez de la dirección: una segunda rama en paralelo (EventBridge → facturación y
notificación) agrega alto sin agregar largo, y quitar un salto innecesario (la cola entre EventBridge
y la Lambda) y un edge de observabilidad que abría una columna extra acortó el ancho.
