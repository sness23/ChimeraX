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

# get PDB shared lib loaded...
import chimerax.atomic.pdb  # noqa
from .mmcif import (  # noqa
    get_cif_tables, get_mmcif_tables, get_mmcif_tables_from_metadata,
    open_mmcif, fetch_mmcif, citations,
    TableMissingFieldsError, CIFTable,
    find_template_residue, load_mmCIF_templates,
    add_citation, add_software,
)

from chimerax.core.toolshed import BundleAPI


class _mmCIFioAPI(BundleAPI):

    @staticmethod
    def fetch_from_database(session, identifier, ignore_cache=False, database_name=None,
                            format_name=None, **kw):
        # 'fetch_from_database' is called by session code to fetch data with give identifier
        # returns (list of models, status message)
        from . import mmcif
        fetchers = {
            "pdb": mmcif.fetch_mmcif,
            "pdbe": mmcif.fetch_mmcif_pdbe,
            "pdbe_updated": mmcif.fetch_mmcif_pdbe_updated,
            "pdbj": mmcif.fetch_mmcif_pdbj,
            "ccd": mmcif.fetch_ccd,
        }
        try:
            fetcher = fetchers[database_name]
        except KeyError:
            from chimerax.core.errors import UserError
            raise UserError("Unknown database for fetching mmCIF: '%s'.  Known databases are: %s"
                            % (database_name, ", ".join(list(fetchers.keys()))))
        return fetcher(session, identifier, ignore_cache=ignore_cache, **kw)

    @staticmethod
    def open_file(session, path, file_name, *, auto_style=True, coordsets=False, atomic=True,
                  max_models=None, log_info=True, combine_sym_atoms=True):
        # 'open_file' is called by session code to open a file
        # returns (list of models, status message)
        from . import mmcif
        return mmcif.open_mmcif(session, path, file_name, auto_style=auto_style,
                                coordsets=coordsets, atomic=atomic, max_models=max_models,
                                log_info=log_info, combine_sym_atoms=combine_sym_atoms)

    @staticmethod
    def save_file(session, path, *, models=None, rel_model=None, selected_only=None, displayed_only=None):
        # 'save_file' is called by session code to save a file
        from . import mmcif_write
        return mmcif_write.write_mmcif(session, path, models=models, rel_model=rel_model, selected_only=selected_only, displayed_only=displayed_only)

    @staticmethod
    def run_provider(session, name, mgr):
        if mgr == session.open_command:
            if name == "mmCIF":
                from chimerax.open_command import OpenerInfo

                class Info(OpenerInfo):
                    def open(self, session, data, file_name, **kw):
                        from . import mmcif
                        return mmcif.open_mmcif(session, data, file_name, **kw)

                    @property
                    def open_args(self):
                        from chimerax.core.commands import BoolArg, IntArg
                        return {
                            'atomic': BoolArg,
                            'auto_style': BoolArg,
                            'combine_sym_atoms': BoolArg,
                            'coordsets': BoolArg,
                            'log_info': BoolArg,
                            'max_models': IntArg,
                        }
            elif name == "ccd":
                from chimerax.open_command import FetcherInfo
                from . import mmcif

                class Info(FetcherInfo):
                    def fetch(self, session, ident, format_name, ignore_cache,
                              fetcher=mmcif.fetch_ccd, **kw):
                        return fetcher(session, ident, ignore_cache=ignore_cache, **kw)
            else:
                from chimerax.open_command import FetcherInfo
                from . import mmcif
                fetcher = {
                    "pdb": mmcif.fetch_mmcif,
                    "pdbe": mmcif.fetch_mmcif_pdbe,
                    "pdbe_updated": mmcif.fetch_mmcif_pdbe_updated,
                    "pdbj": mmcif.fetch_mmcif_pdbj,
                }[name]

                class Info(FetcherInfo):
                    def fetch(self, session, ident, format_name, ignore_cache,
                              fetcher=fetcher, **kw):
                        return fetcher(session, ident, ignore_cache=ignore_cache, **kw)

                    @property
                    def fetch_args(self):
                        from chimerax.core.commands import BoolArg, FloatArg
                        return {
                            'oversampling': FloatArg,
                            'structure_factors': BoolArg,
                        }
        else:
            from chimerax.save_command import SaverInfo

            class Info(SaverInfo):
                def save(self, session, path, **kw):
                    from . import mmcif_write
                    mmcif_write.write_mmcif(session, path, **kw)

                @property
                def save_args(self):
                    from chimerax.core.commands import BoolArg, ModelsArg, ModelArg
                    return {
                        'displayed_only': BoolArg,
                        'models': ModelsArg,
                        'rel_model': ModelArg,
                        'selected_only': BoolArg,
                    }

        return Info()


bundle_api = _mmCIFioAPI()
