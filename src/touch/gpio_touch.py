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
        """Reset the touch controller using GPIO.

        GT1151 reset sequence: HIGH -> LOW -> HIGH
        (Note: This is opposite of most touch controllers!)
        """
        print("Resetting touch controller (GT1151 sequence)...")

        if self.gpio_mode == 'RPi.GPIO':
            # GT1151 specific reset sequence: HIGH -> LOW -> HIGH
            self.gpio.output(self.rst_pin, self.gpio.HIGH)
            time.sleep(0.1)  # 100ms high

            self.gpio.output(self.rst_pin, self.gpio.LOW)
            time.sleep(0.1)  # 100ms low

            self.gpio.output(self.rst_pin, self.gpio.HIGH)
            time.sleep(0.1)  # 100ms to stabilize

        elif self.gpio_mode == 'gpiozero':
            # gpiozero: on -> off -> on
            self.rst_gpio.on()   # Pull high
            time.sleep(0.1)

            self.rst_gpio.off()  # Pull low
            time.sleep(0.1)

            self.rst_gpio.on()   # Pull high
            time.sleep(0.1)

        print("Touch controller reset complete")

        # Read version to verify controller is alive
        self._read_version()

    def _read_version(self):
        """Read GT1151 version register to verify controller is responsive."""
        try:
            import smbus2
            bus = smbus2.SMBus(1)
            addr = 0x14

            print("Reading GT1151 version...")

            # GT1151 version is at register 0x8140 (4 bytes)
            # Need to write the register address as 16-bit
            version_data = bus.read_i2c_block_data(addr, 0x40, 4)  # Read from 0x8140

            print(f"  ✓ Version data: {[hex(b) for b in version_data]}")
            bus.close()

        except ImportError:
            print("Warning: smbus2 not available, skipping version read")
        except Exception as e:
            print(f"Warning: Version read failed: {e}")
            print("  (This may be normal - continuing anyway)")

    def read_int_pin(self):
        """Read the interrupt pin state.

        Returns:
            int: 0 if touch detected (INT pulled low), 1 if no touch
        """
        if self.gpio_mode == 'RPi.GPIO':
            return self.gpio.input(self.int_pin)
        elif self.gpio_mode == 'gpiozero':
            # Button.is_pressed is True when pin is LOW (pulled down)
            # We want: 0 = touch (LOW), 1 = no touch (HIGH)
            return 0 if self.int_gpio.is_pressed else 1
        return 1  # Default to no touch

    def cleanup(self):
        """Cleanup GPIO resources."""
        if self.gpio_mode == 'RPi.GPIO' and self.gpio:
            self.gpio.cleanup()
        elif self.gpio_mode == 'gpiozero':
            if hasattr(self, 'rst_gpio'):
                self.rst_gpio.close()
            if hasattr(self, 'int_gpio'):
                self.int_gpio.close()
