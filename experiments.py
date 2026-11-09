from world.GridWorld import GridWorld

test_grid = [
    ["F", "F", "F", "F", "F", "F", "F", "F", "F", "F"],
    ["F", "S", "S", "F", "F", "S", "S", "F", "C", "F"],
    ["F", "S", "S", "F", "F", "S", "S", "F", "F", "F"],
    ["F", "S", "S", "F", "F", "S", "S", "F", "C", "F"],
    ["F", "F", "F", "F", "F", "F", "F", "F", "F", "N"],
]

world = GridWorld(test_grid)
world.render()