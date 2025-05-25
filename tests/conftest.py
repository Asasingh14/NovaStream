import sys
import types

# Create a dummy tkinter module
_tkinter = types.ModuleType("tkinter")
_tkinter.Tk = lambda *args, **kwargs: types.SimpleNamespace(withdraw=lambda: None, destroy=lambda: None)
sys.modules['tkinter'] = _tkinter

# Create dummy tkinter.messagebox
_messagebox = types.ModuleType("tkinter.messagebox")
_messagebox.showinfo = lambda *args, **kwargs: None
_messagebox.showerror = lambda *args, **kwargs: None
sys.modules['tkinter.messagebox'] = _messagebox

# Create dummy tkinter.simpledialog
_simpledialog = types.ModuleType("tkinter.simpledialog")
_simpledialog.askinteger = lambda *args, **kwargs: None
_simpledialog.askstring = lambda *args, **kwargs: None
sys.modules['tkinter.simpledialog'] = _simpledialog 