class Shelf:
    def __init__(self, product, quantity=None):
        self.product = product
        self.quantity = quantity    # None = stock infinito (MVP)

    def has_stock(self):
        return self.quantity is None or self.quantity > 0

    def take(self):
        """Saca una unidad. Devuelve el producto, o None si no hay stock."""
        if not self.has_stock():
            return None
        if self.quantity is not None:
            self.quantity -= 1
        return self.product