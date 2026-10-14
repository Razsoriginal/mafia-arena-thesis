class BaseAgent:
    name = "base"
    def __init__(self, pid):
        self.pid = pid
    def speak(self, role, history) -> str:
        return "I am watching and waiting for evidence."
    def vote(self, role, history, trust) -> tuple[str, dict]:
        return "no-lynch", {}
