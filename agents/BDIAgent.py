class BDIAgent:
    def __init__(self, beliefs, desires, intentions):
        self.beliefs = beliefs
        self.desires = desires
        self.intentions = intentions

    def go