# vim: set expandtab shiftwidth=4 softtabstop=4:

# === UCSF ChimeraX Copyright ===
# Copyright 2016 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  For details see:
# http://www.rbvi.ucsf.edu/chimerax/docs/licensing.html
# This notice must be embedded in or attached to all copies,
# including partial copies, of the software or any revisions
# or derivations thereof.
# === UCSF ChimeraX Copyright ===

from chimerax.core.toolshed import BundleAPI

class _DistUIBundleAPI(BundleAPI):

    @staticmethod
    def initialize(session, bundle_info):
        """Install distance mouse mode"""
        if session.ui.is_gui:
            mm = session.ui.mouse_modes
            from .mouse_dist import DistMouseMode
            mm.add_mode(DistMouseMode(session))

            def criteria(session):
                from chimerax.atomic import selected_atoms
                return len(selected_atoms(session)) == 2
            def callback(session):
                from chimerax.atomic import selected_atoms
                a1, a2 = selected_atoms(session)
                command = "dist %s %s" % (a1.string(style="command line"),
                    a2.string(style="command line"))
                from chimerax.core.commands import run
                run(session, command)
            from chimerax.ui import SelectMouseMode
            SelectMouseMode.register_menu_entry("Distance", criteria, callback)

bundle_api = _DistUIBundleAPI()
