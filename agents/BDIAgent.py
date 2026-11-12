from .pathfinding import astar, adjacent_floor
import random
from global_config import SEED


random.seed(SEED)

DELTAS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
NAMES = {v: k for k, v in DELTAS.items()}


class BDIAgent:
    MAX_BLOCKED_TICKS = 3   # ticks esperando antes de replanificar

    def __init__(self, agent_id, beliefs, desires=None, intentions=None, network=None):
        self.id = agent_id
        self.network = network
        # beliefs: {"world": ..., "position": None, "others": {}, "carrying": None,
        #           "product_locations": {producto: (x, y)}}
        self.beliefs = beliefs
        self.desires = desires if desires is not None else []
        self.intentions = intentions if intentions is not None else []
        self.battery = 100
        self.blocked_ticks = 0
        self._last_action = "WAIT"
        self._source = None          # "reactive" | "deliberative"

    # ------------------------------------------------------------------
    # Ciclo principal: lo llama el bucle de simulación una vez por tick
    # ------------------------------------------------------------------
    def tick(self, percept):
        self.perceive(percept)
        self.social()                       # actualiza creencias sobre otros agentes
        action, source = self.react(), "reactive"
        if action is None:                       # ninguna regla reactiva se dispara
            action, source = self.deliberate(), "deliberative"
        self._last_action, self._source = action, source
        return action

    def feedback(self, success):
        """Resultado de la acción en el entorno. Hay que llamarlo tras world.step.
        Además de registrar el resultado, deja preparado el plan del siguiente tick
        (siguiente celda, intención expandida...), para que react() pueda ir primero."""
        action = self._last_action
        if success and action in DELTAS:         # sé que me he movido: actualizo mi posición
            x, y = self.beliefs["position"]
            dx, dy = DELTAS[action]
            self.beliefs["position"] = (x + dx, y + dy)

        if self._source == "deliberative":
            if action in DELTAS:                 # movimiento
                if success:
                    self.intentions[0]["path"].pop(0)
                    self.blocked_ticks = 0
                else:
                    self._register_block()
            elif isinstance(action, tuple):      # ("PICK", pos) / ("PUT", pos)
                if success:
                    done = self.intentions.pop(0)
                    if self.network is not None and done.get("task_id") is not None:
                        self.network.send({"type": "DONE", "from": self.id,
                                           "to": done["target"], "task_id": done["task_id"]})
                else:
                    self._abandon(f"{action} ha fallado")
        elif success and action in DELTAS:       # me movió la reactiva: la ruta ya no vale
            if self.intentions and self.intentions[0]["type"] == "GO_TO":
                self.intentions[0]["path"] = None

        self.update_intentions()                 # prepara el siguiente tick

    def prime(self, percept):
        """Prepara el primer tick (posición inicial y primer plan). Llamar una vez
        al crear el agente, y también al darle trabajo estando ocioso."""
        self.perceive(percept)
        self.update_intentions()

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
    # Capa reactiva:
    # ------------------------------------------------------------------
    def react(self):
        # Regla: no entrar en una celda ocupada por otro agente
        if self._next_cell() in self.beliefs["others"].values():
            self._register_block()
            return "WAIT"                        # la intención se conserva
        return None

    def _next_cell(self):
        """Celda a la que me llevaría el plan este tick (sin efectos secundarios)."""
        if self.intentions and self.intentions[0]["type"] == "GO_TO":
            return self.intentions[0]["path"][0]
        return None

    def _register_block(self):
        self.blocked_ticks += 1
        move_prob = 0.3
        rng = random.random()
        if self.blocked_ticks >= self.MAX_BLOCKED_TICKS or rng < move_prob:
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

    # ------------------------------------------------------------------
    # Capa deliberativa
    # ------------------------------------------------------------------
    def update_intentions(self):
        """Adopta deseos, expande FETCH, planifica rutas y descarta intenciones
        cumplidas. Al terminar, intentions[0] es una intención lista para actuar
        (GO_TO con ruta no vacía, PICK o PUT), o no queda ninguna."""
        while True:
            if not self.intentions:
                if not self.desires:
                    return
                self._adopt(self.desires.pop(0))     # deseo -> intenciones
                continue

            current = self.intentions[0]
            kind = current["type"]

            if kind == "FETCH":                      # se expande al llegar su turno
                self.intentions[0:1] = self._expand_fetch(current)

            elif kind == "GO_TO":
                if current["path"] is None:          # ruta perezosa: desde donde estoy
                    current["path"] = self._plan_path(current["target"])
                    if current["path"] is None:
                        self._abandon(f"no hay ruta a {current['target']}")
                        continue
                if not current["path"]:              # ya he llegado
                    self.intentions.pop(0)
                    continue
                return

            elif kind in ("PICK", "PUT"):
                return

            else:
                raise ValueError(f"Intención desconocida: {current}")

    def deliberate(self):
        """Acción que propone la intención actual."""
        self.update_intentions()                     # normalmente no hace nada (ya está listo)
        if not self.intentions:
            return "WAIT"
        current = self.intentions[0]
        if current["type"] == "GO_TO":
            x, y = self.beliefs["position"]
            nx, ny = current["path"][0]
            return NAMES[(nx - x, ny - y)]
        return (current["type"], current["target"])  # PICK / PUT

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
        shelf = self.beliefs["product_locations"].get(fetch["product"])
        if shelf is None:
            self._abandon(f"no hay estantería con {fetch['product']}")
            return []
        cart = fetch["cart"]
        return [{"type": "GO_TO", "target": shelf, "path": None},
                {"type": "PICK", "target": shelf},
                {"type": "GO_TO", "target": cart, "path": None},
                {"type": "PUT", "target": cart, "task_id": fetch.get("task_id")}]

    def _plan_path(self, target):
        world = self.beliefs["world"]
        return astar(world, self.beliefs["position"], adjacent_floor(world, target))

    def _abandon(self, reason):
        print(f"[agente {self.id}] plan abandonado: {reason}")
        if self.network is not None:                 # avisa a los managers de las tareas perdidas
            for i in self.intentions:
                if i["type"] in ("FETCH", "PUT") and i.get("task_id") is not None:
                    cart = i["cart"] if i["type"] == "FETCH" else i["target"]
                    self.network.send({"type": "FAIL", "from": self.id, "to": cart,
                                   "task_id": i["task_id"]})
        self.intentions.clear()

    # ------------------------------------------------------------------
    # Capa social
    # ------------------------------------------------------------------
    def social(self):
        if self.network is None:
            return
        for msg in self.network.receive(self.id):
            if msg["type"] == "CFP":
                self._bid(msg)
            elif msg["type"] == "ACCEPT":
                self.intentions.append({"type": "FETCH", "product": msg["product"],
                                        "cart": msg["from"], "task_id": msg["task_id"]})
        self.update_intentions()                 # tocar intenciones => dejar el plan listo
 
    def _bid(self, cfp):
        if not self.done() or self.beliefs["carrying"] is not None:
            return                               # ocupado: no puja
        bids = {}
        for task_id, product in cfp["tasks"].items():
            cost = self._estimate_cost(product)
            if cost is not None:
                bids[task_id] = cost
        if bids:
            self.network.send({"type": "PROPOSE", "from": self.id, "to": cfp["from"], "bids": bids})
 
    def _estimate_cost(self, product):
        """Pasos hasta la estantería."""
        world, pos = self.beliefs["world"], self.beliefs["position"]
        shelf = self.beliefs["product_locations"].get(product)
        if shelf is None:
            return None
        leg1 = astar(world, pos, adjacent_floor(world, shelf))
        return None if leg1 is None else len(leg1)
