#!/usr/bin/env python3
"""GPIO-based touch controller initialization for Waveshare 2.13" V4."""

import time


class TouchGPIO:
    """Handles GPIO initialization for capacitive touch controller."""

    # Default GPIO pins for Waveshare 2.13" V4 touch
    # These may vary - check your specific model
    TP_RST_PIN = 13  # Touch panel reset pin
    TP_INT_PIN = 17  # Touch panel interrupt pin

    def __init__(self, rst_pin=None, int_pin=None):
        """
        Initialize touch GPIO handler.

        Args:
            rst_pin: GPIO pin for touch reset (default: 13)
            int_pin: GPIO pin for touch interrupt (default: 17)
        """
        self.rst_pin = rst_pin or self.TP_RST_PIN
        self.int_pin = int_pin or self.TP_INT_PIN
        self.gpio = None
        self.gpio_mode = None

    def init(self):
        """Initialize GPIO and reset touch controller."""
        # Try RPi.GPIO first (most common)
        try:
            import RPi.GPIO as GPIO
            self.gpio = GPIO
            self.gpio_mode = 'RPi.GPIO'

            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Setup reset pin as output
            GPIO.setup(self.rst_pin, GPIO.OUT)

            # Setup interrupt pin as input (optional, for future interrupt handling)
            GPIO.setup(self.int_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            print(f"✓ GPIO initialized (RPi.GPIO) - RST:GPIO{self.rst_pin}, INT:GPIO{self.int_pin}")

        except ImportError:
            # Try gpiozero as fallback
            try:
                from gpiozero import LED, Button
                self.gpio_mode = 'gpiozero'

                # Use LED class for output (reset pin)
                self.rst_gpio = LED(self.rst_pin)

                # Use Button class for input (interrupt pin)
                self.int_gpio = Button(self.int_pin, pull_up=True)

                print(f"✓ GPIO initialized (gpiozero) - RST:GPIO{self.rst_pin}, INT:GPIO{self.int_pin}")

            except ImportError:
                raise RuntimeError("No GPIO library available (need RPi.GPIO or gpiozero)")

        # Perform touch controller reset sequence
        self.reset_touch_controller()

        return True

    def reset_touch_controller(self):
        """Reset the touch controller using GPIO."""
        print("Resetting touch controller...")

        if self.gpio_mode == 'RPi.GPIO':
            # Standard reset sequence: LOW -> wait -> HIGH
            self.gpio.output(self.rst_pin, self.gpio.LOW)
            time.sleep(0.01)  # 10ms low

            self.gpio.output(self.rst_pin, self.gpio.HIGH)
            time.sleep(0.05)  # 50ms to stabilize

        elif self.gpio_mode == 'gpiozero':
            # gpiozero: off -> wait -> on
            self.rst_gpio.off()  # Pull low
            time.sleep(0.01)

            self.rst_gpio.on()   # Pull high
            time.sleep(0.05)

        print("Touch controller reset complete")

    def cleanup(self):
        """Cleanup GPIO resources."""
        if self.gpio_mode == 'RPi.GPIO' and self.gpio:
            self.gpio.cleanup()
        elif self.gpio_mode == 'gpiozero':
            if hasattr(self, 'rst_gpio'):
                self.rst_gpio.close()
            if hasattr(self, 'int_gpio'):
                self.int_gpio.close()
