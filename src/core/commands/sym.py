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

def sym(session, molecules,
        symmetry = None, center = None, axis = None, coordinate_system = None, assembly = None,
        copies = False, clear = False, surface_only = False, resolution = None):
    '''
    Show molecular assemblies of molecular models defined in mmCIF files.
    These can be subassemblies or symmetrical copies with individual chains 
    placed according to matrices specified in the mmCIF file.

    Parameters
    ----------
    molecules : list of AtomicStructure
      List of molecules to show as assemblies.
    symmetry : cli.Symmetry
      Desired symmetry to display
    center : cli.Center
      Center of symmetry.  Default 0,0,0.
    axis : Axis
      Axis of symmetry.  Default z.
    coordinate_system : Place
      Transform mapping coordinates for center and axis arguments to scene coordinates.
    assembly : string
      The name of assembly in the mmCIF file. If this parameter is None
      then the names of available assemblies are printed in log.
    copies : bool
      Whether to make copies of the molecule chains.  If copies are not made
      then clones of the original molecule.  Copies are needed to give different
      colors or styles to each copy.  When copies are made a new model with
      submodels are created, one submode for each copy.
    clear : bool
      Revert to displaying no assembly, resets the use of any symmetry matrices.
    surface_only : bool
      Instead of showing instances of the molecule, show instances
      of surfaces of each chain.  The chain surfaces are computed if
      they do not already exist.
    resolution : float
      Resolution for computing surfaces when surface_only is true.
    '''
    if len(molecules) == 0:
        from ..errors import UserError
        raise UserError('No molecules specified.')

    if symmetry is not None:
        if assembly is not None:
            from ..errors import UserError
            raise UserError('Cannot specify explicit symmetry and the assembly option.')
        if clear:
            from ..errors import UserError
            raise UserError('Cannot specify explicit symmetry and the clear option.')
        transforms = symmetry.positions(center, axis, coordinate_system, molecules[0])
        show_symmetry(molecules, transforms, copies, surface_only, resolution, session)
        return
            
    for m in molecules:
        if clear:
            from ..geometry import Places
            m.positions = Places([m.position])	# Keep only first position.
            for s in m.surfaces():
                s.positions = Places([s.position])
            continue
        assem = pdb_assemblies(m)
        if assembly is None:
            ainfo = '\n'.join(' %s = %s (%s)' % (a.id,a.description,a.copy_description(m))
                              for a in assem)
            anames = ainfo if assem else "no assemblies"
            session.logger.info('Assemblies for %s:\n%s' % (m.name, anames))
            for a in assem:
                a.create_selector(m)
        else:
            amap = dict((a.id, a) for a in assem)
            if not assembly in amap:
                from ..errors import UserError
                raise UserError('Assembly "%s" not found, have %s'
                                % (assembly, ', '.join(a.id for a in assem)))
            a = amap[assembly]
            if copies:
                a.show_copies(m, surface_only, resolution, session)
            elif surface_only:
               a.show_surfaces(m, resolution, session)
            else:
                a.show(m, session)

def register_command(session):
    from . import CmdDesc, register, AtomicStructuresArg, StringArg, NoArg, FloatArg
    from . import CenterArg, AxisArg, SymmetryArg, CoordSysArg
    _sym_desc = CmdDesc(
        required = [('molecules', AtomicStructuresArg)],
        optional = [('symmetry', SymmetryArg)],
        keyword = [('center', CenterArg),
                   ('axis', AxisArg),
                   ('coordinate_system', CoordSysArg),
                   ('assembly', StringArg),
                   ('copies', NoArg),
                   ('clear', NoArg),
                   ('surface_only', NoArg),
                   ('resolution', FloatArg)],
        synopsis = 'create model copies')
    register('sym', _sym_desc, sym)

def show_symmetry(molecules, transforms, copies, surface_only, resolution, session):
    if copies:
        from ..models import Model
        g = Model('%d copies' % len(transforms), session)
        for i, tf in enumerate(transforms):
            if len(molecules) > 1:
                # Add grouping model if more the one model is being copied
                ci = Model('copy %d' % (i+1), session)
                ci.position = tf
                g.add([ci])
                copies = [m.copy() for m in molecules]
                for c,m in zip(copies, molecules):
                    c.position = m.scene_position
                ci.add(copies)
            else:
                m0 = molecules[0]
                c = m0.copy()
                c.position = tf * m0.scene_position
                g.add([c])
        session.models.add([g])
    else:
        # Instancing    
        for m in molecules:
            # Transforms are in scene coordinates, so convert to molecule coordinates
            spos = m.scene_position
            symops = transforms if spos.is_identity() else transforms.transform_coordinates(spos)
            if surface_only:
                from .surface import surface
                surfs = surface(session, m.atoms, resolution = resolution)
                for s in surfs:
                    s.positions =  s.positions * symops
            else:
                m.positions = m.positions * symops

