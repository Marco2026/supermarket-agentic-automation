import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

class GridWorld:

    def __init__(self, grid):
        if not all(len(row) == len(grid[0]) for row in grid):
            raise ValueError("All rows in the grid must have the same length")
        
        self.width = len(grid[0])
        self.height = len(grid)
        self.grid = grid

    def get_cell(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        else:
            raise IndexError("Cell coordinates are out of bounds")

    def render(self, agents=None):
        COLORES = {"F": "#eeeeee", "S": "saddlebrown", "C": "steelblue"}
        fig, ax = plt.subplots()

        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == "N":
                    continue  # no se dibuja nada
                ax.add_patch(Rectangle((x, y), 1, 1,
                                    facecolor=COLORES[cell],
                                    edgecolor="gray", linewidth=1))

        for i, (x, y) in (agents or {}).items():
            ax.text(x + 0.5, y + 0.5, str(i), ha="center", va="center", color="red")

        ax.set_xlim(0, self.width)
        ax.set_ylim(self.height, 0)   # eje y invertido: la fila 0 queda arriba
        ax.set_aspect("equal")
        ax.axis("off")
        plt.show()