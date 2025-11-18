#!/usr/bin/env python3
"""Detect correct GPIO pins for touch controller reset.

This script tries different common GPIO pin combinations used by
Waveshare e-ink displays to find which pins successfully wake the
touch controller.

Common pin configurations for Waveshare displays:
- 2.13" V4: GPIO13 (RST), GPIO17 (INT)
- Some variants: GPIO22 (RST), GPIO17 (INT)
- Some variants: GPIO17 (RST), GPIO4 (INT)
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import RPi.GPIO as GPIO
    import smbus2
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    print("Install with: sudo apt-get install python3-rpi.gpio python3-smbus")
    sys.exit(1)


# Common pin combinations for Waveshare displays
PIN_COMBINATIONS = [
    {"name": "2.13\" V4 (default)", "rst": 13, "int": 17},
    {"name": "Alternative 1", "rst": 22, "int": 17},
    {"name": "Alternative 2", "rst": 17, "int": 4},
    {"name": "Alternative 3", "rst": 25, "int": 24},
]

TOUCH_ADDR = 0x14
I2C_BUS = 1


def test_pin_combination(rst_pin, int_pin):
    """Test a specific GPIO pin combination."""
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Setup pins
        GPIO.setup(rst_pin, GPIO.OUT)
        GPIO.setup(int_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Perform reset sequence
        GPIO.output(rst_pin, GPIO.LOW)
        time.sleep(0.02)
        GPIO.output(rst_pin, GPIO.HIGH)
        time.sleep(0.1)

        # Try I2C wake sequence
        bus = smbus2.SMBus(I2C_BUS)

        # Write to power management register
        try:
            bus.write_byte_data(TOUCH_ADDR, 0xFE, 0x00)
            time.sleep(0.05)
        except:
            pass

        # Read chip ID
        try:
            chip_id = bus.read_byte_data(TOUCH_ADDR, 0xA7)
        except:
            chip_id = None

        # Check if touch data registers respond
        time.sleep(0.1)
        touch_points = None
        try:
            touch_points = bus.read_byte_data(TOUCH_ADDR, 0x02)
        except:
            pass

        bus.close()
        GPIO.cleanup()

        return {
            "chip_id": chip_id,
            "touch_reg_accessible": touch_points is not None,
        }

    except Exception as e:
        GPIO.cleanup()
        return {"error": str(e)}


def main():
    """Main entry point."""
    print("=" * 60)
    print("Waveshare Touch Controller GPIO Pin Detection")
    print("=" * 60)
    print("\nThis tool will test common GPIO pin combinations to find")
    print("which pins are connected to your touch controller.\n")

    # Test I2C connectivity first
    print("Testing I2C connectivity...")
    try:
        bus = smbus2.SMBus(I2C_BUS)
        bus.read_byte(TOUCH_ADDR)
        print(f"✓ Touch controller found at I2C address 0x{TOUCH_ADDR:02X}\n")
        bus.close()
    except Exception as e:
        print(f"✗ Cannot connect to touch controller: {e}")
        print("Make sure I2C is enabled (sudo raspi-config)")
        sys.exit(1)

    print("Testing GPIO pin combinations...")
    print("=" * 60)

    results = []
    for combo in PIN_COMBINATIONS:
        print(f"\nTesting: {combo['name']}")
        print(f"  RST: GPIO{combo['rst']}, INT: GPIO{combo['int']}")

        result = test_pin_combination(combo['rst'], combo['int'])

        if "error" in result:
            print(f"  ✗ Error: {result['error']}")
            results.append((combo, False, result))
        else:
            chip_id = result.get('chip_id')
            touch_ok = result.get('touch_reg_accessible', False)

            if chip_id and chip_id != 0x00:
                print(f"  ✓ Chip ID: 0x{chip_id:02X}")
                print(f"  {'✓' if touch_ok else '?'} Touch registers: {'Accessible' if touch_ok else 'Not responding'}")
                results.append((combo, True, result))
            else:
                print(f"  ✗ No response from touch controller")
                results.append((combo, False, result))

        time.sleep(0.5)  # Brief delay between tests

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    working_combos = [r for r in results if r[1]]

    if working_combos:
        print("\n✓ Working pin combinations found:\n")
        for combo, success, result in working_combos:
            chip_id = result.get('chip_id', 0)
            print(f"  {combo['name']}")
            print(f"    RST: GPIO{combo['rst']}, INT: GPIO{combo['int']}")
            print(f"    Chip ID: 0x{chip_id:02X}")
            print()

        print("To use these pins, update src/touch/gpio_touch.py:")
        best = working_combos[0][0]
        print(f"  TP_RST_PIN = {best['rst']}")
        print(f"  TP_INT_PIN = {best['int']}")

    else:
        print("\n✗ No working pin combinations found.")
        print("\nPossible issues:")
        print("  1. Touch controller may use different pins than tested")
        print("  2. Touch hardware may not be properly connected")
        print("  3. Display may not have touch capability")
        print("\nTo find the correct pins:")
        print("  1. Check your display's documentation")
        print("  2. Look at Waveshare demo code for your specific model")
        print("  3. Use a multimeter to trace the touch controller connections")


if __name__ == '__main__':
    main()
