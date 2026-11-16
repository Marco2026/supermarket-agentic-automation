class Manager:
    """Manager de un carro. Dos niveles de comunicación:

    Nivel 1, reclutamiento (manager <-> todos los agentes):
      RECRUIT (broadcast) -> OFFER (si libre, con coste) -> ENROLL (los mejores)
      -> DECLINE (si el agente ya se ha comprometido con otro manager)
    Nivel 2, reparto de tareas (manager <-> su equipo), Contract Net:
      CFP -> PROPOSE -> ACCEPT -> DONE / FAIL
    Al sobrar agentes (quedan menos productos que miembros ociosos) o al terminar:
      RELEASE, y esos agentes quedan libres para otros managers.
    """
    BID_WINDOW = 2   # ticks entre la petición y la decisión (ida y vuelta)
    COOLDOWN = 5     # ticks mínimos entre rondas repetidas si no ha pasado nada nuevo

    def __init__(self, pos, cart, network, max_team=4):
        self.id = pos                        # el carro se identifica por su posición
        self.cart = cart
        self.network = network
        self.max_team = max_team
        self.team = set()                    # empieza sin agentes
        self.tasks = {}                      # task_id -> {"product", "state", "agent"}
        self.offers = []                     # (coste, id_agente)
        self.bids = []                       # (coste, id_agente, task_id)
        self.t = 0
        self.finished_at = None
        self._recruit_start = self._last_recruit = None
        self._cfp_start = self._last_cfp = None

    def assign_order(self, order):
        self.cart.assign_order(order)
        units = [p for p, qty in order.items() for _ in range(qty)]
        self.tasks = {i: {"product": p, "state": "open", "agent": None}
                      for i, p in enumerate(units)}
        self.finished_at = None

    def tick(self):
        if self.finished_at is not None:
            return
        self.t += 1
        event = self._read_messages()

        enrolled = False
        if self._recruit_start is not None and self.t - self._recruit_start >= self.BID_WINDOW:
            enrolled = self._enroll()
            self._recruit_start = None
        if self._cfp_start is not None and self.t - self._cfp_start >= self.BID_WINDOW:
            self._award()
            self._cfp_start = None

        if self.tasks and self._pending() == 0:
            self._finish()
            return
        self._release_surplus()
        self._maybe_recruit(event)
        self._maybe_announce(event or enrolled)

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------
    def _open_tasks(self):
        return {i: t["product"] for i, t in self.tasks.items() if t["state"] == "open"}

    def _pending(self):
        return sum(t["state"] != "done" for t in self.tasks.values())

    def _busy(self):
        return {t["agent"] for t in self.tasks.values() if t["state"] == "awarded"}

    def _target_size(self):
        """Tantos agentes como productos pendientes, hasta max_team."""
        return min(self.max_team, self._pending())

    def _read_messages(self):
        event = False                        # algo ha cambiado: conviene actuar ya
        for msg in self.network.receive(self.id):
            kind = msg["type"]
            if kind == "OFFER":
                self.offers.append((msg["cost"], msg["from"]))
            elif kind == "DECLINE":
                self.team.discard(msg["from"])
                event = True
            elif kind == "PROPOSE":
                self.bids += [(cost, msg["from"], task_id)
                              for task_id, cost in msg["bids"].items()]
            elif kind == "DONE":
                self.tasks[msg["task_id"]]["state"] = "done"
                event = True
            elif kind == "FAIL":
                self.tasks[msg["task_id"]].update(state="open", agent=None)
                event = True
        return event

    # ------------------------------------------------------------------
    # Nivel 1: reclutamiento y liberación
    # ------------------------------------------------------------------
    def _maybe_recruit(self, event):
        if self._recruit_start is not None or len(self.team) >= self._target_size():
            return
        if event or self._last_recruit is None or self.t - self._last_recruit >= self.COOLDOWN:
            self.offers = []
            self.network.broadcast({"type": "RECRUIT", "from": self.id,
                                "slots": self._target_size() - len(self.team)})
            self._recruit_start = self._last_recruit = self.t

    def _enroll(self):
        slots = self._target_size() - len(self.team)
        chosen = sorted(self.offers)[:max(slots, 0)]          # menor coste primero
        for _, agent_id in chosen:
            self.team.add(agent_id)
            self.network.send({"type": "ENROLL", "from": self.id, "to": agent_id})
        self.offers = []
        return bool(chosen)

    def _release_surplus(self):
        """Si hay más miembros ociosos que tareas abiertas, libera los que sobran."""
        idle = sorted(self.team - self._busy())
        surplus = len(idle) - len(self._open_tasks())
        for agent_id in idle[::-1][:max(surplus, 0)]:
            self._release(agent_id)

    def _release(self, agent_id):
        self.team.discard(agent_id)
        self.network.send({"type": "RELEASE", "from": self.id, "to": agent_id})

    def _finish(self):
        self.cart.deliver_order()
        for agent_id in sorted(self.team):
            self._release(agent_id)
        self.finished_at = self.t

    # ------------------------------------------------------------------
    # Nivel 2: reparto de tareas entre los miembros del equipo
    # ------------------------------------------------------------------
    def _maybe_announce(self, urgent):
        if self._cfp_start is not None:
            return
        idle, tasks = self.team - self._busy(), self._open_tasks()
        if not idle or not tasks:
            return
        if urgent or self._last_cfp is None or self.t - self._last_cfp >= self.COOLDOWN:
            self.bids = []
            for agent_id in sorted(idle):
                self.network.send({"type": "CFP", "from": self.id, "to": agent_id, "tasks": tasks})
            self._cfp_start = self._last_cfp = self.t

    def _award(self):
        busy = set()
        for cost, agent_id, task_id in sorted(self.bids):    # menor coste primero
            task = self.tasks[task_id]
            if task["state"] != "open" or agent_id in busy or agent_id not in self.team:
                continue
            task.update(state="awarded", agent=agent_id)
            busy.add(agent_id)
            self.network.send({"type": "ACCEPT", "from": self.id, "to": agent_id,
                           "task_id": task_id, "product": task["product"]})
        self.bids = []