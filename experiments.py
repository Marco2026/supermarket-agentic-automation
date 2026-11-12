from world.GridWorld import GridWorld
from agents.BDIAgent import BDIAgent
import matplotlib.pyplot as plt
import random
from global_config import SEED
from communication.Manager import Manager
from communication.Network import Network


random.seed(SEED)

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

world = GridWorld(LAYOUT, agent_starts={1: (19, 14), 2: (19, 13)})

locations = {shelf.product: pos for pos, shelf in world.shelves.items()}

cart_pos = (3, 13)
order = {"Product 7": 1, "Product 2": 2}

network = Network()
manager = Manager(cart_pos, world.carts[cart_pos], network, contractors=[1, 2])
manager.assign_order(order)

agent_1 = BDIAgent(1, {"world": world, "position": None, "others": {}, "carrying": None,
                     "product_locations": locations},
                 desires=[],
                 network=network)
agent_2 = BDIAgent(2, {"world": world, "position": None, "others": {}, "carrying": None,
                     "product_locations": locations},
                 desires=[],
                 network=network)
agents = [agent_1, agent_2]

for _ in range(1000):
    random.shuffle(agents)      # movimiento aleatorio tiende a ser como si fueran simultáneos
    for agent in agents:
        action = agent.tick(world.perceive(agent.id))
        ok = world.step(agent.id, action)
        agent.feedback(ok)
    manager.tick()
    network.deliver()            # entrega los mensajes enviados durante este tick
    world.render()
    if manager.finished_at is not None:
        break
plt.show()