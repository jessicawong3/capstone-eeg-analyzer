# import random

# def get_fake_prediction():
#     stages = ["Awake", "N1", "N2", "N3", "REM"]
#     pred = random.choice(stages)
#     confidences = {s: random.random() for s in stages}
#     total = sum(confidences.values())
#     confidences = {k: v/total for k, v in confidences.items()}
#     return pred, confidences


import random
import time

STAGES = ["Awake", "N1", "N2", "N3", "REM"]

# Simple Markov transition model for realism
TRANSITIONS = {
    "Awake": ["Awake", "N1"],
    "N1": ["N1", "N2", "Awake"],
    "N2": ["N2", "N3", "REM"],
    "N3": ["N3", "N2"],
    "REM": ["REM", "N1", "Awake"]
}

class MockEEGModel:
    def __init__(self, latency=0.2, seed=None):
        self.current_stage = "Awake"
        self.latency = latency
        if seed is not None:
            random.seed(seed)

    def predict(self, features):
        """
        features: placeholder argument for bandpowers, DWT output, etc.
                  (ignored, but included so the dashboard works unchanged
                   when the real model is dropped in)
        """

        # Simulate processing latency
        time.sleep(self.latency)

        # Transition to a realistic next stage
        self.current_stage = random.choice(TRANSITIONS[self.current_stage])

        # Generate confidence distribution with bias toward the current stage
        raw = {s: random.random() * (3 if s == self.current_stage else 1)
               for s in STAGES}
        total = sum(raw.values())
        confidences = {s: v / total for s, v in raw.items()}

        return self.current_stage, confidences