def pdb_assemblies(m):
    if not hasattr(m, 'filename') or not m.filename.endswith('.cif'):
        return []
    if hasattr(m, 'assemblies'):
        return m.assemblies
    m.assemblies = alist = mmcif_assemblies(m)
    return alist

def mmcif_assemblies(model):
    table_names = ('pdbx_struct_assembly',
                   'pdbx_struct_assembly_gen',
                   'pdbx_struct_oper_list',
                   'pdbx_poly_seq_scheme',
                   'pdbx_nonpoly_scheme')
    from ..atomic import mmcif
    assem, assem_gen, oper, cremap1, cremap2 = mmcif.get_mmcif_tables(model.filename, table_names)
    if assem is None or assem_gen is None or oper is None:
        return []

    name = assem.mapping('id', 'details')
    ids = list(name.keys())
    ids.sort()

    cops = assem_gen.fields(('assembly_id', 'oper_expression', 'asym_id_list'))
    chain_ops = {}
    for id, op_expr, cids in cops:
        chain_ops.setdefault(id,[]).append((cids.split(','), op_expr))

    ops = {}
    mat = oper.fields(('id',
                       'matrix[1][1]', 'matrix[1][2]', 'matrix[1][3]', 'vector[1]',
                       'matrix[2][1]', 'matrix[2][2]', 'matrix[2][3]', 'vector[2]',
                       'matrix[3][1]', 'matrix[3][2]', 'matrix[3][3]', 'vector[3]'))
    from ..geometry import Place
    for id, m11,m12,m13,m14,m21,m22,m23,m24,m31,m32,m33,m34 in mat:
        ops[id] = Place(matrix = ((m11,m12,m13,m14),(m21,m22,m23,m24),(m31,m32,m33,m34)))

    cmap = chain_id_changes(cremap1, cremap2)

    alist = [Assembly(id, name[id], chain_ops[id], ops, cmap) for id in ids]
    return alist

#
# Assemblies described using mmCIF chain ids but ChimeraX uses author chain ids.
# Map author chain id and residue number to mmCIF chain id.
# Only include entries if chain id is changed.
#
def chain_id_changes(poly_seq_scheme, nonpoly_scheme):
    cmap = {}
    if not poly_seq_scheme is None:
        # Note the pdb_seq_num (and not the auth_seq_num) in this table corresponds to
        # auth_seq_id in the atom_site table.  Example 3efz.
        pcnc = poly_seq_scheme.fields(('asym_id', 'pdb_seq_num', 'pdb_strand_id'))
        cmap = dict(((auth_cid, int(auth_resnum)), mmcif_cid)
                    for mmcif_cid, auth_resnum, auth_cid in pcnc
                    if mmcif_cid != auth_cid and auth_resnum != '?')
    if not nonpoly_scheme is None:
        ncnc = nonpoly_scheme.fields(('asym_id', 'pdb_seq_num', 'pdb_strand_id'))
        ncmap = dict(((auth_cid, int(auth_resnum)), mmcif_cid)
                     for mmcif_cid, auth_resnum, auth_cid in ncnc
                     if mmcif_cid != auth_cid and auth_resnum != '?')
        cmap.update(ncmap)
    return cmap

