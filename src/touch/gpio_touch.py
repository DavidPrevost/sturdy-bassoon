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
            time.sleep(0.02)  # 20ms low (increased for reliability)

            self.gpio.output(self.rst_pin, self.gpio.HIGH)
            time.sleep(0.1)  # 100ms to stabilize (increased for boot time)

        elif self.gpio_mode == 'gpiozero':
            # gpiozero: off -> wait -> on
            self.rst_gpio.off()  # Pull low
            time.sleep(0.02)

            self.rst_gpio.on()   # Pull high
            time.sleep(0.1)

        print("Touch controller reset complete")

        # Now perform I2C initialization sequence
        self._i2c_wake_sequence()

    def _i2c_wake_sequence(self):
        """Perform I2C wake/configuration sequence after GPIO reset."""
        try:
            import smbus2
            bus = smbus2.SMBus(1)
            addr = 0x14

            print("Performing I2C wake sequence...")

            # Method 1: Exit sleep mode via power register
            try:
                bus.write_byte_data(addr, 0xFE, 0x00)  # Exit sleep mode
                time.sleep(0.05)
                print("  ✓ Wrote to power management register (0xFE)")
            except Exception as e:
                print(f"  ✗ Power register write failed: {e}")

            # Method 2: Trigger calibration/reset via command register
            try:
                bus.write_byte_data(addr, 0xFA, 0x00)  # Normal mode (not factory reset)
                time.sleep(0.05)
                print("  ✓ Wrote to command register (0xFA)")
            except Exception as e:
                print(f"  ✗ Command register write failed: {e}")

            # Method 3: Read chip ID to confirm controller is responsive
            try:
                chip_id = bus.read_byte_data(addr, 0xA7)
                print(f"  ✓ Chip ID: 0x{chip_id:02X}")
            except Exception as e:
                print(f"  ✗ Chip ID read failed: {e}")

            # Method 4: Configure interrupt mode (if needed)
            try:
                # Some controllers need interrupt mode configured
                # 0xFA: Motion mask register (enable touch reporting)
                bus.write_byte_data(addr, 0xFA, 0x01)  # Enable touch events
                time.sleep(0.01)
                print("  ✓ Configured touch event reporting")
            except Exception as e:
                # Not critical if this fails
                pass

            print("I2C wake sequence complete")
            bus.close()

        except ImportError:
            print("Warning: smbus2 not available, skipping I2C wake sequence")
        except Exception as e:
            print(f"Warning: I2C wake sequence failed: {e}")

    def cleanup(self):
        """Cleanup GPIO resources."""
        if self.gpio_mode == 'RPi.GPIO' and self.gpio:
            self.gpio.cleanup()
        elif self.gpio_mode == 'gpiozero':
            if hasattr(self, 'rst_gpio'):
                self.rst_gpio.close()
            if hasattr(self, 'int_gpio'):
                self.int_gpio.close()
