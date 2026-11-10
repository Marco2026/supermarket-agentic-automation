from world.GridWorld import GridWorld
from agents.BDIAgent import BDIAgent
import matplotlib.pyplot as plt


LAYOUT = """
SFFFFFFFFFFFFFFFFFFS
SFFFFFFFFFFFFFFFFFFS
SFFSSFFSSFFSSFFSSFFS
SFFSSFFSSFFSSFFSSFFS
SFFSSFFSSFFSSFFSSFFS
SFFSSFFSSFFSSFFSSFFS
SFFSSFFSSFFSSFFSSFFS
SFFSSFFSSFFSSFFSSFFS
SFFSSFFSSFFSSFFSSFFS
SFFSSFFSSFFSSFFSSFFS
SFFSSFFSSFFSSFFSSFFS
SFFSSFFSSFFSSFFSSFFS
FFFFFFFFFFFFFFFFFFFF
FFFCFFFCFFFFCFFFCFFF
FFFFFFFFFFFFFFFFFFFF
"""

world = GridWorld(LAYOUT, agent_starts={1: (19, 14)})
world.render()

locations = {}
for pos, shelf in world.shelves.items():
    locations.setdefault(shelf.product, []).append(pos)

cart_pos = (3, 13)
order = {"Product 7": 1, "Product 2": 2}
world.carts[cart_pos].assign_order(order)

agent = BDIAgent(1, {"world": world, "position": None, "others": {}, "carrying": None,
                     "product_locations": locations},
                 desires=[{"type": "FULFILL_ORDER", "cart": cart_pos, "order": order}])

for _ in range(1000):
    action = agent.tick(world.perceive(agent.id))
    ok = world.step(agent.id, action)
    agent.feedback(ok)
    world.render()
    if agent.done():
        break
plt.show()