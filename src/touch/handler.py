"""Touch input handler for the e-ink display."""
import time
import sys
from pathlib import Path
from typing import Optional, Callable, Tuple
from enum import Enum


class Gesture(Enum):
    """Touch gesture types."""
    TAP = "tap"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    LONG_PRESS = "long_press"


class TouchEvent:
    """Represents a touch event."""

    def __init__(self, gesture: Gesture, position: Tuple[int, int] = None):
        self.gesture = gesture
        self.position = position  # (x, y) coordinates
        self.timestamp = time.time()

    def __repr__(self):
        return f"TouchEvent({self.gesture.value}, pos={self.position})"


class TouchHandler:
    """
    Handles touch input from the e-ink display.

    Note: This is a basic implementation. The actual touch interface
    will depend on the specific Waveshare display model and its driver.
    """

    def __init__(self, width=250, height=122, epdconfig=None):
        self.width = width
        self.height = height
        self.simulation_mode = True  # Will be set based on hardware availability
        self.epdconfig = epdconfig  # Pre-initialized epdconfig module (optional)

        # Touch detection parameters
        self.swipe_threshold = 30  # Minimum pixels for swipe
        self.long_press_duration = 1.0  # Seconds for long press
        self.tap_timeout = 0.3  # Maximum duration for tap

        # Touch state
        self.touch_start = None
        self.touch_start_time = None
        self.touch_current = None
        self._long_press_fired = False

        # Callbacks
        self.on_gesture: Optional[Callable[[TouchEvent], None]] = None

        try:
            # Try to initialize touch hardware
            self._init_touch_hardware()
            self.simulation_mode = False
        except Exception as e:
            print(f"Touch hardware not available: {e}")
            print("Touch handler running in simulation mode")

    def _init_touch_hardware(self):
        """
        Initialize touch hardware using Waveshare's GT1151 library.

        This uses the working library from python/lib/TP_lib instead of
        reimplementing the touch detection.
        """
        # Add Waveshare's library to Python path
        repo_root = Path(__file__).parent.parent.parent
        waveshare_lib = repo_root / "python" / "lib"

        if not waveshare_lib.exists():
            raise RuntimeError(f"Waveshare library not found at {waveshare_lib}")

        sys.path.insert(0, str(waveshare_lib))

        try:
            from TP_lib import gt1151, epdconfig

            # Only initialize module if not already done
            if self.epdconfig is None:
                # Initialize the module (sets up SPI, I2C, GPIO)
                epdconfig.module_init()
                self.epdconfig = epdconfig
                print("✓ Waveshare module initialized by touch handler")
            else:
                # Use pre-initialized epdconfig
                epdconfig = self.epdconfig
                print("✓ Using pre-initialized Waveshare module")

            # Create GT1151 touch controller instance
            self.gt = gt1151.GT1151()
            self.GT_Dev = gt1151.GT_Development()
            self.GT_Old = gt1151.GT_Development()

            # Initialize the touch controller (reset + version read)
            self.gt.GT_Init()

            print("✓ Touch hardware initialized (Waveshare GT1151)")

        except Exception as e:
            raise RuntimeError(f"Failed to initialize Waveshare GT1151: {e}")

    def set_gesture_callback(self, callback: Callable[[TouchEvent], None]):
        """Set callback function for gesture events."""
        self.on_gesture = callback

    def poll(self) -> Optional[TouchEvent]:
        """
        Poll for touch events from hardware using Waveshare's GT1151 library.

        Returns:
            TouchEvent if a gesture was detected, None otherwise
        """
        if self.simulation_mode:
            return None

        try:
            # Use Waveshare's GT1151 library
            if hasattr(self, 'gt'):
                # Check INT pin state
                int_state = self.epdconfig.digital_read(self.gt.INT)

                if int_state == 0:  # INT LOW = touch detected
                    self.GT_Dev.Touch = 1
                else:
                    self.GT_Dev.Touch = 0

                # Scan for touch data
                self.gt.GT_Scan(self.GT_Dev, self.GT_Old)

                # Check if we have new touch data (position changed)
                if (self.GT_Dev.X[0] != self.GT_Old.X[0] or
                    self.GT_Dev.Y[0] != self.GT_Old.Y[0]):

                    if self.GT_Dev.TouchpointFlag:
                        # New touch data available
                        x, y = self.GT_Dev.X[0], self.GT_Dev.Y[0]

                        if self.touch_start is None:
                            # New touch started
                            self.touch_start = (x, y)
                            self.touch_start_time = time.time()
                            self.touch_current = (x, y)
                        else:
                            # Touch continuing - update current position
                            self.touch_current = (x, y)

                            # Check for long press
                            duration = time.time() - self.touch_start_time
                            if duration > self.long_press_duration and not self._long_press_fired:
                                self._long_press_fired = True
                                return TouchEvent(Gesture.LONG_PRESS, self.touch_start)
                    else:
                        # Touch released
                        if self.touch_start is not None:
                            # Touch was released, detect gesture
                            end_pos = self.touch_current or self.touch_start
                            duration = time.time() - self.touch_start_time

                            # Only detect gesture if long press wasn't already fired
                            if not self._long_press_fired:
                                gesture = self._detect_gesture(self.touch_start, end_pos, duration)
                                event = TouchEvent(gesture, end_pos)
                            else:
                                event = None  # Long press already handled

                            # Reset state
                            self.touch_start = None
                            self.touch_start_time = None
                            self.touch_current = None
                            self._long_press_fired = False

                            return event

        except Exception as e:
            # Don't spam errors, just return None
            pass

        return None

    def simulate_gesture(self, gesture: Gesture, position: Tuple[int, int] = None):
        """
        Simulate a gesture (for testing without hardware).

        Args:
            gesture: The gesture to simulate
            position: Optional touch position
        """
        event = TouchEvent(gesture, position)
        print(f"[SIMULATION] Touch gesture: {event}")

        if self.on_gesture:
            self.on_gesture(event)

        return event

    def _detect_gesture(self, start_pos: Tuple[int, int], end_pos: Tuple[int, int], duration: float) -> Gesture:
        """
        Detect gesture type based on start/end positions and duration.

        Args:
            start_pos: (x, y) starting position
            end_pos: (x, y) ending position
            duration: Time in seconds

        Returns:
            Detected gesture type
        """
        x1, y1 = start_pos
        x2, y2 = end_pos

        dx = x2 - x1
        dy = y2 - y1

        # Long press detection
        if duration > self.long_press_duration:
            return Gesture.LONG_PRESS

        # Swipe detection
        if abs(dx) > self.swipe_threshold or abs(dy) > self.swipe_threshold:
            # Horizontal swipe
            if abs(dx) > abs(dy):
                return Gesture.SWIPE_LEFT if dx < 0 else Gesture.SWIPE_RIGHT
            # Vertical swipe
            else:
                return Gesture.SWIPE_UP if dy < 0 else Gesture.SWIPE_DOWN

        # Tap (short touch with minimal movement)
        if duration < self.tap_timeout:
            return Gesture.TAP

        # Default to tap
        return Gesture.TAP

    def get_touch_zones(self, num_zones: int = 3) -> list:
        """
        Divide screen into touch zones for simple navigation.

        Args:
            num_zones: Number of horizontal zones (default 3: left, center, right)

        Returns:
            List of (x_start, x_end) tuples defining zones
        """
        zone_width = self.width // num_zones
        zones = []

        for i in range(num_zones):
            x_start = i * zone_width
            x_end = (i + 1) * zone_width if i < num_zones - 1 else self.width
            zones.append((x_start, x_end))

        return zones

    def get_zone_from_position(self, x: int, num_zones: int = 3) -> int:
        """
        Get zone index from x position.

        Args:
            x: X coordinate
            num_zones: Number of zones

        Returns:
            Zone index (0-based)
        """
        zones = self.get_touch_zones(num_zones)
        for i, (x_start, x_end) in enumerate(zones):
            if x_start <= x < x_end:
                return i
        return num_zones - 1  # Default to last zone

    def cleanup(self):
        """Clean up GPIO and touch hardware resources."""
        if hasattr(self, 'epdconfig'):
            try:
                self.epdconfig.module_exit()
                print("Touch hardware resources cleaned up")
            except Exception as e:
                print(f"Error cleaning up touch hardware: {e}")


