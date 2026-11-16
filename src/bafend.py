
"""
Half of this is literally just generating fake astronaut data.

This is built so you can get rid of the fake data and easily implement real data from real machines.
"""

import random
from time import sleep, perf_counter

class Astronaut:
    def __init__(self, name, age, base_bpm, base_bo, base_tmp, base_bp, base_rsr):
        # basic info
        self.name = name
        self.age  = age

        # baselines
        self.base_bpm = base_bpm
        self.base_bo  = base_bo
        self.base_tmp = base_tmp
        self.base_bp  = base_bp
        self.base_rsr = base_rsr

        # actual
        self.bpm = self.base_bpm
        self.bo  = self.base_bo
        self.tmp = self.base_tmp
        self.bps, self.bpd = self.base_bp
        self.rsr = self.base_rsr

        # drifts
        self.bpm_drift = random.uniform(-0.02, 0.02)
        self.bo_drift  = random.uniform(-0.001, 0.001)
        self.tmp_drift = random.uniform(-0.0005, 0.0005)
        self.bps_drift = random.uniform(-0.01, 0.01)
        self.bpd_drift = random.uniform(-0.01, 0.01)
        self.rsr_drift = random.uniform(-0.005, 0.005)

        # conditions (for simulation purposes)
        self.conditions = {
            "hypoxia_normal": {
                "effects": {
                    "bo": -0.12,
                    "bpm": 0.5,
                    "rsr": -0.015
                }
            },
            "dehydration": {
                "effects": {
                    "bpm": 0.08,
                    "bps": -0.08,
                    "rsr": 0.03
                }
            },

            "infection_fever": {
                "effects": {
                    "bpm": 0.07,
                    "tmp": 0.025,
                    "rsr": 0.04
                }
            }
        }

        # currently active conditions
        self.active_conditions = set()

        self.DRIFT_MAP = {
            "bpm": "bpm_drift",
            "bo": "bo_drift",
            "tmp": "tmp_drift",
            "bps": "bps_drift",
            "bpd": "bpd_drift",
            "rsr": "rsr_drift"
        }

        # internal stats
        self._dt = 0 # secs
        self._lastUpdateTime = perf_counter()

    def update_health(self):
        # generating random values at runtime because we don't have actual astronauts;
        # you would hook this up to real equipment
        now = perf_counter()
        self._dt = now - self._lastUpdateTime
        self._lastUpdateTime = now

        # bounds
        self.bpm = max(0, self.bpm)
        self.bo = max(0, min(100, self.bo))
        self.tmp = max(0, self.tmp)
        self.bps = max(0, self.bps)
        self.bpd = max(0, self.bpd)
        self.rsr = max(0, self.rsr)

        # aggregate condition effects
        condition_effects = {
            "bpm": 0.0,
            "bo": 0.0,
            "tmp": 0.0,
            "bps": 0.0,
            "bpd": 0.0,
            "rsr": 0.0
        }

        for condition in self.active_conditions:
            effects = self.conditions[condition]["effects"]

            for effect, value in effects.items():
                condition_effects[effect] += value

        # natural drift + condition effects + random variation
        self.bpm = round(random.gauss(
            self.bpm + (self.bpm_drift + condition_effects["bpm"]) * self._dt, 1.5
        ))

        self.bo = round(random.gauss(
            self.bo + (self.bo_drift + condition_effects["bo"]) * self._dt, 0.2
        ), 1)

        self.tmp = round(random.gauss(
            self.tmp + (self.tmp_drift + condition_effects["tmp"]) * self._dt, 0.05
        ), 2)

        self.bps = round(random.gauss(
            self.bps + (self.bps_drift + condition_effects["bps"]) * self._dt, 1
        ))

        self.bpd = round(random.gauss(
            self.bpd + (self.bpd_drift + condition_effects["bpd"]) * self._dt, 1
        ))

        self.rsr = round(random.gauss(
            self.rsr + (self.rsr_drift + condition_effects["rsr"]) * self._dt, 0.5
        ))

    def generate_reading(self):
        return {
            "name": self.name,
            "age": self.age,
            "heart_rate": self.bpm,
            "blood_oxygen": self.bo,
            "temperature": self.tmp,
            "blood_pressure": {
                "systolic": self.bps,
                "diastolic": self.bpd
            },
            "respiratory_rate": self.rsr
        }

    def inflict_condition(self, condition):
        if condition not in self.conditions:
            print(f"Unknown condition: {condition}")
            return

        self.active_conditions.add(condition)
        print(f"Condition activated: {condition}")

    def remove_condition(self, condition):
        self.active_conditions.discard(condition)
        print(f"Condition removed: {condition}")
