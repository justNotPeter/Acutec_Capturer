import os
from app.config.digital_io import (
    DIGITAL_OUTPUTS_FROM_FANUC_TO_PI,
    DIGITAL_OUTPUTS_FROM_PI_TO_FANUC,
)

SIMULATION_MODE = os.getenv("PI_SIM", "1") == "1"

if not SIMULATION_MODE:
    import RPi.GPIO as _GPIO
    print("Using Raspberry Pi GPIO")
else:
    from app.external.dummy_gpio import GPIO as _GPIO
    print("Using DummyGPIO (Simulation Mode)")

GPIO = _GPIO

_initialized = False


def init_gpio_pins() -> None:
    global _initialized
    if _initialized:
        return

    try:
        GPIO.setmode(GPIO.BCM)

        # Fanuc to Pi 
        GPIO.setup(
            DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["HEARTBEAT"],
            GPIO.IN,
            pull_up_down=GPIO.PUD_DOWN,
        )
        GPIO.setup(
            DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["ROBOT_IN_POSITION_FOR_CAPTURE"],
            GPIO.IN,
            pull_up_down=GPIO.PUD_DOWN,
        )
        GPIO.setup(
            DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["ACKNOWLEDGEMENT"],
            GPIO.IN,
            pull_up_down=GPIO.PUD_DOWN,
        )
        GPIO.setup(
            DIGITAL_OUTPUTS_FROM_FANUC_TO_PI["PART_SEQUENCE_DONE"],
            GPIO.IN,
            pull_up_down=GPIO.PUD_DOWN,
        )

        # Pi to Fanuc 
        GPIO.setup(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RESET_SIGNAL"], GPIO.OUT)
        GPIO.setup(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["CAPTURE_DONE"], GPIO.OUT)
        GPIO.setup(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["ERROR_SIGNAL"], GPIO.OUT)
        GPIO.setup(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RECIPE_BIT_2"], GPIO.OUT)
        GPIO.setup(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RECIPE_BIT_1"], GPIO.OUT)
        GPIO.setup(DIGITAL_OUTPUTS_FROM_PI_TO_FANUC["RECIPE_BIT_0"], GPIO.OUT)

        _initialized = True
        print("GPIO initialized successfully (gpio_setup.init_gpio_pins).")

    except Exception as e:
        print(f"Failed to initialize GPIO: {e}")
        _initialized = False


def cleanup_gpio() -> None:
    try:
        GPIO.cleanup()
        print("GPIO cleanup complete!")
    except Exception as e:
        print(f"GPIO cleanup failed: {e}")