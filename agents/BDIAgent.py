from .pathfinding import astar, adjacent_floor

DELTAS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
NAMES = {v: k for k, v in DELTAS.items()}


class BDIAgent:
    MAX_BLOCKED_TICKS = 3   # ticks esperando antes de replanificar

    def __init__(self, agent_id, beliefs, desires=None, intentions=None):
        self.id = agent_id
        self.beliefs = beliefs        # {"world": ..., "position": None, "others": {}}
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
        if self._last_action not in DELTAS:
            return
        if success:
            self.intentions[0]["path"].pop(0)   # el paso se dio: consumirlo
            self.blocked_ticks = 0
        else:
            self._register_block()

    def done(self):
        return not self.intentions and not self.desires

    # ------------------------------------------------------------------
    # Creencias
    # ------------------------------------------------------------------
    def perceive(self, percept):
        self.beliefs["position"] = percept["position"]
        self.beliefs["others"] = percept["others"]

    # ------------------------------------------------------------------
    # Capa deliberativa
    # ------------------------------------------------------------------
    def deliberate(self):
        """Devuelve la acción que propone la intención actual."""
        while True:
            if self.intentions:
                current = self.intentions[0]
                if current["type"] == "GO_TO":
                    if not current["path"]:          # ya he llegado
                        self.intentions.pop(0)
                        continue
                    x, y = self.beliefs["position"]
                    nx, ny = current["path"][0]
                    return NAMES[(nx - x, ny - y)]
            elif self.desires:
                self._adopt(self.desires.pop(0))     # deseo -> intención
            else:
                return "WAIT"

    def _adopt(self, desire):
        if desire["type"] == "GO_TO":
            if not self.go_to(desire["target"]):
                print(f"[agente {self.id}] deseo imposible, descartado: {desire}")

    def go_to(self, target):
        world = self.beliefs["world"]
        start = self.beliefs["position"]
        path = astar(world, start, adjacent_floor(world, target))
        if path is None:
            return False    # intención imposible, la deliberativa debe reconsiderar
        self.intentions.append({"type": "GO_TO", "target": target, "path": path})
        return True

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