class DummyGPIO:
    BCM = "BCM"
    IN = "IN"
    OUT = "OUT"
    HIGH = 1
    LOW = 0
    PUD_DOWN = "PUD_DOWN"

    def __init__(self):
        self._pins = {}

    def setmode(self, mode):
        print(f"[SIM GPIO] setmode({mode})")

    def setup(self, pin, direction, pull_up_down=None):
        self._pins[pin] = 0
        print(f"[SIM GPIO] setup(pin={pin}, dir={direction}, pud={pull_up_down})")

    def input(self, pin):
        return self._pins.get(pin, 0)

    def output(self, pin, value):
        self._pins[pin] = value
        print(f"[SIM GPIO] output(pin={pin}) = {value}")

    def cleanup(self):
        print("[SIM GPIO] cleanup()")
        self._pins.clear()
        
GPIO = DummyGPIO()