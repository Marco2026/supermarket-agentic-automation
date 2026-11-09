import heapq

# Convención (x, y), igual que GridWorld.get_cell(x, y). La fila 0 está arriba.
DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # arriba, abajo, izquierda, derecha
WALKABLE = {"F"}  # solo el suelo es transitable


def adjacent_floor(world, target):
    """Celdas de suelo desde las que se puede interactuar con `target` (S o C)."""
    tx, ty = target
    cells = []
    for dx, dy in DIRECTIONS:
        x, y = tx + dx, ty + dy
        if 0 <= x < world.width and 0 <= y < world.height \
                and world.get_cell(x, y) in WALKABLE:
            cells.append((x, y))
    return cells


def astar(world, start, goals, blocked=frozenset()):
    """
    Camino más corto de `start` a cualquiera de las celdas de `goals`.

    world:   GridWorld (usa width, height y get_cell)
    start:   (x, y)
    goals:   iterable de (x, y); basta con llegar a una
    blocked: celdas temporalmente ocupadas (por ejemplo, otros agentes)

    Devuelve la lista de celdas a recorrer SIN incluir `start`,
    [] si ya está en un objetivo, o None si no hay camino.
    """
    goals = set(goals)
    if not goals:
        return None

    def h(p):  # Manhattan al objetivo más cercano: admisible y consistente
        return min(abs(p[0] - gx) + abs(p[1] - gy) for gx, gy in goals)

    open_heap = [(h(start), 0, start)]      # (f, g, celda)
    g_cost = {start: 0}
    came_from = {}

    while open_heap:
        _, g, current = heapq.heappop(open_heap)
        if g > g_cost[current]:
            continue                        # entrada obsoleta del heap

        if current in goals:
            path = []
            while current != start:
                path.append(current)
                current = came_from[current]
            return path[::-1]

        for dx, dy in DIRECTIONS:
            nb = (current[0] + dx, current[1] + dy)
            if not (0 <= nb[0] < world.width and 0 <= nb[1] < world.height):
                continue
            if world.get_cell(*nb) not in WALKABLE or nb in blocked:
                continue
            new_g = g + 1
            if new_g < g_cost.get(nb, float("inf")):
                g_cost[nb] = new_g
                came_from[nb] = current
                heapq.heappush(open_heap, (new_g + h(nb), new_g, nb))

    return None


def path_to_moves(start, path):
    """Convierte una lista de celdas en una lista de movimientos (dx, dy)."""
    moves, prev = [], start
    for cell in path:
        moves.append((cell[0] - prev[0], cell[1] - prev[1]))
        prev = cell
    return moves