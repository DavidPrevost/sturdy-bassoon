"""E-ink display driver for Waveshare e-Paper HAT."""
import time
import sys
from pathlib import Path
from PIL import Image

try:
    # Use TP_lib which shares GPIO with touch controller
    # Add to path if not already there
    repo_root = Path(__file__).parent.parent.parent
    waveshare_lib = repo_root / "python" / "lib"
    if str(waveshare_lib) not in sys.path:
        sys.path.insert(0, str(waveshare_lib))

    from TP_lib import epd2in13_V4
    DISPLAY_AVAILABLE = True
except ImportError:
    # Fallback for development/testing without hardware
    DISPLAY_AVAILABLE = False
    print("Warning: Waveshare TP_lib library not found. Running in simulation mode.")


class DisplayDriver:
    """Wrapper for e-ink display hardware."""

    def __init__(self, width=250, height=122):
        self.width = width
        self.height = height
        self.epd = None
        self.initialized = False
        self.simulation_mode = not DISPLAY_AVAILABLE

        if DISPLAY_AVAILABLE:
            try:
                self.epd = epd2in13_V4.EPD()
                print("E-ink display driver initialized")
            except Exception as e:
                print(f"Failed to initialize display hardware: {e}")
                self.simulation_mode = True

    def init(self, full=True):
        """Initialize the display."""
        if self.simulation_mode:
            print("[SIMULATION] Display initialized (full={})".format(full))
            self.initialized = True
            return

        try:
            # TP_lib requires update mode constant (FULL_UPDATE or PART_UPDATE)
            if full:
                self.epd.init(self.epd.FULL_UPDATE)
            else:
                self.epd.init(self.epd.PART_UPDATE)
            self.epd.Clear(0xFF)
            self.initialized = True
            print("Display initialized successfully")
        except Exception as e:
            print(f"Error initializing display: {e}")
            raise

    def display_image(self, image: Image.Image, partial=False):
        """
        Display an image on the e-ink screen.

        Args:
            image: PIL Image object (will be converted to 1-bit)
            partial: Use partial refresh (faster but may have ghosting)
        """
        if not self.initialized:
            self.init(full=not partial)

        # Ensure image is correct size and mode
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))

        # Convert to 1-bit black and white
        image = image.convert('1')

        if self.simulation_mode:
            # Save image to file for debugging
            output_path = Path(__file__).parent.parent.parent / ".cache" / "display_output.png"
            output_path.parent.mkdir(exist_ok=True)
            image.save(output_path)
            print(f"[SIMULATION] Image saved to {output_path}")
            return

        try:
            if partial:
                self.epd.displayPartial(self.epd.getbuffer(image))
            else:
                self.epd.display(self.epd.getbuffer(image))
            print(f"Image displayed (partial={partial})")
        except Exception as e:
            print(f"Error displaying image: {e}")
            raise

    def clear(self):
        """Clear the display to white."""
        if self.simulation_mode:
            print("[SIMULATION] Display cleared")
            return

        try:
            self.epd.Clear(0xFF)
        except Exception as e:
            print(f"Error clearing display: {e}")

    def sleep(self):
        """Put display into low-power sleep mode."""
        if self.simulation_mode:
            print("[SIMULATION] Display entering sleep mode")
            return

        try:
            if self.epd:
                self.epd.sleep()
                print("Display entering sleep mode")
        except Exception as e:
            print(f"Error putting display to sleep: {e}")

    def __del__(self):
        """Cleanup on deletion."""
        if not self.simulation_mode and self.epd:
            try:
                self.sleep()
            except:
                pass