class KeyboardTouchEmulator:
    """
    Keyboard-based touch emulator for testing without hardware.

    Use arrow keys to simulate swipes, space for tap, etc.
    """

    def __init__(self, touch_handler: TouchHandler):
        self.touch_handler = touch_handler
        self.enabled = False

    def enable(self):
        """Enable keyboard emulation (requires keyboard library)."""
        try:
            import keyboard
            self.enabled = True

            # Bind keys
            keyboard.on_press_key("left", lambda _: self.touch_handler.simulate_gesture(Gesture.SWIPE_LEFT))
            keyboard.on_press_key("right", lambda _: self.touch_handler.simulate_gesture(Gesture.SWIPE_RIGHT))
            keyboard.on_press_key("up", lambda _: self.touch_handler.simulate_gesture(Gesture.SWIPE_UP))
            keyboard.on_press_key("down", lambda _: self.touch_handler.simulate_gesture(Gesture.SWIPE_DOWN))
            keyboard.on_press_key("space", lambda _: self.touch_handler.simulate_gesture(Gesture.TAP, (125, 61)))

            print("Keyboard touch emulation enabled:")
            print("  Arrow keys = Swipe gestures")
            print("  Space = Tap")

        except ImportError:
            print("keyboard library not available. Install with: pip install keyboard")
            print("Note: May require root/admin privileges")

    def disable(self):
        """Disable keyboard emulation."""
        if self.enabled:
            try:
                import keyboard
                keyboard.unhook_all()
                self.enabled = False
            except:
                pass
