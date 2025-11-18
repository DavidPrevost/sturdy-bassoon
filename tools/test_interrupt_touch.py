#!/usr/bin/env python3
"""Test GT1151 interrupt-based touch detection.

This script uses the exact same method as Waveshare's demo:
1. Monitor INT pin (GPIO17)
2. When INT goes LOW, read touch data from GT1151 registers
3. Display touch coordinates

This should finally work since we're using the correct approach!
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.touch.gpio_touch import TouchGPIO
    import smbus2
except ImportError as e:
    print(f"Error: Missing required library: {e}")
    sys.exit(1)


def monitor_gt1151_interrupt(gpio_touch, bus, addr):
    """Monitor GT1151 using interrupt pin."""
    print("\n" + "=" * 60)
    print("GT1151 Interrupt-Based Touch Monitor")
    print("=" * 60)
    print("Touch the screen to test. Press Ctrl+C to exit\n")

    touch_count = 0
    last_int_state = 1

    try:
        while True:
            # Read interrupt pin state
            int_state = gpio_touch.read_int_pin()

            # Detect falling edge (HIGH -> LOW transition)
            if last_int_state == 1 and int_state == 0:
                try:
                    # INT pin went LOW - touch detected!
                    # Read status register (0x814E)
                    status = bus.read_byte_data(addr, 0x4E)

                    # Check bit 0x80 for valid touch data
                    if status & 0x80:
                        num_touches = status & 0x0F  # Lower 4 bits

                        if 1 <= num_touches <= 5:
                            # Read touch data (8 bytes per touch point)
                            touch_data = bus.read_i2c_block_data(addr, 0x4F, num_touches * 8)

                            # Parse first touch point
                            track_id = touch_data[0]
                            x = (touch_data[2] << 8) | touch_data[1]
                            y = (touch_data[4] << 8) | touch_data[3]
                            size = (touch_data[6] << 8) | touch_data[5]

                            touch_count += 1
                            print(f"[{touch_count}] Touch detected!")
                            print(f"    X: {x:3d}, Y: {y:3d}, Size: {size:3d}")
                            print(f"    Status: 0x{status:02X}, Touches: {num_touches}")

                        else:
                            print(f"Invalid touch count: {num_touches}")

                    else:
                        print(f"Status register has no valid data: 0x{status:02X}")

                    # Clear status register to acknowledge touch
                    bus.write_byte_data(addr, 0x4E, 0x00)

                except Exception as e:
                    print(f"Error reading touch data: {e}")

            last_int_state = int_state
            time.sleep(0.01)  # Poll at 100Hz

    except KeyboardInterrupt:
        print(f"\n\nTotal touches detected: {touch_count}")
        print("Monitoring stopped")


def main():
    """Main entry point."""
    print("=" * 60)
    print("GT1151 Interrupt-Based Touch Test")
    print("=" * 60)

    # Step 1: Initialize GPIO and reset touch controller
    print("\n[Step 1] Initializing GPIO and resetting GT1151...")
    try:
        gpio_touch = TouchGPIO()
        gpio_touch.init()
        print("✓ GPIO initialization complete")
    except Exception as e:
        print(f"✗ GPIO initialization failed: {e}")
        sys.exit(1)

    # Step 2: Connect to I2C bus
    print("\n[Step 2] Connecting to I2C bus...")
    bus_num = 1
    touch_addr = 0x14

    try:
        bus = smbus2.SMBus(bus_num)
        bus.read_byte(touch_addr)
        print(f"✓ GT1151 found at I2C address 0x{touch_addr:02X}")
    except Exception as e:
        print(f"✗ Error connecting to GT1151: {e}")
        gpio_touch.cleanup()
        sys.exit(1)

    # Step 3: Verify INT pin is readable
    print("\n[Step 3] Testing INT pin...")
    try:
        int_state = gpio_touch.read_int_pin()
        print(f"✓ INT pin state: {'HIGH (no touch)' if int_state else 'LOW (touch!)'}")
    except Exception as e:
        print(f"✗ Error reading INT pin: {e}")
        gpio_touch.cleanup()
        bus.close()
        sys.exit(1)

    # Step 4: Monitor for touches using interrupt
    try:
        monitor_gt1151_interrupt(gpio_touch, bus, touch_addr)
    finally:
        # Cleanup
        gpio_touch.cleanup()
        bus.close()
        print("\nGPIO resources cleaned up")


if __name__ == '__main__':
    main()
