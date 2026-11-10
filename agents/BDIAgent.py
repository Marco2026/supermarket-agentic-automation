from .pathfinding import astar, adjacent_floor

DELTAS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
NAMES = {v: k for k, v in DELTAS.items()}


def _manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class BDIAgent:
    MAX_BLOCKED_TICKS = 3   # ticks esperando antes de replanificar

    def __init__(self, agent_id, beliefs, desires=None, intentions=None):
        self.id = agent_id
        self.beliefs = beliefs
        self.desires = desires if desires is not None else []
        self.intentions = intentions if intentions is not None else []
        self.battery = 100
        self.blocked_ticks = 0
        self._last_action = "WAIT"

    # ------------------------------------------------------------------
    # Ciclo principal: lo llama el bucle de simulación una vez por tick
    # ------------------------------------------------------------------
    def tick(self, percept):
        self.perceive(percept)
        proposed = self.deliberate()       # capa deliberativa propone
        action = self.react(proposed)      # capa reactiva valida o sustituye
        self._last_action = action
        return action

    def feedback(self, success):
        """Resultado de la acción en el entorno. Hay que llamarlo tras world.step."""
        action = self._last_action
        if action in DELTAS:                          # movimiento
            if success:
                self.intentions[0]["path"].pop(0)     # el paso se dio: consumirlo
                self.blocked_ticks = 0
            else:
                self._register_block()
        elif isinstance(action, tuple):               # ("PICK", pos) / ("PUT", pos)
            if success:
                self.intentions.pop(0)                # intención cumplida
            else:
                self._abandon(f"{action} ha fallado")

    def done(self):
        return not self.intentions and not self.desires

    # ------------------------------------------------------------------
    # Creencias
    # ------------------------------------------------------------------
    def perceive(self, percept):
        self.beliefs["position"] = percept["position"]
        self.beliefs["others"] = percept["others"]
        self.beliefs["carrying"] = percept["carrying"]

    # ------------------------------------------------------------------
    # Capa deliberativa
    # ------------------------------------------------------------------
    def deliberate(self):
        """Devuelve la acción que propone la intención actual."""
        while True:
            if not self.intentions:
                if not self.desires:
                    return "WAIT"
                self._adopt(self.desires.pop(0))      # deseo -> intenciones
                continue

            current = self.intentions[0]
            kind = current["type"]

            if kind == "FETCH":                       # se expande al llegar su turno
                self.intentions[0:1] = self._expand_fetch(current)

            elif kind == "GO_TO":
                if current["path"] is None:           # ruta perezosa: desde donde estoy ahora
                    current["path"] = self._plan_path(current["target"])
                    if current["path"] is None:
                        self._abandon(f"no hay ruta a {current['target']}")
                        continue
                if not current["path"]:               # ya he llegado
                    self.intentions.pop(0)
                    continue
                x, y = self.beliefs["position"]
                nx, ny = current["path"][0]
                return NAMES[(nx - x, ny - y)]

            elif kind in ("PICK", "PUT"):
                return (kind, current["target"])

            else:
                raise ValueError(f"Intención desconocida: {current}")

    def _adopt(self, desire):
        kind = desire["type"]
        if kind == "GO_TO":
            self.intentions.append({"type": "GO_TO", "target": desire["target"], "path": None})
        elif kind == "FULFILL_ORDER":
            # una intención FETCH por cada unidad pedida (capacidad 1)
            self.intentions += [{"type": "FETCH", "product": p, "cart": desire["cart"]}
                                for p, qty in desire["order"].items() for _ in range(qty)]
        else:
            raise ValueError(f"Deseo desconocido: {desire}")

    def _expand_fetch(self, fetch):
        """FETCH(producto) -> ir a la estantería, coger, ir al carro, depositar."""
        shelves = self.beliefs["product_locations"].get(fetch["product"], [])
        if not shelves:
            self._abandon(f"no hay estantería con {fetch['product']}")
            return []
        shelf = min(shelves, key=lambda s: _manhattan(s, self.beliefs["position"]))
        cart = fetch["cart"]
        return [{"type": "GO_TO", "target": shelf, "path": None},
                {"type": "PICK", "target": shelf},
                {"type": "GO_TO", "target": cart, "path": None},
                {"type": "PUT", "target": cart}]

    def _plan_path(self, target):
        world = self.beliefs["world"]
        return astar(world, self.beliefs["position"], adjacent_floor(world, target))

    def _abandon(self, reason):
        print(f"[agente {self.id}] plan abandonado: {reason}")
        self.intentions.clear()

    # ------------------------------------------------------------------
    # Capa reactiva
    # ------------------------------------------------------------------
    def react(self, action):
        if action not in DELTAS:
            return action
        x, y = self.beliefs["position"]
        dx, dy = DELTAS[action]
        if (x + dx, y + dy) in self.beliefs["others"].values():
            self._register_block()
            return "WAIT"        # no choco: espero y la intención se conserva
        return action

    def _register_block(self):
        self.blocked_ticks += 1
        if self.blocked_ticks >= self.MAX_BLOCKED_TICKS:
            self._replan()

    def _replan(self):
        """Bloqueo persistente: nueva ruta evitando a los demás agentes."""
        current = self.intentions[0]
        world = self.beliefs["world"]
        blocked = set(self.beliefs["others"].values())
        path = astar(world, self.beliefs["position"],
                     adjacent_floor(world, current["target"]), blocked=blocked)
        if path is not None:
            current["path"] = path
            self.blocked_ticks = 0
        # si no hay ruta alternativa, sigue esperando