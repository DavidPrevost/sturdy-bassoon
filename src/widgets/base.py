"""Base widget class for the e-ink dashboard."""
from abc import ABC, abstractmethod
from src.display.renderer import Renderer


class Widget(ABC):
    """Base class for all dashboard widgets."""

    def __init__(self, config, cache=None):
        """
        Initialize widget.

        Args:
            config: Config object with settings
            cache: APICache object for caching API calls
        """
        self.config = config
        self.cache = cache
        self.last_update = None

    @abstractmethod
    def render(self, renderer: Renderer, bounds: tuple) -> None:
        """
        Render the widget content.

        Args:
            renderer: Renderer object to draw with
            bounds: (x, y, width, height) tuple defining the widget area
        """
        pass

    @abstractmethod
    def update_data(self) -> bool:
        """
        Fetch/update widget data.

        Returns:
            True if data was updated, False otherwise
        """
        pass

    def get_name(self) -> str:
        """Get widget name."""
        return self.__class__.__name__.replace('Widget', '').lower()

    def needs_update(self, force=False) -> bool:
        """
        Check if widget needs to update its data.

        Args:
            force: Force update regardless of timing

        Returns:
            True if update is needed
        """
        if force or self.last_update is None:
            return True

        # Default: update every refresh cycle
        return True
