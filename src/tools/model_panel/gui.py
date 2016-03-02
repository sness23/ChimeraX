# vim: set expandtab shiftwidth=4 softtabstop=4:

from chimerax.core.tools import ToolInstance


class ModelPanel(ToolInstance):

    SESSION_ENDURING = True
    # if SESSION_ENDURING is True, tool instance not deleted at session closure
    SIZE = (200, 250)

    def __init__(self, session, bundle_info):
        ToolInstance.__init__(self, session, bundle_info)
        self.display_name = "Models"
        from chimerax.core.ui.gui import MainToolWindow

        class ModelPanelWindow(MainToolWindow):
            close_destroys = False

        self.tool_window = ModelPanelWindow(self, size=self.SIZE)
        self.settings = ModelPanelSettings(session, "ModelPanel")
        parent = self.tool_window.ui_area
        import wx
        import wx.grid
        last = self.settings.last_use
        from time import time
        now = self.settings.last_use = time()
        short_titles = last != None and now - last < 777700 # about 3 months
        self.table = wx.grid.Grid(parent, size=(200, 150))
        self.table.CreateGrid(5, 4)
        self.table.SetColLabelValue(0, "ID")
        self.table.SetColSize(0, 25)
        self.table.SetColLabelValue(1, " ")
        self.table.SetColSize(1, -1)
        title = "S" if short_titles else "Shown"
        self.table.SetColLabelValue(2, title)
        self.table.SetColSize(2, -1)
        self.table.SetColFormatBool(2)
        from chimerax.core.graphics import Drawing
        Drawing.triggers.add_handler('display changed', self._initiate_fill_table)
        self.table.SetColLabelValue(3, "Name")
        self.table.HideRowLabels()
        self.table.SetDefaultCellAlignment(wx.ALIGN_CENTRE, wx.ALIGN_BOTTOM)
        self.table.EnableEditing(False)
        self.table.SelectionMode = wx.grid.Grid.GridSelectRows
        self.table.CellHighlightPenWidth = 0
        self._fill_table()
        self.table.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self._left_click)
        from chimerax.core.models import ADD_MODELS, REMOVE_MODELS
        self.session.triggers.add_handler(ADD_MODELS, self._initiate_fill_table)
        self.session.triggers.add_handler(REMOVE_MODELS, self._initiate_fill_table)
        self.session.triggers.add_handler("atomic changes", self._changes_cb)
        self._frame_drawn_handler = None
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.table, 1, wx.EXPAND)
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        for model_func in [close, hide, show, view]:
            button = wx.Button(parent, label=model_func.__name__.capitalize())
            button.Bind(wx.EVT_BUTTON, lambda e, self=self, mf=model_func, ses=session:
                mf([self.models[i] for i in self.table.SelectedRows] or self.models, ses))
            button_sizer.Add(button, 0, wx.EXPAND)
        sizer.Add(button_sizer, 0, wx.ALIGN_CENTER_VERTICAL)
        parent.SetSizerAndFit(sizer)
        self.tool_window.manage(placement="right")

    @classmethod
    def get_singleton(self, session):
        from chimerax.core import tools
        return tools.get_singleton(session, ModelPanel, 'model panel', create=False)

    def _changes_cb(self, trigger_name, data):
        reasons = data["Atom"].reasons
        if "color changed" in reasons or 'display changed' in reasons:
            self._initiate_fill_table()

    def _initiate_fill_table(self, *args):
        # in order to allow molecules to be drawn as quickly as possible,
        # delay the update of the table until the 'frame drawn' trigger fires
        if self._frame_drawn_handler is None:
            self._frame_drawn_handler = self.session.triggers.add_handler(
                "frame drawn", self._fill_table)

    def _fill_table(self, *args):
        # prevent repaints untill the end of this method...
        import wx
        locker = wx.grid.GridUpdateLocker(self.table)
        nr = self.table.NumberRows
        sel = self.table.SelectedRows
        if nr:
            self.table.DeleteRows(0, nr)
        models = self.session.models.list()
        self.table.AppendRows(len(models))
        self.models = sorted(models, key=lambda m: m.id)
        for i, model in enumerate(self.models):
            self.table.SetCellValue(i, 0, model.id_string())
            self.table.SetCellBackgroundColour(i, 1, self._model_color(model))
            self.table.SetCellValue(i, 2, "1" if model.display else "")
            self.table.SetCellValue(i, 3, getattr(model, "name", "(unnamed)"))
        self.table.AutoSizeColumns()
        if nr == self.table.NumberRows:
            for i, row in enumerate(sel):
                self.table.SelectRow(row, addToSelected=bool(i))
        del locker

        self._frame_drawn_handler = None
        from chimerax.core.triggerset import DEREGISTER
        return DEREGISTER

    def _left_click(self, event):
        if event.Col == 2:
            model = self.models[event.Row]
            model.display = not model.display
        event.Skip()

    def _model_color(self, model):
        return model.single_color

from chimerax.core.settings import Settings
class ModelPanelSettings(Settings):
    AUTO_SAVE = {
        'last_use': None
    }

def close(models, session):
    session.models.close(models)

def hide(models, session):
    for m in models:
        m.display = False

_mp = None
def model_panel(session, bundle_info):
    global _mp
    if _mp is None:
        _mp = ModelPanel(session, bundle_info)
    return _mp

def show(models, session):
    for m in models:
        m.display = True

def view(models, session):
    from chimerax.core.objects import Objects
    view_objects = Objects(models=models)
    for model in models:
        if getattr(model, 'atoms', None):
            view_objects.add_atoms(model.atoms)
    from chimerax.core.commands.view import view
    view(session, view_objects)

