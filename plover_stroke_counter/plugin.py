import wx
import threading
import queue
from plover.engine import StenoEngine

# Lazy import helper
def lazy_wx():
    import wx
    return wx

class StrokeCounterGUI(threading.Thread):
    def __init__(self):
        """Initialize the Stroke Counter GUI inside Plover."""
        super().__init__(daemon=True)  # Run GUI in a separate thread
        self.stroke_count = 0
        self.wx_ready = threading.Event()  # Flag for wx readiness
        self.stroke_queue = queue.Queue()  # Thread-safe queue for strokes

        # Start the GUI thread
        self.start()

    def run(self):
        """Run wxPython GUI in its own thread."""
        wx = lazy_wx()

        if not wx.GetApp():
            self.wx_app = wx.App(False)  # Create wx.App in GUI thread

        self.frame = wx.Frame(None, title="Stroke Counter", size=(250, 150))
        panel = wx.Panel(self.frame)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Stroke count display
        self.text = wx.StaticText(panel, label="Total Strokes: 0")
        sizer.Add(self.text, 0, wx.ALL | wx.CENTER, 10)

        # Reset Button
        self.reset_button = wx.Button(panel, label="Reset Counter")
        sizer.Add(self.reset_button, 0, wx.ALL | wx.CENTER, 5)

        # Bind button click event
        self.reset_button.Bind(wx.EVT_BUTTON, self.reset_count)

        # Attach layout to panel
        panel.SetSizer(sizer)

        # Show the window
        self.frame.Show()
        self.wx_ready.set()  # Indicate wxPython is ready

        # Start stroke processing loop in the background (non-blocking)
        wx.CallLater(100, self.process_strokes)  

        # Start the event loop
        wx.CallAfter(self.frame.Layout)
        wx.GetApp().MainLoop()

    def process_strokes(self):
        """Process queued stroke updates without blocking the GUI."""
        wx = lazy_wx()

        while not self.stroke_queue.empty():
            strokes = self.stroke_queue.get()
            wx.CallAfter(self._update_count, strokes)

        # Schedule the next check in 100ms
        wx.CallLater(100, self.process_strokes)  

    def update_count(self):
        """Add a new stroke to the queue (ensuring no loss of strokes)."""
        self.stroke_queue.put(1)  # Each stroke is +1

    def _update_count(self, strokes):
        """Actually update the stroke counter."""
        self.stroke_count += strokes
        self.text.SetLabel(f"Total Strokes: {self.stroke_count}")
        self.frame.Layout()

    def reset_count(self, event=None):
        """Schedule reset operation."""
        wx = lazy_wx()
        wx.CallAfter(self._reset_count)

    def _reset_count(self):
        """Reset stroke count to zero."""
        self.stroke_count = 0
        self.text.SetLabel("Total Strokes: 0")
        self.frame.Layout()

    def close(self):
        """Close the GUI safely."""
        if self.wx_ready.is_set():
            wx = lazy_wx()
            wx.CallAfter(self.frame.Close)


class StrokeCounterPlugin:
    def __init__(self, engine: StenoEngine):
        """Initialize Stroke Counter Plugin inside Plover."""
        self.engine = engine
        self.gui = None
        self.engine.hook_connect("stroked", self.on_stroke)

        # Start GUI in a separate thread after 5 seconds
        threading.Timer(5, self.start).start()

    def start(self):
        """Create and show the GUI."""
        if self.gui is None:
            self.gui = StrokeCounterGUI()

    def on_stroke(self, stroke):
        """Schedule GUI update when a stroke is made."""
        if self.gui:
            self.gui.update_count()

    def stop(self):
        """Shut down GUI when the plugin is disabled."""
        if self.gui:
            self.gui.close()
            self.gui = None
        self.engine.hook_disconnect("stroked", self.on_stroke)

def plugin_init(engine):
    """Plover plugin entry point."""
    return StrokeCounterPlugin(engine)
