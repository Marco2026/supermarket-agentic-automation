# Supermarket Agentic Automation

## Description of Hybrid BDI Agents

BDI Agents are usually composed of three elements: Beliefs, Desires and Intentions. Given that they are hybrid agents, they also present a Layer Structure.

### Layer Structure

Hybrid BDI Agents present a layer structure which acts following a priority order described below.

1. Reactive Layer
2. Deliberative Layer
3. Social Layer

The Reactive layer is the most prioritary, preventing the agent from collisions with other agents. The deliberative layer acts when there is no need to react instantly to an stimulus, planning the route to the next target. The social layer is always active and sends an update of the current state of the agent to the other agents.

### Beliefs, Desires and Intentions

#### Beliefs

Beliefs of a BDI Agent are the information it knows about the elements in its environment. The format in the actual implementation is as follows:

```Python
{
    "world": world,                      # static map (only width, height, get_cell are used).
    "position": (8, 11),                 # agent position.
    "others": {2: (7, 3), 3: (5, 9)},    # position of the other agents {id: (x, y)}.
    "carrying": "Product 7",             # the product the agent is carrying (if it's not carring any, the value is None).
    "product_locations": {               # static knowledge of where it's every product in the map.
        "Product 7": (5, 2),
        "Product 2": (2, 1),
    },
}
```

#### Desires

The desire of a BDI Agent is the objective it is actually trying to accomplish. The format in the actual implementation is as follows:

```Python
[
    {"type": "FULFILL_ORDER",
     "cart": (8, 1),                              # cart assigned to the current order
     "order": {"Product 7": 1, "Product 2": 2}},  # product: quantity
    {"type": "GO_TO", "target": (5, 2)},          # simple desire
]
```

#### Intentions

The intentions of a BDI Agent are the steps it must follow to achieve its desire. The format in the actual implementation is as follows:

```Python
[
    {"type": "GO_TO", "target": (8, 1), "path": [(8, 2), (7, 2)]},  # already planned route
    {"type": "PUT", "target": (8, 1)},                              # interaction action
    {"type": "FETCH", "product": "Product 2", "cart": (8, 1)},      # pending: it expands in its turn
    {"type": "FETCH", "product": "Product 2", "cart": (8, 1)},
]
```

## Communication

1. CFP (manager $\to$ cada agente)
Anuncia las tareas abiertas. Se envía un mensaje a cada contratista en cada ronda.

```python
{"type": "CFP", "from": (3, 13), "to": 1,
 "tasks": {0: "Product 7", 1: "Product 2", 2: "Product 2"}}   # task_id: producto
```

2. PROPOSE (agente $\to$ manager)
Responde al CFP con el coste (pasos hasta la estantería) de cada tarea alcanzable. Solo responde si está libre, y si está ocupado no envía nada.

```python
{"type": "PROPOSE", "from": 1, "to": (3, 13),
 "bids": {0: 14, 1: 22, 2: 22}}                                # task_id: coste
```

3. ACCEPT (manager $\to$ agente ganador)
Adjudica una tarea. Como mucho una por agente y ronda.

```python
{"type": "ACCEPT", "from": (3, 13), "to": 1,
 "task_id": 0, "product": "Product 7"}
```

4. DONE (agente $\to$ manager)
Se envía cuando el agente deposita el producto en el carro (el PUT tiene éxito).

```python
{"type": "DONE", "from": 1, "to": (3, 13), "task_id": 0}
```

5. FAIL (agente $\to$ manager)
Se envía por cada tarea pendiente cuando el agente abandona su plan (por ejemplo, un producto sin estantería o un PICK/PUT fallido). El manager vuelve a abrir la tarea.

```python
{"type": "FAIL", "from": 1, "to": (3, 13), "task_id": 0}
```

Flujo típico de una tarea: CFP → PROPOSE → ACCEPT → DONE, con un tick de retraso entre cada mensaje. FAIL es la alternativa a DONE.
