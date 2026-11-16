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

world = GridWorld(LAYOUT, agent_starts={1: (19, 14), 2: (19, 13), 3: (19, 12)})

locations = {shelf.product: pos for pos, shelf in world.shelves.items()}

cart_1_pos = (3, 13)
cart_2_pos = (7, 13)
cart_3_pos = (12, 13)
cart_4_pos = (16, 13)

network = Network()

agent_1 = BDIAgent(1, {"world": world, "position": None, "others": {}, "carrying": None,
                     "product_locations": locations}, desires=[], network=network)
agent_2 = BDIAgent(2, {"world": world, "position": None, "others": {}, "carrying": None,
                     "product_locations": locations}, desires=[], network=network)
agent_3 = BDIAgent(3, {"world": world, "position": None, "others": {}, "carrying": None,
                     "product_locations": locations}, desires=[], network=network)

agents = [agent_1, agent_2, agent_3]

manager_1 = Manager(cart_1_pos, world.carts[cart_1_pos], network)
manager_2 = Manager(cart_2_pos, world.carts[cart_2_pos], network)
manager_3 = Manager(cart_3_pos, world.carts[cart_3_pos], network)
manager_4 = Manager(cart_4_pos, world.carts[cart_4_pos], network)

managers = [manager_1, manager_2, manager_3, manager_4]

order_1 = {"Product 7": 1, "Product 2": 2}
order_2 = {"Product 9": 2, "Product 15": 1}
order_3 = {"Product 1": 1, "Product 3": 1, "Product 5": 1}
order_4 = {"Product 4": 1, "Product 6": 1, "Product 8": 1, "Product 10": 1}
order_5 = {"Product 11": 1, "Product 12": 1, "Product 13": 1, "Product 14": 1}
order_6 = {"Product 16": 1, "Product 17": 1, "Product 18": 1, "Product 19": 1}

orders = [order_1, order_2, order_3, order_4, order_5, order_6]

manager_1.assign_order(orders.pop(0))
manager_2.assign_order(orders.pop(0))
manager_3.assign_order(orders.pop(0))
manager_4.assign_order(orders.pop(0))

for _ in range(1000):
    random.shuffle(agents)      # movimiento aleatorio tiende a ser como si fueran simultáneos
    random.shuffle(managers)
    for agent in agents:
        action = agent.tick(world.perceive(agent.id))
        ok = world.step(agent.id, action)
        agent.feedback(ok)
    for manager in managers:
        manager.tick()
        if manager.finished_at is not None:
            if len(orders) > 0:
                manager.assign_order(orders.pop(0))
    network.deliver()            # entrega los mensajes enviados durante este tick
    world.render()
    if all(m.finished_at is not None for m in managers):
        break
plt.show()