#!/usr/bin/env python3
"""Test GPIO touch initialization and verify touch data after reset.

This script:
1. Initializes GPIO and resets the touch controller
2. Reads touch data registers to verify they populate
3. Monitors for touch events in real-time
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
    print("Install with: sudo apt-get install python3-smbus")
    sys.exit(1)


def read_touch_registers(bus, addr, start_reg, num_regs):
    """Read a range of registers and return their values."""
    values = []
    for reg in range(start_reg, start_reg + num_regs):
        try:
            value = bus.read_byte_data(addr, reg)
            values.append((reg, value))
        except:
            values.append((reg, None))
    return values


def print_registers(registers, title):
    """Print registers in a nice format."""
    print(f"\n{title}")
    print("=" * 50)
    print("  Reg | Hex  | Dec | Binary")
    print("  ----|------|-----|----------")
    for reg, value in registers:
        if value is not None:
            print(f"  0x{reg:02X} | 0x{value:02X} | {value:3d} | {value:08b}")
        else:
            print(f"  0x{reg:02X} |  N/A |  N/A |    N/A")


def monitor_touch(bus, addr):
    """Monitor touch controller registers in real-time."""
    print("\n" + "=" * 50)
    print("Touch Monitor - Touch the screen to test")
    print("=" * 50)
    print("Press Ctrl+C to exit\n")

    prev_values = {}

    try:
        while True:
            # Read touch data registers
            registers = read_touch_registers(bus, addr, 0x00, 16)

            # Check for changes
            changes = []
            for reg, value in registers:
                if value is not None and prev_values.get(reg) != value:
                    changes.append((reg, prev_values.get(reg), value))
                    prev_values[reg] = value

            # Print changes
            if changes:
                print(f"\n[{time.strftime('%H:%M:%S')}] Touch detected! Register changes:")
                for reg, old, new in changes:
                    old_str = f"0x{old:02X}" if old is not None else "None"
                    print(f"  Reg 0x{reg:02X}: {old_str} -> 0x{new:02X} (dec {new})")

                    # Decode important registers
                    if reg == 0x02:
                        print(f"    └─ Touch points: {new}")
                    elif reg == 0x03:
                        print(f"    └─ X coordinate (high byte)")
                    elif reg == 0x04:
                        print(f"    └─ X coordinate (low byte)")
                    elif reg == 0x05:
                        print(f"    └─ Y coordinate (high byte)")
                    elif reg == 0x06:
                        print(f"    └─ Y coordinate (low byte)")

            time.sleep(0.1)  # Poll 10 times per second

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")


def main():
    """Main entry point."""
    print("=" * 50)
    print("GPIO Touch Initialization Test")
    print("=" * 50)

    # Step 1: Initialize GPIO and reset touch controller
    print("\n[Step 1] Initializing GPIO and resetting touch controller...")
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
        print(f"✓ Touch controller found at I2C address 0x{touch_addr:02X}")
    except Exception as e:
        print(f"✗ Error connecting to touch controller: {e}")
        gpio_touch.cleanup()
        sys.exit(1)

    # Step 3: Read initial register state
    print("\n[Step 3] Reading touch data registers (0x00-0x0F)...")
    time.sleep(0.1)  # Brief delay for controller to stabilize
    registers = read_touch_registers(bus, touch_addr, 0x00, 16)
    print_registers(registers, "Touch Data Registers After GPIO Reset")

    # Check if registers are non-zero (good sign)
    non_zero_count = sum(1 for _, val in registers if val is not None and val != 0)
    print(f"\nNon-zero registers: {non_zero_count}/16")

    if non_zero_count == 0:
        print("\n⚠ WARNING: All touch data registers are 0x00")
        print("  This may be normal if screen is not being touched.")
        print("  Touch the screen during monitoring to verify functionality.")
    else:
        print("\n✓ Touch controller appears to be responding!")

    # Step 4: Monitor for touch events
    try:
        monitor_touch(bus, touch_addr)
    finally:
        # Cleanup
        gpio_touch.cleanup()
        print("\nGPIO resources cleaned up")


if __name__ == '__main__':
    main()
