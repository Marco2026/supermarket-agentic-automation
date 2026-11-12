class Manager:
    """Manager del Contract Net: un carro con un pedido que subasta sus productos.

    Protocolo (cada flecha tarda un tick):
      Manager --CFP--> todos          (lista de tareas abiertas)
      Agente  --PROPOSE--> Manager    (solo si está libre; coste por tarea)
      Manager --ACCEPT--> ganador     (menor coste; como mucho una tarea por agente y ronda)
      Agente  --DONE/FAIL--> Manager  (al depositar el producto / si abandona el plan)
    """
    BID_WINDOW = 2   # ticks entre el CFP y la adjudicación (ida y vuelta)
    COOLDOWN = 5     # ticks mínimos entre rondas si nadie ha terminado ni fallado

    def __init__(self, id, cart_pos, cart, network, contractors):
        self.id = id
        self.cart_pos = cart_pos
        self.cart = cart
        self.network = network
        self.contractors = list(contractors)
        self.tasks = {}                      # task_id -> {"product", "state", "agent"}
        self.bids = []                       # (coste, id_agente, task_id)
        self.t = 0
        self.finished_at = None
        self._round_start = None
        self._last_announce = None

    def assign_order(self, order):
        self.cart.assign_order(order)
        units = [p for p, qty in order.items() for _ in range(qty)]
        self.tasks = {i: {"product": p, "state": "open", "agent": None}
                      for i, p in enumerate(units)}
        self.finished_at = None

    def tick(self):
        self.t += 1
        event = self._read_messages()

        if self._round_start is not None and self.t - self._round_start >= self.BID_WINDOW:
            self._award()
            self._round_start = None

        if self._round_start is None and self._open_tasks():
            if event or self._last_announce is None \
                    or self.t - self._last_announce >= self.COOLDOWN:
                self._announce()

        if self.tasks and self.finished_at is None \
                and all(t["state"] == "done" for t in self.tasks.values()):
            self.cart.deliver_order()
            self.finished_at = self.t

    # ------------------------------------------------------------------
    def _open_tasks(self):
        return {i: t["product"] for i, t in self.tasks.items() if t["state"] == "open"}

    def _read_messages(self):
        event = False                        # DONE/FAIL: hay que re-anunciar ya
        for msg in self.network.receive(self.cart_pos):
            if msg["type"] == "PROPOSE":
                self.bids += [(cost, msg["from"], task_id)
                              for task_id, cost in msg["bids"].items()]
            elif msg["type"] == "DONE":
                self.tasks[msg["task_id"]]["state"] = "done"
                event = True
            elif msg["type"] == "FAIL":
                self.tasks[msg["task_id"]].update(state="open", agent=None)
                event = True
        return event

    def _announce(self):
        self.bids = []
        tasks = self._open_tasks()
        for agent_id in self.contractors:
            self.network.send({"type": "CFP", "from": self.cart_pos, "to": agent_id, "tasks": tasks})
        self._round_start = self._last_announce = self.t

    def _award(self):
        busy = set()
        for cost, agent_id, task_id in sorted(self.bids):    # menor coste primero
            task = self.tasks[task_id]
            if task["state"] != "open" or agent_id in busy:
                continue
            task.update(state="awarded", agent=agent_id)
            busy.add(agent_id)
            self.network.send({"type": "ACCEPT", "from": self.cart_pos, "to": agent_id,
                           "task_id": task_id, "product": task["product"]})
        self.bids = []