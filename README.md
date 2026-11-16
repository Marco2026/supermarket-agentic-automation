# Supermarket Agentic Automation

## Description of Hybrid BDI Agents

BDI Agents are usually composed of three elements: Beliefs, Desires and Intentions. Given that they are hybrid agents, they also present a Layer Structure.

### Layer Structure

Hybrid BDI Agents present a layer structure which acts following a priority order described below.

1. Reactive Layer
2. Deliberative Layer
3. Social Layer

The Reactive layer is the most prioritary, preventing the agent from collisions with other agents. The deliberative layer acts when there is no need to react instantly to an stimulus, planning the route to the next target. The social layer is always active and sends an update of the current state of the agent to the other agents.

### Beliefs, Desires and Intentions

#### Beliefs

Beliefs of a BDI Agent are the information it knows about the elements in its environment. The format in the actual implementation is as follows:

```Python
{
    "world": world,                      # static map (only width, height, get_cell are used).
    "position": (8, 11),                 # agent position.
    "others": {2: (7, 3), 3: (5, 9)},    # position of the other agents {id: (x, y)}.
    "carrying": "Product 7",             # the product the agent is carrying (if it's not carring any, the value is None).
    "product_locations": {               # static knowledge of where it's every product in the map.
        "Product 7": (5, 2),
        "Product 2": (2, 1),
    },
}
```

#### Desires

The desire of a BDI Agent is the objective it is actually trying to accomplish. The format in the actual implementation is as follows:

```Python
[
    {"type": "FULFILL_ORDER",
     "cart": (8, 1),                              # cart assigned to the current order
     "order": {"Product 7": 1, "Product 2": 2}},  # product: quantity
    {"type": "GO_TO", "target": (5, 2)},          # simple desire
]
```

#### Intentions

The intentions of a BDI Agent are the steps it must follow to achieve its desire. The format in the actual implementation is as follows:

```Python
[
    {"type": "GO_TO", "target": (8, 1), "path": [(8, 2), (7, 2)]},  # already planned route
    {"type": "PUT", "target": (8, 1)},                              # interaction action
    {"type": "FETCH", "product": "Product 2", "cart": (8, 1)},      # pending: it expands in its turn
    {"type": "FETCH", "product": "Product 2", "cart": (8, 1)},
]
```

## Communication

Agents communicate through a synchronous `Network`: messages sent during a tick are delivered at the end of that tick and read in the next one, so no agent benefits from the order in which agents are executed. The total number of messages is counted in `network.sent` (a broadcast counts as one message per agent).

The protocol is a Contract Net where each cart is managed by a `Manager` and the agents act as contractors. Managers are identified by the position of their cart, `(x, y)`, and agents by their integer id. A manager starts with no agents assigned. Agents start with no desires either: their work arrives as tasks assigned by a manager (the `FULFILL_ORDER` desire is only used by the baseline agent, which works alone and has no network).

Communication has two levels:

1. **Recruitment**: a manager asks all the agents to join its order, and builds a team.
2. **Task allocation**: the manager and the members of its team run a Contract Net to decide who fetches each product.

### Level 1: Recruitment (manager $\leftrightarrow$ all agents)

A manager asks for as many agents as products are still pending, up to a limit (`max_team`, 4 by default). Only agents that are free answer: they are not in a team, they have no intentions and they are not carrying any product.

1. RECRUIT (manager $\to$ every agent)
Asks for agents to join the team. It is a broadcast, so one message is sent to each agent. `slots` is the number of agents the manager still needs.

```python
{"type": "RECRUIT", "from": (3, 13), "to": 1, "slots": 3}
```

2. OFFER (agent $\to$ manager)
Answer of a free agent to a RECRUIT. The cost is the number of steps to reach the cart. Busy agents do not answer.

```python
{"type": "OFFER", "from": 1, "to": (3, 13), "cost": 14}
```

3. ENROLL (manager $\to$ selected agents)
The manager enrolls the offers with the lowest cost, up to the number of slots. From this moment the agent belongs to the team of that manager.

```python
{"type": "ENROLL", "from": (3, 13), "to": 1}
```

4. DECLINE (agent $\to$ manager)
Sent when an agent cannot join. If several managers enroll the same agent at the same time, it joins the one with the lowest offered cost and declines the rest. An agent that is already in a team declines every new ENROLL. The manager removes the agent from its team and recruits again.

```python
{"type": "DECLINE", "from": 1, "to": (7, 13)}
```

5. RELEASE (manager $\to$ agent)
The agent leaves the team and becomes free for other managers. It is sent to the idle members that are no longer needed (for example, when 2 products are pending and the team has 4 agents, the 2 members without a task are released) and to the whole team when the order is complete.

```python
{"type": "RELEASE", "from": (3, 13), "to": 2}
```

### Level 2: Task allocation (manager $\leftrightarrow$ its team)

Each unit of a product in the order is a task. The manager only talks to the members of its team that have no task assigned.

6. CFP (manager $\to$ idle team members)
Announces the open tasks.

```python
{"type": "CFP", "from": (3, 13), "to": 1,
 "tasks": {0: "Product 7", 1: "Product 2", 2: "Product 2"}}   # task_id: product
```

7. PROPOSE (agent $\to$ manager)
Answer to a CFP with the cost (steps to the shelf) of every reachable task. It is only sent if the CFP comes from the agent's manager and the agent has no task; otherwise the agent does not answer.

```python
{"type": "PROPOSE", "from": 1, "to": (3, 13),
 "bids": {0: 14, 1: 22, 2: 22}}                                # task_id: cost
```

8. ACCEPT (manager $\to$ winning agent)
Assigns a task. Offers are sorted by cost and every agent gets at most one task per round.

```python
{"type": "ACCEPT", "from": (3, 13), "to": 1,
 "task_id": 0, "product": "Product 7"}
```

9. DONE (agent $\to$ manager)
Sent when the agent puts the product in the cart (the PUT succeeds). The agent stays in the team until it is released.

```python
{"type": "DONE", "from": 1, "to": (3, 13), "task_id": 0}
```

10. FAIL (agent $\to$ manager)
Sent for every pending task when the agent abandons its plan (for example, a product without a shelf or a failed PICK/PUT). The manager reopens the task and announces it again.

```python
{"type": "FAIL", "from": 1, "to": (3, 13), "task_id": 0}
```

### Message flow

Typical life of an agent in a team: RECRUIT → OFFER → ENROLL → CFP → PROPOSE → ACCEPT → DONE → RELEASE. Every message takes one tick to arrive, and the manager waits 2 ticks (`BID_WINDOW`) to collect the answers of a round, so an agent starts moving about five ticks after the first RECRUIT. When recruitment or allocation rounds do not succeed (for example, no agent is free), the manager repeats them every 5 ticks (`COOLDOWN`), or immediately after a DONE, FAIL or DECLINE.

There are no REJECT or REFUSE messages (agents that lose a bid or are busy do not receive or send anything), and there are no messages between agents: all the communication goes through a manager.