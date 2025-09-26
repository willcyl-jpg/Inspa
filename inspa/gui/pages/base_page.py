"""Base class for all pages in the Builder GUI."""
import customtkinter as ctk
from typing import Any

class BasePage(ctk.CTkFrame):
    def __init__(self, parent: Any, controller: Any, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.parent = parent
        self.controller = controller
        self.setup_ui()

    def setup_ui(self):
        """Setup the UI for the page. To be implemented by subclasses."""
        pass

    def get_data(self) -> dict:
        """Return data from the page. To be implemented by subclasses."""
        return {}

    def load_data(self, data: dict):
        """Load data into the page. To be implemented by subclasses."""
        pass
