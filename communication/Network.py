from collections import defaultdict


class Network:
    """Canal de mensajes síncrono. Lo enviado durante un tick se entrega con
    deliver() al final de ese tick y se lee en el siguiente, así que ningún
    agente se beneficia de su posición en el orden de ejecución."""

    def __init__(self):
        self._pending = []
        self._inboxes = defaultdict(list)
        self.agents = set()                 # ids de agentes registrados (destinatarios de broadcast)
        self.sent = 0                       # métrica: mensajes intercambiados

    def register(self, agent_id):
        self.agents.add(agent_id)

    def send(self, msg):
        """msg: dict con al menos "type", "from" y "to"."""
        self._pending.append(msg)
        self.sent += 1

    def broadcast(self, msg):
        """Un mensaje a cada agente registrado (cuenta como un mensaje por destinatario)."""
        for agent_id in sorted(self.agents):
            self.send({**msg, "to": agent_id})

    def deliver(self):
        for msg in self._pending:
            self._inboxes[msg["to"]].append(msg)
        self._pending.clear()

    def receive(self, receiver_id):
        msgs, self._inboxes[receiver_id] = self._inboxes[receiver_id], []
        return msgs