"""Touch-based input screens for user interaction."""
from typing import Optional, Callable
from src.display.renderer import Renderer
from src.touch.handler import TouchEvent, Gesture


class NumpadScreen:
    """
    Touch numpad for entering numbers (ZIP codes, etc.).

    Layout on 250x122 display:
    ┌─────────────────────┐
    │   ZIP: 12345_       │  Title area (20px)
    ├─────────────────────┤
    │  [1] [2] [3]        │
    │  [4] [5] [6]        │  Numpad (90px)
    │  [7] [8] [9]        │
    │  [<] [0] [✓]        │
    └─────────────────────┘
    """

    def __init__(self, max_digits: int = 5, title: str = "Enter ZIP Code"):
        self.max_digits = max_digits
        self.title = title
        self.current_value = ""
        self.on_submit: Optional[Callable[[str], None]] = None
        self.on_cancel: Optional[Callable[[], None]] = None

        # Button layout (3 columns x 4 rows)
        self.button_width = 75
        self.button_height = 22
        self.button_spacing = 5
        self.start_x = 10
        self.start_y = 30

        # Define button positions and labels
        self.buttons = self._create_button_layout()

    def _create_button_layout(self):
        """Create button positions and labels."""
        buttons = []

        # Row 1: 1 2 3
        # Row 2: 4 5 6
        # Row 3: 7 8 9
        # Row 4: < 0 ✓

        keys = [
            ['1', '2', '3'],
            ['4', '5', '6'],
            ['7', '8', '9'],
            ['<', '0', '✓']
        ]

        for row_idx, row in enumerate(keys):
            for col_idx, key in enumerate(row):
                x = self.start_x + col_idx * (self.button_width + self.button_spacing)
                y = self.start_y + row_idx * (self.button_height + self.button_spacing)

                buttons.append({
                    'key': key,
                    'x': x,
                    'y': y,
                    'width': self.button_width,
                    'height': self.button_height
                })

        return buttons

    def render(self, renderer: Renderer):
        """Render the numpad screen."""
        # Title
        renderer.draw_text(
            self.title,
            renderer.width // 2,
            5,
            font_size=11,
            bold=True,
            anchor="mt"
        )

        # Current value display
        display_text = self.current_value if self.current_value else "_" * self.max_digits
        renderer.draw_text(
            display_text,
            renderer.width // 2,
            18,
            font_size=12,
            bold=True,
            anchor="mt"
        )

        # Draw buttons
        for btn in self.buttons:
            # Button box
            renderer.draw_rectangle(
                btn['x'],
                btn['y'],
                btn['width'],
                btn['height'],
                outline=0
            )

            # Button label (centered)
            label_x = btn['x'] + btn['width'] // 2
            label_y = btn['y'] + btn['height'] // 2

            font_size = 14 if btn['key'].isdigit() else 12
            renderer.draw_text(
                btn['key'],
                label_x,
                label_y,
                font_size=font_size,
                bold=True,
                anchor="mm"
            )

    def handle_touch(self, event: TouchEvent) -> bool:
        """
        Handle touch event on numpad.

        Returns:
            True if input is complete (submitted or cancelled)
        """
        if event.gesture != Gesture.TAP or not event.position:
            return False

        x, y = event.position

        # Find which button was tapped
        for btn in self.buttons:
            if (btn['x'] <= x <= btn['x'] + btn['width'] and
                btn['y'] <= y <= btn['y'] + btn['height']):

                key = btn['key']

                if key.isdigit():
                    # Add digit
                    if len(self.current_value) < self.max_digits:
                        self.current_value += key
                        print(f"Input: {self.current_value}")

                elif key == '<':
                    # Backspace
                    if self.current_value:
                        self.current_value = self.current_value[:-1]
                        print(f"Input: {self.current_value}")
                    else:
                        # Empty backspace = cancel
                        if self.on_cancel:
                            self.on_cancel()
                        return True

                elif key == '✓':
                    # Submit
                    if len(self.current_value) == self.max_digits:
                        if self.on_submit:
                            self.on_submit(self.current_value)
                        return True
                    else:
                        print(f"Need {self.max_digits} digits, have {len(self.current_value)}")

                return False

        return False

    def reset(self):
        """Clear the current input."""
        self.current_value = ""


class InputMode:
    """
    Manages overlay input screens (numpad, etc.).

    This allows widgets to trigger input overlays for user interaction.
    """

    def __init__(self):
        self.active_screen = None
        self.callback = None

    def show_numpad(self, title: str, max_digits: int, callback: Callable[[str], None]):
        """Show numpad for number input."""
        numpad = NumpadScreen(max_digits=max_digits, title=title)
        numpad.on_submit = self._on_submit
        numpad.on_cancel = self._on_cancel
        self.active_screen = numpad
        self.callback = callback

    def _on_submit(self, value: str):
        """Handle input submission."""
        if self.callback:
            self.callback(value)
        self.close()

    def _on_cancel(self):
        """Handle input cancellation."""
        self.close()

    def close(self):
        """Close the active input screen."""
        self.active_screen = None
        self.callback = None

    def is_active(self) -> bool:
        """Check if an input screen is active."""
        return self.active_screen is not None

    def render(self, renderer: Renderer):
        """Render the active input screen."""
        if self.active_screen:
            self.active_screen.render(renderer)

    def handle_touch(self, event: TouchEvent) -> bool:
        """
        Handle touch event.

        Returns:
            True if event was handled by input screen
        """
        if self.active_screen:
            return self.active_screen.handle_touch(event)
        return False
