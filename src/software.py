"""
Half of this is literally just generating fake astronaut data.
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

        # conditions (for simulation purposes)
        self.conditions = {
            "hypoxia_normal": {
                "effects": {
                    "bo": 1,
                    "bpm": 2,
                    "rsr": -1
                }
            }
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

        print(self._dt)

        self.bpm = round(random.gauss(self.bpm + self.bpm_drift * self.dt, 1.5))
        self.bo  = round(random.gauss(self.bo  + self.bo_drift  * self.dt, 0.2), 1)
        self.tmp = round(random.gauss(self.tmp + self.tmp_drift * self.dt, 0.05), 2)
        self.bps = round(random.gauss(self.bps + self.bps_drift * self.dt, 1))
        self.bpd = round(random.gauss(self.bpd + self.bpd_drift * self.dt, 1))
        self.rsr = round(random.gauss(self.rsr + self.rsr_drift * self.dt, 0.5))

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
        if condition in self.conditions:
            conData = self.conditions[condition]
            print(condition)
            print(conData)

    def reset_drifts(self):
        self.bpm_drift = random.uniform(-0.02, 0.02)
        self.bo_drift  = random.uniform(-0.001, 0.001)
        self.tmp_drift = random.uniform(-0.0005, 0.0005)
        self.bps_drift = random.uniform(-0.01, 0.01)
        self.bpd_drift = random.uniform(-0.01, 0.01)
        self.rsr_drift = random.uniform(-0.005, 0.005)

astronaut = Astronaut(
    "Alex Morgan",
    34,
    65,
    98,
    36.7,
    (115, 75),
    14
)

tracking = True

astronaut._reset_drifts()
astronaut._inflict_condition("hypoxia_normal")

#while tracking:
#    astronaut.update_health()
#    print(astronaut.generate_reading())
#    sleep(5)
