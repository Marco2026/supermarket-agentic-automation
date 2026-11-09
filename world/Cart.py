from collections import Counter


class Cart:
    def __init__(self, order=None):
        self.order = Counter(order or {})   # lo que hay que comprar
        self.content = Counter()            # lo que ya está en el carro

    def assign_order(self, order):
        if self.order and not self.is_complete():
            raise ValueError("El carro tiene un pedido sin completar")
        self.order = Counter(order)
        self.content = Counter()

    def missing(self):
        """Lo que falta por depositar (Counter vacío si está completo)."""
        return self.order - self.content

    def is_complete(self):
        return bool(self.order) and not self.missing()

    def store(self, product):
        """Deposita un producto. Devuelve False si el pedido no lo necesita."""
        if self.missing()[product] <= 0:
            return False
        self.content[product] += 1
        return True

    def deliver_order(self):
        """Entrega el pedido completo y deja el carro libre."""
        if not self.is_complete():
            raise ValueError("El pedido no está completo")
        delivered = dict(self.content)
        self.order = Counter()
        self.content = Counter()
        return delivered