#!/usr/bin/env python3
"""Touch controller diagnostic tool.

This script reads I2C registers from the touch controller to help
debug and understand the register map.
"""

import sys
import time

try:
    import smbus2
except ImportError:
    print("Error: smbus2 not installed")
    print("Install with: sudo apt-get install python3-smbus")
    sys.exit(1)


def read_register_range(bus, addr, start_reg, num_regs):
    """Read a range of registers and return their values."""
    values = []
    for reg in range(start_reg, start_reg + num_regs):
        try:
            value = bus.read_byte_data(addr, reg)
            values.append((reg, value))
        except:
            values.append((reg, None))
    return values


def print_registers(registers):
    """Print registers in a nice format."""
    print("\n  Reg | Hex  | Dec | Binary")
    print("  ----|------|-----|----------")
    for reg, value in registers:
        if value is not None:
            print(f"  0x{reg:02X} | 0x{value:02X} | {value:3d} | {value:08b}")
        else:
            print(f"  0x{reg:02X} |  N/A |  N/A |    N/A")


def monitor_touch(bus, addr):
    """Monitor touch controller registers in real-time."""
    print("\nTouch Controller Monitor")
    print("Touch the screen to see register changes")
    print("Press Ctrl+C to exit\n")

    # Track previous values to detect changes
    prev_values = {}

    try:
        while True:
            # Read common touch controller registers
            # Most capacitive controllers use 0x00-0x0F
            registers = read_register_range(bus, addr, 0x00, 16)

            # Check for changes
            changes = []
            for reg, value in registers:
                if value is not None and prev_values.get(reg) != value:
                    changes.append((reg, prev_values.get(reg), value))
                    prev_values[reg] = value

            # Print changes
            if changes:
                print(f"\n[{time.strftime('%H:%M:%S')}] Register changes detected:")
                for reg, old, new in changes:
                    old_str = f"0x{old:02X}" if old is not None else "None"
                    print(f"  Reg 0x{reg:02X}: {old_str} -> 0x{new:02X} (dec {new})")

            time.sleep(0.1)  # Poll 10 times per second

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")


def try_wake_controller(bus, addr):
    """Try various methods to wake up the touch controller."""
    print("\nAttempting to wake up touch controller...")

    # Method 1: Write to power management register
    print("  [1] Trying power management register...")
    try:
        # Many controllers use register 0xA5 or 0xFE for power
        bus.write_byte_data(addr, 0xFE, 0x00)  # Exit sleep mode
        time.sleep(0.1)
        print("      Wrote 0x00 to register 0xFE")
    except Exception as e:
        print(f"      Failed: {e}")

    # Method 2: Try chip ID register read (often wakes chip)
    print("  [2] Reading chip ID registers...")
    try:
        chip_id_regs = [0xA3, 0xA7, 0xA8, 0xA9]
        for reg in chip_id_regs:
            val = bus.read_byte_data(addr, reg)
            if val != 0x00:
                print(f"      Reg 0x{reg:02X} = 0x{val:02X} (possible chip ID!)")
    except Exception as e:
        print(f"      Failed: {e}")

    # Method 3: Soft reset
    print("  [3] Trying soft reset...")
    try:
        bus.write_byte_data(addr, 0xFA, 0x01)  # Reset command
        time.sleep(0.1)
        print("      Reset command sent")
    except Exception as e:
        print(f"      Failed: {e}")

    # Method 4: Read version info (CST816S specific)
    print("  [4] Reading version registers...")
    try:
        version_regs = [0x15, 0xA7, 0xA8, 0xA9]
        for reg in version_regs:
            val = bus.read_byte_data(addr, reg)
            if val != 0x00:
                print(f"      Reg 0x{reg:02X} = 0x{val:02X}")
    except Exception as e:
        print(f"      Failed: {e}")

    print("\n  Checking if controller is now responsive...")
    time.sleep(0.2)


def main():
    """Main entry point."""
    print("="*60)
    print("Touch Controller I2C Diagnostic Tool")
    print("="*60)

    # I2C setup
    bus_num = 1
    touch_addr = 0x14

    print(f"\nConnecting to I2C bus {bus_num}, address 0x{touch_addr:02X}...")

    try:
        bus = smbus2.SMBus(bus_num)
        # Test connection
        bus.read_byte(touch_addr)
        print("✓ Touch controller found!")
    except Exception as e:
        print(f"✗ Error connecting to touch controller: {e}")
        sys.exit(1)

    # Try to wake up the controller
    try_wake_controller(bus, touch_addr)

    # Read initial state
    print("\n" + "="*60)
    print("Register State After Wake Attempt (0x00-0x0F)")
    print("="*60)
    registers = read_register_range(bus, touch_addr, 0x00, 16)
    print_registers(registers)

    # Also check extended registers
    print("\n" + "="*60)
    print("Extended Registers (0xA0-0xAF)")
    print("="*60)
    registers_ext = read_register_range(bus, touch_addr, 0xA0, 16)
    print_registers(registers_ext)

    # Start monitoring
    print("\n" + "="*60)
    monitor_touch(bus, touch_addr)


if __name__ == '__main__':
    main()
