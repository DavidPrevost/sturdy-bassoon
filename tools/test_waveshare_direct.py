#!/usr/bin/env python3
"""Test touch using Waveshare's GT1151 library directly.

This uses their actual working code instead of our reimplementation.
"""

import sys
import os
from pathlib import Path

# Add Waveshare's library to path
waveshare_lib = Path(__file__).parent.parent / "python" / "lib"
sys.path.insert(0, str(waveshare_lib))

try:
    from TP_lib import gt1151
    from TP_lib import epdconfig
except ImportError as e:
    print(f"Error: Could not import Waveshare library: {e}")
    print(f"Make sure python/lib/TP_lib exists")
    sys.exit(1)


def main():
    """Test touch using Waveshare's library."""
    print("=" * 60)
    print("Waveshare GT1151 Library Direct Test")
    print("=" * 60)

    # Initialize the GT1151 touch controller
    print("\n[Step 1] Initializing GT1151 using Waveshare's library...")
    try:
        epdconfig.module_init()
        gt = gt1151.GT1151()
        GT_Dev = gt1151.GT_Development()
        GT_Old = gt1151.GT_Development()

        gt.GT_Init()
        print("✓ GT1151 initialized successfully")
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Monitor for touch events
    print("\n[Step 2] Monitoring for touch events...")
    print("Touch the screen. Press Ctrl+C to exit\n")

    touch_count = 0
    try:
        while True:
            # Check INT pin
            int_state = epdconfig.digital_read(gt.INT)

            if int_state == 0:  # INT pin LOW = touch detected
                GT_Dev.Touch = 1
            else:
                GT_Dev.Touch = 0

            # Scan for touch
            gt.GT_Scan(GT_Dev, GT_Old)

            # Check if position changed (indicates new touch data)
            if GT_Dev.X[0] != GT_Old.X[0] or GT_Dev.Y[0] != GT_Old.Y[0]:
                if GT_Dev.TouchpointFlag:
                    touch_count += 1
                    print(f"[{touch_count}] Touch detected!")
                    print(f"    X: {GT_Dev.X[0]:3d}, Y: {GT_Dev.Y[0]:3d}, Size: {GT_Dev.S[0]:3d}")
                    print(f"    Touch count: {GT_Dev.TouchCount}")

    except KeyboardInterrupt:
        print(f"\n\nTotal touches detected: {touch_count}")
        print("Exiting...")
    finally:
        epdconfig.module_exit()
        print("Cleanup complete")


if __name__ == '__main__':
    main()
