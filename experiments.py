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

world = GridWorld(LAYOUT, agent_starts={1: (19, 14), 2: (1, 0)})
agent = BDIAgent(1, {"world": world, "position": None, "others": {}},
                 desires=[{"type": "GO_TO", "target": (5, 2)}])
agent_2 = BDIAgent(2, {"world": world, "position": None, "others": {}},
                 desires=[{"type": "GO_TO", "target": (5, 8)}])

world.render()
for _ in range(100):
    action = agent.tick(world.perceive(agent.id))
    ok = world.step(agent.id, action)
    agent.feedback(ok)
    world.render()
    if agent.done():
        break
plt.show()