class Assembly:
    def __init__(self, id, description, chain_ops, operator_table, chain_map):
        self.id = id
        self.description = description

        cops = []
        for chain_ids, operator_expr in chain_ops:
            products = parse_operator_expression(operator_expr)
            ops = operator_products(products, operator_table)
            cops.append((chain_ids, operator_expr, ops))
        self.chain_ops = cops	# Triples of chain id list, operator expression, operator matrices

        self.operator_table = operator_table
        # Chain map maps ChimeraX (chain id, res number) to mmcif chain id used in chain_ids
        self.chain_map = chain_map

    def show(self, mol, session):
        mols = self._molecule_copies(mol, session)
        for (chain_ids, op_expr, ops), m in zip(self.chain_ops, mols):
            included_atoms, excluded_atoms = self._partition_atoms(m.atoms, chain_ids)
            if len(excluded_atoms) > 0:
                # Hide chains that are not part of assembly
                excluded_atoms.displays = False
                excluded_atoms.unique_residues.ribbon_displays = False
            self._show_atoms(included_atoms)
            m.positions = ops

    def _show_atoms(self, atoms):
        if not atoms.displays.all():
            # Show chains that have not atoms or ribbons shown.
            for mc, cid, catoms in atoms.by_chain:
                if not catoms.displays.any() and not catoms.residues.ribbon_displays.any():
                    catoms.displays = True

    def show_surfaces(self, mol, res, session):
        included_atoms, excluded_atoms = self._partition_atoms(mol.atoms, self._chain_ids())
        from .surface import surface
        surfs = surface(session, included_atoms, resolution = res)
        if len(excluded_atoms) > 0:
            surface(session, excluded_atoms, hide = True)
        for s in surfs:
            mmcif_cid = mmcif_chain_ids(s.atoms[:1], self.chain_map)[0]
            s.positions = self._chain_operators(mmcif_cid)

    def show_copies(self, mol, surface_only, resolution, session):
        mlist = []
        for chain_ids, op_expr, ops in self.chain_ops:
            for pos in ops:
                m = mol.copy()
                mlist.append(m)
                m.position = pos
                included_atoms, excluded_atoms = self._partition_atoms(m.atoms, chain_ids)
                if len(excluded_atoms) > 0:
                    excluded_atoms.delete()
                self._show_atoms(included_atoms)

        g = session.models.add_group(mlist)[0]
        g.name = '%s assembly %s' % (mol.name, self.id)

        if surface_only:
            from .surface import surface
            for m in mlist:
                surface(session, m.atoms, resolution = resolution)

        mol.display = False

    def _partition_atoms(self, atoms, chain_ids):
        mmcif_cids = mmcif_chain_ids(atoms, self.chain_map)
        from numpy import in1d, logical_not
        mask = in1d(mmcif_cids, chain_ids)
        included_atoms = atoms.filter(mask)
        logical_not(mask,mask)
        excluded_atoms = atoms.filter(mask)
        return included_atoms, excluded_atoms

    def _chain_ids(self):
        return sum((chain_ids for chain_ids, op_expr, ops in self.chain_ops), [])

    def _chain_operators(self, chain_id):
        cops = []
        for chain_ids, operator_expr, ops in self.chain_ops:
            if chain_id in chain_ids:
                cops.extend(ops)
        from ..geometry import Places
        return Places(cops)

    def _molecule_copies(self, mol, session):
        copies = [m for m in getattr(mol, '_sym_copies', []) if not m.deleted]
        nm = 1 + len(copies)
        n = len(self.chain_ops)
        if nm < n:
            # Create new copies
            mnew = [mol.copy('%s %d' % (mol.name,i)) for i in range(nm,n)]
            session.models.add(mnew)
            copies.extend(mnew)
            mol._sym_copies = copies
        elif nm > n:
            # Close extra copies
            session.models.close(copies[nm-n-1:])
            copies = copies[:nm-n-1]
            mol._sym_copies = copies
        mols = [mol] + copies
        return mols

    def copy_description(self, mol):
        atoms = mol.atoms
        groups = []
        for cids, expr, ops in self.chain_ops:
            # Convert mmcif chain ids to author chain ids
            incl_atoms, excl_atoms = self._partition_atoms(atoms, cids)
            author_cids = ','.join(incl_atoms.unique_chain_ids)
            copy = 'copy' if len(ops) == 1 else 'copies'
            groups.append('%d %s of chains %s' % (len(ops), copy, author_cids))
        return ', '.join(groups)

    def create_selector(self, mol):
        if self._is_subassembly():
            name = self.id
            sel_name = ('A' + name) if is_integer(name) else name
            def _selector(session, models, results, self=self, mol=mol):
                atoms = self._subassembly_atoms(mol)
                results.add_atoms(atoms)
            from . import register_selector
            register_selector(sel_name, _selector)

    def _is_subassembly(self):
        cops = self.chain_ops
        if len(cops) != 1:
            return False
        chain_ids, op_expr, ops = cops[0]
        if len(ops) != 1:
            return False
        return True
        
    def _subassembly_atoms(self, mol):
        chain_ids = self.chain_ops[0][0]
        included_atoms, excluded_atoms = self._partition_atoms(mol.atoms, chain_ids)
        return included_atoms

def is_integer(s):
    try:
        int(s)
    except:
        return False
    return True

def mmcif_chain_ids(atoms, chain_map):
    if len(chain_map) == 0:
        cids = atoms.residues.chain_ids
    else:
        r = atoms.residues
        from numpy import array
        cids = array([chain_map.get((cid,n), cid) for cid,n in zip(r.chain_ids, r.numbers)])
    return cids

def operator_products(products, oper_table):
    from ..geometry import Places
    p = Places(tuple(oper_table[e] for e in products[0]))
    if len(products) > 1:
        p = p * operator_products(products[1:], oper_table)
    return p

# Example from 1m4x.cif (1,10,23)(61,62,69-88)
def parse_operator_expression(expr):
    product = []
    import re
    factors = [e for e in re.split('[()]', expr) if e]
    for f in factors:
        terms = f.split(',')
        elem = []
        for t in terms:
            dash = t.split('-')
            if len(dash) == 2:
                elem.extend(str(e) for e in range(int(dash[0]), int(dash[1])+1))
            else:
                elem.append(t)
        product.append(elem)
    return product
