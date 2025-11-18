"""Touch input handler for the e-ink display."""
import time
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

    def __init__(self, width=250, height=122):
        self.width = width
        self.height = height
        self.simulation_mode = True  # Will be set based on hardware availability

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
        Initialize touch hardware for Waveshare 2.13" V4 display.

        The V4 uses a capacitive touch controller accessible via I2C.
        IMPORTANT: The touch controller requires GPIO initialization (reset sequence)
        before it will respond with touch data.
        """
        self.touch_driver = None
        self.gpio_touch = None

        # Step 1: Initialize GPIO and reset touch controller
        # This is CRITICAL - the touch controller won't report touches without this
        try:
            from src.touch.gpio_touch import TouchGPIO
            self.gpio_touch = TouchGPIO()
            self.gpio_touch.init()
            print("✓ Touch controller GPIO initialized and reset")
        except Exception as e:
            print(f"Warning: GPIO touch init failed: {e}")
            print("Touch controller may not respond without GPIO reset")

        # Step 2: Try Waveshare's GT1151 module (most common for V4)
        try:
            from waveshare_epd import gt1151
            self.touch_driver = gt1151.GT1151()
            print("✓ Touch hardware initialized (GT1151)")
            return
        except (ImportError, Exception) as e:
            print(f"GT1151 module not available: {e}")

        # Try generic TP module
        try:
            from waveshare_epd import TP
            self.touch_driver = TP.TP()
            print("✓ Touch hardware initialized (TP module)")
            return
        except (ImportError, Exception) as e:
            print(f"TP module not available: {e}")

        # Try direct I2C access as fallback
        try:
            import smbus2
            self.i2c_bus = smbus2.SMBus(1)  # I2C bus 1 on Raspberry Pi
            # Waveshare 2.13" V4 uses address 0x14 (not the standard 0x5D)
            self.touch_i2c_addr = 0x14
            # Test communication
            self.i2c_bus.read_byte(self.touch_i2c_addr)
            print("✓ Touch hardware initialized (I2C direct at 0x14)")
            return
        except Exception as e:
            print(f"I2C touch init failed: {e}")

        # No hardware available
        raise NotImplementedError("Touch hardware not available")

    def set_gesture_callback(self, callback: Callable[[TouchEvent], None]):
        """Set callback function for gesture events."""
        self.on_gesture = callback

    def poll(self) -> Optional[TouchEvent]:
        """
        Poll for touch events from hardware.

        Returns:
            TouchEvent if a gesture was detected, None otherwise
        """
        if self.simulation_mode:
            return None

        try:
            # Read touch data from Waveshare driver
            if self.touch_driver and hasattr(self.touch_driver, 'scan'):
                touch_data = self.touch_driver.scan()
                if not touch_data:
                    # No touch or touch released
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
                    return None

                # Touch detected - get first touch point
                x, y = touch_data[0]  # Waveshare typically returns list of (x, y) tuples

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

            # Alternative: GT1151 interrupt-based I2C reading
            elif hasattr(self, 'i2c_bus') and self.gpio_touch:
                # GT1151 uses interrupt-based touch detection
                # Only read I2C when INT pin goes LOW
                try:
                    int_state = self.gpio_touch.read_int_pin()

                    if int_state == 0:  # INT pin LOW = touch detected
                        # Read GT1151 status register (0x814E)
                        status = self.i2c_bus.read_byte_data(self.touch_i2c_addr, 0x4E)

                        # Check if valid touch data (bit 0x80 set)
                        if status & 0x80:
                            touch_count = status & 0x0F  # Lower 4 bits = number of touches

                            if 1 <= touch_count <= 5:
                                # Read touch data from 0x814F (8 bytes per touch)
                                touch_data = self.i2c_bus.read_i2c_block_data(
                                    self.touch_i2c_addr, 0x4F, touch_count * 8
                                )

                                # Clear status register to acknowledge touch
                                self.i2c_bus.write_byte_data(self.touch_i2c_addr, 0x4E, 0x00)

                                # Parse first touch point (bytes 0-7)
                                # Byte 0: Track ID
                                # Bytes 1-2: X coordinate (little endian)
                                # Bytes 3-4: Y coordinate (little endian)
                                # Bytes 5-6: Size/pressure
                                x = (touch_data[2] << 8) | touch_data[1]
                                y = (touch_data[4] << 8) | touch_data[3]

                                if not hasattr(self, '_touch_debug_shown'):
                                    print(f"✓ Touch detected! X={x}, Y={y}")
                                    self._touch_debug_shown = True

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
                                # Invalid touch count
                                self.i2c_bus.write_byte_data(self.touch_i2c_addr, 0x4E, 0x00)
                        else:
                            # No valid touch data, clear status anyway
                            self.i2c_bus.write_byte_data(self.touch_i2c_addr, 0x4E, 0x00)

                    else:  # INT pin HIGH = no touch
                        # Check if touch was released
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
                    # I2C read error, skip this poll
                    if not hasattr(self, '_i2c_error_shown'):
                        print(f"Touch I2C error: {e}")
                        self._i2c_error_shown = True
                    pass

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
        if self.gpio_touch:
            try:
                self.gpio_touch.cleanup()
                print("Touch GPIO resources cleaned up")
            except Exception as e:
                print(f"Error cleaning up GPIO: {e}")


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
