import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from .Shelf import Shelf
from .Cart import Cart

COLORS = {"F": "#eeeeee", "S": "saddlebrown", "C": "steelblue"}
VALID_CELLS = set("FSCN")

# Acciones de movimiento: (dx, dy). La fila 0 está arriba.
MOVES = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
    "WAIT": (0, 0)
}


class GridWorld:
    def __init__(self, grid, agent_starts=None):
        if isinstance(grid, str):
            grid = [line.strip() for line in grid.strip().splitlines() if line.strip()]

        if not all(len(row) == len(grid[0]) for row in grid):
            raise ValueError("All rows in the grid must have the same length")

        invalid = {c for row in grid for c in row} - VALID_CELLS
        if invalid:
            raise ValueError(f"Invalid cells in grid: {invalid}")

        self.width = len(grid[0])
        self.height = len(grid)
        self.grid = grid

        self.agents = {}                 # id_agente -> (x, y)
        self.carrying = {}
        self._initial_positions = {}

        self.shelves = {}
        self.carts = {}
        self.load_shelves_and_carts()

        self._fig = None                 # figura de matplotlib (se crea al hacer render)
        self._ax = None
        self._agent_artists = []

        if agent_starts is not None:
            self.spawn_agents(agent_starts)

    # ------------------------------------------------------------------
    # Consulta del mapa
    # ------------------------------------------------------------------
    def get_cell(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        raise IndexError("Cell coordinates are out of bounds")

    def _adjacent(self, agent_id, target):
        x, y = self.agents[agent_id]
        return abs(x - target[0]) + abs(y - target[1]) == 1 

    # ------------------------------------------------------------------
    # Agentes
    # ------------------------------------------------------------------
    def spawn_agents(self, starts):
        """
        starts: dict {id: (x, y)} o lista de posiciones [(x, y), ...] (ids 0, 1, ...).
        Se llama una vez al crear el mundo; los agentes no aparecen ni desaparecen después.
        """
        if not isinstance(starts, dict):
            starts = dict(enumerate(starts))

        positions = list(starts.values())
        if len(set(positions)) != len(positions):
            raise ValueError("Dos agentes comparten posición inicial")
        for aid, (x, y) in starts.items():
            if not (0 <= x < self.width and 0 <= y < self.height):
                raise ValueError(f"Agente {aid}: {(x, y)} fuera del mapa")
            if self.grid[y][x] != "F":
                raise ValueError(f"Agente {aid}: {(x, y)} no es suelo (F)")

        self._initial_positions = dict(starts)
        self.agents = dict(starts)
        self.carrying = {a: None for a in starts}

    def reset(self):
        self.agents = dict(self._initial_positions)
        self.carrying = {a: None for a in self._initial_positions}

    def perceive(self, agent_id):
        """Lo único que el agente puede saber del estado dinámico del mundo."""
        return {
            "position": self.agents[agent_id],
            "others": {a: p for a, p in self.agents.items() if a != agent_id},
            "carrying": self.carrying[agent_id]
        }

    def step(self, agent_id, action):
        """
        Ejecuta la acción de un agente. Devuelve True si tuvo éxito.
        Un movimiento fallido (pared, estantería, borde u otro agente) no mueve al agente:
        es información útil para la capa reactiva.
        """
        if isinstance(action, tuple):
            kind, target = action
            if kind == "PICK":
                return self._pick(agent_id, target)
            elif kind == "PUT":
                return self._put(agent_id, target)
            
        if action not in MOVES:
            raise ValueError(f"Acción desconocida: {action}")

        dx, dy = MOVES[action]
        x, y = self.agents[agent_id]
        nx, ny = x + dx, y + dy

        if action == "WAIT":
            return True
        if not (0 <= nx < self.width and 0 <= ny < self.height):
            return False
        if self.grid[ny][nx] != "F":
            return False
        if (nx, ny) in self.agents.values():
            return False

        self.agents[agent_id] = (nx, ny)
        return True

    def _pick(self, agent_id, target):
        shelf = self.shelves.get(target)
        if shelf is None or self.carrying[agent_id] is not None \
                or not self._adjacent(agent_id, target):
            return False
        product = shelf.pick()
        self.carrying[agent_id] = product
        return product is not None

    def _put(self, agent_id, target):
        cart, product = self.carts.get(target), self.carrying[agent_id]
        if cart is None or product is None or not self._adjacent(agent_id, target):
            return False
        if not cart.store(product):
            return False
        self.carrying[agent_id] = None
        return True

    # ------------------------------------------------------------------
    # Initialize world
    # ------------------------------------------------------------------
    def load_shelves_and_carts(self):
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == "S":
                    sid = len(self.shelves) + 1
                    self.shelves[(x, y)] = Shelf(sid, f"Product {sid}")
                elif cell == "C":
                    cid = len(self.carts) + 1
                    self.carts[(x, y)] = Cart(cid, None)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def _draw_static(self):
        """Dibuja el terreno una sola vez."""
        self._fig, self._ax = plt.subplots()
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == "N":
                    continue  # no se dibuja nada
                self._ax.add_patch(Rectangle((x, y), 1, 1,
                                             facecolor=COLORS[cell],
                                             edgecolor="gray", linewidth=1))
        self._ax.set_xlim(0, self.width)
        self._ax.set_ylim(self.height, 0)   # eje y invertido: la fila 0 queda arriba
        self._ax.set_aspect("equal")
        self._ax.axis("off")

    def render(self, pause=0.2):
        """
        Redibuja solo los agentes sobre la misma ventana.
        Llama a render() en cada tick; al terminar la simulación usa plt.show()
        para mantener la ventana abierta.
        """
        if self._fig is None or not plt.fignum_exists(self._fig.number):
            self._draw_static()
            self._agent_artists = []

        for artist in self._agent_artists:
            artist.remove()
        self._agent_artists = []

        for aid, (x, y) in self.agents.items():
            circle = Circle((x + 0.5, y + 0.5), 0.35, facecolor="tomato",
                            edgecolor="darkred", zorder=3)
            label = self._ax.text(x + 0.5, y + 0.5, str(aid), ha="center",
                                  va="center", color="white", zorder=4)
            self._ax.add_patch(circle)
            self._agent_artists += [circle, label]

        self._fig.canvas.draw_idle()
        plt.pause(pause)