# vim: set expandtab shiftwidth=4 softtabstop=4:
from numpy import uint8, int32, float64, float32, bool as npy_bool
from .molc import string, cptr, pyobject, c_property, set_c_pointer, c_function, ctype_type_to_numpy, pointer
import ctypes
size_t = ctype_type_to_numpy[ctypes.c_size_t]   # numpy dtype for size_t

# -------------------------------------------------------------------------------
# These routines convert C++ pointers to Python objects and are used for defining
# the object properties.
#
def _atoms(a):
    from .molarray import Atoms
    return Atoms(a)
def _atom_pair(p):
    return (object_map(p[0],Atom), object_map(p[1],Atom))
def _bonds(b):
    from .molarray import Bonds
    return Bonds(b)
def _element(e):
    return object_map(e, Element)
def _pseudobonds(b):
    from .molarray import Pseudobonds
    return Pseudobonds(b)
def _residue(p):
    return object_map(p, Residue)
def _residues(r):
    from .molarray import Residues
    return Residues(r)
def _chains(c):
    from .molarray import Chains
    return Chains(c)
def _atomic_structure(p):
    return object_map(p, AtomicStructureData)
def _pseudobond_group_map(pbgc_map):
    from .pbgroup import PseudobondGroup
    pbg_map = dict((name, object_map(pbg,PseudobondGroup)) for name, pbg in pbgc_map.items())
    return pbg_map

# -----------------------------------------------------------------------------
#
class BaseSphere(type):
    """'Base class' for Atom, Sphere, etc.

        We avoid the diffculties of interacting through ctypes to the C++ layer
        by using BaseSphere as a metaclass for it's 'derived' classes, which places
        properties into them during class layout.
    """
    def __new__(meta, name, bases, attrs):
        related_class_info = {
            'Atom': (_atoms, 'AtomicStructure', 'structure', _atomic_structure, 'Bond', _bonds)
        }
        if name != meta.__name__:
            doc_marker = "[BS]"
            doc_add = \
                "{}: Generic attributes added by {}'s {} metaclass (and therefore usable " \
                "by in any class whose metaclass is {}, such as Atom, Sphere, etc.) " \
                "are noted by preceding their documentation with '{}'.".format(
                doc_marker, name, meta.__name__, meta.__name__, doc_marker)
            if "__doc__" in attrs:
                doc = attrs['__doc__']
                if doc:
                    if doc[-1] == '\n':
                        newlines = '\n'
                    else:
                        newlines = '\n\n'
                else:
                    newlines = ""
            else:
                doc = ""
                newlines = ""
            attrs["__doc__"] = doc + newlines + doc_add

            #define some vars useful later
            (collective, container_name, container_nickname, container_collective,
                conn_name, conn_collective) = related_class_info[name]
            connection = conn_name.lower()
            connections = connection + 's'
            connectible = name.lower()
            num_connections = 'num_' + connections

            # Property tuples are: (generic attr name, specific attr name,
            # other args to c_property, keywords to c_property, doc string).
            # If the specific attr name is None, then it's the same as the
            # generic attr name.
            #
            # Some shared properties (e.g. name) are defined in the C++ layer
            # for some classes but not others.  Those properties are defined
            # directly in the final class rather than via the metaclass.
            properties = [
                ('coord', None, (float64, 3), {},
                    "Coordinates as a numpy length 3 array, 64-bit float values."),
                ('connections', connections, (cptr, num_connections),
                    { 'astype': conn_collective, 'read_only': True },
                    "{}s connected to this {} as an array of :py:class:`{}` objects."
                    " Read only.".format(conn_name, connectible, conn_name)),
                ("neighbors", None, (cptr, num_connections), { 'astype': collective,
                    'read_only': True },
                    ":class:`.{}`\\ s connnected to this {} directly by one {}."
                    " Read only.".format(name, connectible, connection)),
                ("color", None, (uint8, 4), {},
                    "Color RGBA length 4 numpy uint8 array."),
                ("display", None, (npy_bool,), {},
                    "Whether to display the {}. Boolean value.".format(connectible)),
                ("draw_mode", None, (uint8,), {},
                    "Controls how the {} is depicted.\n\n|  Possible values:\n"
                    "SPHERE_STYLE\n"
                    "    Use full {} radius\n"
                    "BALL_STYLE\n"
                    "    Use reduced {} radius, but larger than {} radius\n"
                    "STICK_STYLE\n"
                    "    Match {} radius"
                    .format(connectible, connectible, connectible, connection, connection)),
                ("graph", container_nickname, (cptr,),
                    { 'astype': container_collective, 'read_only': True },
                    ":class:`.{}` the {} belongs to".format(container_name, connectible)),
                ("hide", None, (int32,), {},
                    "Whether {} is hidden (overrides display).  Integer bitmask."
                    "\n\n|  Possible values:\n"
                    "HIDE_RIBBON\n"
                    "    Hide mask for backbone atoms in ribbon.  "
                    "[Only applicable to Atom class.]".format(connectible)),
                ("num_connections", "num_{}".format(connections), (size_t,),
                    { 'read_only': True },
                    "Number of {}s connected to this {}. Read only."
                    .format(connection, connectible)),
                ("radius", None, (float32,), {}, "Radius of {}.".format(connectible)),
                ("selected", None, (npy_bool,), {},
                    "Whether the {} is selected.".format(connectible)),
                ("visible", None, (npy_bool,), { 'read_only': True },
                    "Whether {} is displayed and not hidden.".format(connectible)),
            ]
            prefix = connectible + '_'
            for generic_attr_name, specific_attr_name, args, kw, doc in properties:
                if specific_attr_name is None:
                    prop_attr_name = generic_attr_name
                else:
                    prop_attr_name = specific_attr_name
                attrs[generic_attr_name] = c_property(prefix + prop_attr_name, *args, **kw,
                    doc = doc_marker + " " + doc)
                if specific_attr_name is not None:
                    attrs[specific_attr_name] = c_property(prefix + prop_attr_name,
                        *args, **kw, doc = doc)

            # define symbolic constants
            for enum_val, sym_prefix in enumerate(['SPHERE', 'BALL', 'STICK']):
                attrs[sym_prefix + '_STYLE'] = enum_val
            attrs['HIDE_RIBBON'] = 0x1

            #define __init__ method in attrs dict
            exec("def __init__(self, c_pointer):\n"
                "    set_c_pointer(self, c_pointer)\n", globals(), attrs)

            # define connects_to method in attrs dict
            exec("def connects_to(self, {}):\n"
                "    '''{} Whether this {} is directly bonded to a specified {}.'''\n"
                "    f = c_function('{}_connects_to',\n"
                "                   args = (ctypes.c_void_p, ctypes.c_void_p),\n"
                "                   ret = ctypes.c_bool)\n"
                "    c = f(self._c_pointer, {}._c_pointer)\n"
                "    return c\n".format(connectible, doc_marker, connectible,
                connectible, connectible, connectible), globals(), attrs)

            # define scene_coord property in attrs dict
            exec("@property\n"
                "def scene_coord(self):\n"
                "    '''\n"
                "    {} {} center coordinates in the global scene coordinate system.\n"
                "    This accounts for the :class:`Drawing` positions for the hierarchy\n"
                "    of models this {} belongs to.\n"
                "    '''\n"
                "    return self.graph.scene_position * self.coord\n"
                .format(doc_marker, name, connectible), globals(), attrs)

        return super().__new__(meta, name, bases, attrs)

# -----------------------------------------------------------------------------
#
class Atom(metaclass=BaseSphere):
    '''
    An atom includes physical and graphical properties such as an element name,
    coordinates in space, and color and radius for rendering.

    To create an Atom use the :class:`.AtomicStructure` new_atom() method.
    '''
    # only Atom-specific attrs/methods here;
    # others provided by BaseSphere
    bfactor = c_property('atom_bfactor', float32,
        doc = "B-factor, floating point value.")
    chain_id = c_property('atom_chain_id', string, read_only = True,
        doc = "Protein Data Bank chain identifier. Limited to 4 characters."
        " Read only string.")
    element = c_property('atom_element', cptr, astype = _element, read_only = True,
        doc =  ":class:`Element` corresponding to the chemical element for the atom.")
    element_name = c_property('atom_element_name', string, read_only = True,
        doc = "Chemical element name. Read only.")
    element_number = c_property('atom_element_number', uint8, read_only = True,
        doc = "Chemical element number. Read only.")
    in_chain = c_property('atom_in_chain', npy_bool, read_only = True,
        doc = "Whether this atom belongs to a polymer. Read only.")
    is_backbone = c_property('atom_is_backbone', npy_bool,
        doc = "Whether this a protein or nucleic acid backbone atom.")
    name = c_property('atom_name', string,
        doc = "Atom name. Maximum length 4 characters.")
    residue = c_property('atom_residue', cptr, astype = _residue, read_only = True,
        doc = ":class:`Residue` the atom belongs to.")
    structure_category = c_property('atom_structure_category', string, read_only=True,
        doc = "Whether atom is ligand, ion, etc.")

# -----------------------------------------------------------------------------
#
class Bond:
    '''
    Bond connecting two atoms.

    To create a Bond use the :class:`.AtomicStructure` new_bond() method.
    '''
    def __init__(self, bond_pointer):
        set_c_pointer(self, bond_pointer)

    atoms = c_property('bond_atoms', cptr, 2, astype = _atom_pair, read_only = True)
    '''Two-tuple of :py:class:`Atom` objects that are the bond end points.'''
    color = c_property('bond_color', uint8, 4)
    '''Color RGBA length 4 numpy uint8 array.'''
    display = c_property('bond_display', npy_bool)
    '''
    Whether to display the bond if both atoms are shown.
    Can be overriden by the hide attribute.
    '''
    halfbond = c_property('bond_halfbond', npy_bool)
    '''
    Whether to color the each half of the bond nearest an end atom to match that atom
    color, or use a single color and the bond color attribute.  Boolean value.
    '''
    radius = c_property('bond_radius', float32)
    '''Displayed cylinder radius for the bond.'''
    HIDE_RIBBON = 0x1
    '''Hide mask for backbone bonds in ribbon.'''
    hide = c_property('bond_hide', int32)
    '''Whether bond is hidden (overrides display).  Integer bitmask.'''
    shown = c_property('bond_shown', npy_bool, read_only = True)
    '''Whether bond is visible and both atoms are shown and at least one is not Sphere style. Read only.'''
    structure = c_property('bond_structure', cptr, astype = _atomic_structure, read_only = True)
    ''':class:`.AtomicStructure` the bond belongs to.'''
    visible = c_property('bond_visible', npy_bool, read_only = True)
    '''Whether bond is display and not hidden. Read only.'''

    def other_atom(self, atom):
        '''Return the :class:`Atom` at the other end of this bond opposite
        the specified atom.'''
        a1,a2 = self.atoms
        return a2 if atom is a1 else a1

# -----------------------------------------------------------------------------
#
class Pseudobond:
    '''
    A Pseudobond is a graphical line between atoms for example depicting a distance
    or a gap in an amino acid chain, often shown as a dotted or dashed line.
    Pseudobonds can join atoms belonging to different :class:`.AtomicStructure`\\ s
    which is not possible with a :class:`Bond`\\ .

    To create a Pseudobond use the :class:`PseudobondGroup` new_pseudobond() method.
    '''
    def __init__(self, pbond_pointer):
        set_c_pointer(self, pbond_pointer)

    atoms = c_property('pseudobond_atoms', cptr, 2, astype = _atom_pair, read_only = True)
    '''Two-tuple of :py:class:`Atom` objects that are the bond end points.'''
    color = c_property('pseudobond_color', uint8, 4)
    '''Color RGBA length 4 numpy uint8 array.'''
    display = c_property('pseudobond_display', npy_bool)
    '''
    Whether to display the bond if both atoms are shown.
    Can be overriden by the hide attribute.
    '''
    halfbond = c_property('pseudobond_halfbond', npy_bool)
    '''
    Whether to color the each half of the bond nearest an end atom to match that atom
    color, or use a single color and the bond color attribute.  Boolean value.
    '''
    radius = c_property('pseudobond_radius', float32)
    '''Displayed cylinder radius for the bond.'''
    shown = c_property('pseudobond_shown', npy_bool, read_only = True)
    '''Whether bond is visible and both atoms are shown. Read only.'''

    @property
    def length(self):
        '''Distance between centers of two bond end point atoms.'''
        a1, a2 = self.atoms
        v = a1.scene_coord - a2.scene_coord
        from math import sqrt
        return sqrt((v*v).sum())

# -----------------------------------------------------------------------------
#
class PseudobondGroupData:
    '''
    A group of pseudobonds typically used for one purpose such as display
    of distances or missing segments.  The category attribute names the group,
    for example "distances" or "missing segments".

    This base class of :class:`.PseudobondGroup` represents the C++ data while
    the derived class handles rendering the pseudobonds.

    To create a PseudobondGroup use the :class:`PseudobondManager` get_group() method.
    '''

    def __init__(self, pbg_pointer):
        set_c_pointer(self, pbg_pointer)

    category = c_property('pseudobond_group_category', string, read_only = True)
    '''Name of the pseudobond group.  Read only string.'''
    num_pseudobonds = c_property('pseudobond_group_num_pseudobonds', size_t, read_only = True)
    '''Number of pseudobonds in group. Read only.'''
    pseudobonds = c_property('pseudobond_group_pseudobonds', cptr, 'num_pseudobonds',
                             astype = _pseudobonds, read_only = True)
    '''Group pseudobonds as a :class:`.Pseudobonds` collection. Read only.'''

    def new_pseudobond(self, atom1, atom2):
        '''Create a new pseudobond between the specified :class:`Atom` objects.'''
        f = c_function('pseudobond_group_new_pseudobond',
                       args = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p),
                       ret = ctypes.c_void_p)
        pb = f(self._c_pointer, atom1._c_pointer, atom2._c_pointer)
        return object_map(pb, Pseudobond)

    # Graphics changed flags used by rendering code.  Private.
    _gc_color = c_property('pseudobond_group_gc_color', npy_bool)
    _gc_select = c_property('pseudobond_group_gc_select', npy_bool)
    _gc_shape = c_property('pseudobond_group_gc_shape', npy_bool)


# -----------------------------------------------------------------------------
#
class PseudobondManager:
    '''Per-session singleton pseudobond manager keeps track of all
    :class:`.PseudobondGroupData` objects.'''

    def __init__(self, change_tracker):
        f = c_function('pseudobond_create_global_manager', args = (ctypes.c_void_p,),
            ret = ctypes.c_void_p)
        set_c_pointer(self, f(change_tracker._c_pointer))

    def get_group(self, category, create = True):
        '''Get an existing :class:`.PseudobondGroup` or create a new one given a category name.'''
        f = c_function('pseudobond_global_manager_get_group',
                       args = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int),
                       ret = ctypes.c_void_p)
        pbg = f(self._c_pointer, category.encode('utf-8'), create)
        if not pbg:
            return None
        from .pbgroup import PseudobondGroup
        return object_map(pbg, PseudobondGroup)


# -----------------------------------------------------------------------------
#
class Residue:
    '''
    A group of atoms such as an amino acid or nucleic acid. Every atom in
    an :class:`.AtomicStructure` belongs to a residue, including solvent and ions.

    To create a Residue use the :class:`.AtomicStructure` new_residue() method.
    '''

    def __init__(self, residue_pointer):
        set_c_pointer(self, residue_pointer)

    atoms = c_property('residue_atoms', cptr, 'num_atoms', astype = _atoms, read_only = True)
    ''':class:`.Atoms` collection containing all atoms of the residue.'''
    chain_id = c_property('residue_chain_id', string, read_only = True)
    '''Protein Data Bank chain identifier. Limited to 4 characters. Read only string.'''
    is_helix = c_property('residue_is_helix', npy_bool)
    '''Whether this residue belongs to a protein alpha helix. Boolean value.'''
    is_sheet = c_property('residue_is_sheet', npy_bool)
    '''Whether this residue belongs to a protein beta sheet. Boolean value.'''
    ss_id = c_property('residue_ss_id', int32)
    '''Secondary structure id number. Integer value.'''
    ribbon_display = c_property('residue_ribbon_display', npy_bool)
    '''Whether to display the residue as a ribbon/pipe/plank. Boolean value.'''
    ribbon_hide_backbone = c_property('residue_ribbon_hide_backbone', npy_bool)
    '''Whether a ribbon automatically hides the residue backbone atoms. Boolean value.'''
    ribbon_color = c_property('residue_ribbon_color', uint8, 4)
    '''Ribbon color RGBA length 4 numpy uint8 array.'''
    ribbon_style = c_property('residue_ribbon_style', int32)
    '''Whether the residue is displayed as a ribbon or a pipe/plank. Integer value.'''
    RIBBON = 0
    '''Ribbon style = ribbon.'''
    PIPE = 1
    '''Ribbon style = pipe/plank.'''
    ribbon_adjust = c_property('residue_ribbon_adjust', float32)
    '''Smoothness adjustment factor (no adjustment = 0 <= factor <= 1 = idealized).'''
    name = c_property('residue_name', string, read_only = True)
    '''Residue name. Maximum length 4 characters. Read only.'''
    num_atoms = c_property('residue_num_atoms', size_t, read_only = True)
    '''Number of atoms belonging to the residue. Read only.'''
    number = c_property('residue_number', int32, read_only = True)
    '''Integer sequence position number as defined in the input data file. Read only.'''
    str = c_property('residue_str', string, read_only = True)
    '''
    String including residue's name, sequence position, and chain ID in a readable
    form. Read only.
    '''
    structure = c_property('residue_structure', cptr, astype = _atomic_structure, read_only = True)
    ''':class:`.AtomicStructure` that this residue belongs too. Read only.'''

    # TODO: Currently no C++ method to get Chain

    def add_atom(self, atom):
        '''Add the specified :class:`.Atom` to this residue.
        An atom can only belong to one residue, and all atoms
        must belong to a residue.'''
        f = c_function('residue_add_atom', args = (ctypes.c_void_p, ctypes.c_void_p))
        f(self._c_pointer, atom._c_pointer)

# -----------------------------------------------------------------------------
#
class Sequence:
    '''
    A polymeric sequence.  Offers string-like interface.
    '''

    def __init__(self, seq_pointer):
        set_c_pointer(self, seq_pointer)

# -----------------------------------------------------------------------------
#
class Chain(Sequence):
    '''
    A single polymer chain such as a protein, DNA or RNA strand.
    A chain has a sequence associated with it.  A chain may have breaks.
    Chain objects are not always equivalent to Protein Databank chains.

    TODO: C++ sequence object is currently not available in Python.
    '''
    def __init__(self, chain_pointer):
        super().__init__(chain_pointer)

    chain_id = c_property('chain_chain_id', string, read_only = True)
    '''Chain identifier. Limited to 4 characters. Read only string.'''
    structure = c_property('chain_structure', cptr, astype = _atomic_structure, read_only = True)
    ''':class:`.AtomicStructure` that this chain belongs too. Read only.'''
    residues = c_property('chain_residues', cptr, 'num_residues', astype = _residues, read_only = True)
    ''':class:`.Residues` collection containing the residues of this chain in order. Read only.'''
    num_residues = c_property('chain_num_residues', size_t, read_only = True)
    '''Number of residues belonging to this chain. Read only.'''

# -----------------------------------------------------------------------------
#
class AtomicStructureData:
    '''
    This is a base class of :class:`.AtomicStructure`.
    This base class manages the atomic data while the
    derived class handles the graphical 3-dimensional rendering using OpenGL.
    '''
    def __init__(self, mol_pointer=None):
        if mol_pointer is None:
            # Create a new atomic structure
            mol_pointer = c_function('structure_new', args = (ctypes.py_object), ret = ctypes.c_void_p)()
        set_c_pointer(self, mol_pointer)

    def delete(self):
        '''Deletes the C++ data for this atomic structure.'''
        c_function('structure_delete', args = (ctypes.c_void_p,))(self._c_pointer)

    atoms = c_property('structure_atoms', cptr, 'num_atoms', astype = _atoms, read_only = True)
    ''':class:`.Atoms` collection containing all atoms of the structure.'''
    bonds = c_property('structure_bonds', cptr, 'num_bonds', astype = _bonds, read_only = True)
    ''':class:`.Bonds` collection containing all bonds of the structure.'''
    chains = c_property('structure_chains', cptr, 'num_chains', astype = _chains, read_only = True)
    ''':class:`.Chains` collection containing all chains of the structure.'''
    name = c_property('structure_name', string)
    '''Structure name, a string.'''
    num_atoms = c_property('structure_num_atoms', size_t, read_only = True)
    '''Number of atoms in structure. Read only.'''
    num_bonds = c_property('structure_num_bonds', size_t, read_only = True)
    '''Number of bonds in structure. Read only.'''
    num_coord_sets = c_property('structure_num_coord_sets', size_t, read_only = True)
    '''Number of coordinate sets in structure. Read only.'''
    num_chains = c_property('structure_num_chains', size_t, read_only = True)
    '''Number of chains structure. Read only.'''
    num_residues = c_property('structure_num_residues', size_t, read_only = True)
    '''Number of residues structure. Read only.'''
    residues = c_property('structure_residues', cptr, 'num_residues', astype = _residues, read_only = True)
    ''':class:`.Residues` collection containing the residues of this structure. Read only.'''
    pbg_map = c_property('structure_pbg_map', pyobject, astype = _pseudobond_group_map, read_only = True)
    '''Dictionary mapping name to :class:`.PseudobondGroup` for pseudobond groups
    belonging to this structure. Read only.'''
    metadata = c_property('metadata', pyobject, read_only = True)
    '''Dictionary with metadata. Read only.'''
    ribbon_tether_scale = c_property('structure_ribbon_tether_scale', float32)
    '''Ribbon tether thickness scale factor (1.0 = match displayed atom radius, 0=invisible).'''
    ribbon_tether_shape = c_property('structure_ribbon_tether_shape', int32)
    '''Ribbon tether shape. Integer value.'''
    ribbon_show_spine = c_property('structure_ribbon_show_spine', npy_bool)
    '''Display ribbon spine. Boolean.'''
    TETHER_CONE = 0
    TETHER_REVERSE_CONE = 1
    TETHER_CYLINDER = 2
    ribbon_tether_sides = c_property('structure_ribbon_tether_sides', int32)
    '''Number of sides for ribbon tether. Integer value.'''
    ribbon_tether_opacity = c_property('structure_ribbon_tether_opacity', float32)
    '''Ribbon tether opacity scale factor (relative to the atom).'''

    def _copy(self):
        f = c_function('structure_copy', args = (ctypes.c_void_p,), ret = ctypes.c_void_p)
        p = f(self._c_pointer)
        return p
        
    def new_atom(self, atom_name, element_name):
        '''Create a new :class:`.Atom` object. It must be added to a :class:`.Residue` object
        belonging to this structure before being used.'''
        f = c_function('structure_new_atom',
                       args = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p),
                       ret = ctypes.c_void_p)
        ap = f(self._c_pointer, atom_name.encode('utf-8'), element_name.encode('utf-8'))
        return object_map(ap, Atom)

    def new_bond(self, atom1, atom2):
        '''Create a new :class:`.Bond` joining two :class:`Atom` objects.'''
        f = c_function('structure_new_bond',
                       args = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p),
                       ret = ctypes.c_void_p)
        bp = f(self._c_pointer, atom1._c_pointer, atom2._c_pointer)
        return object_map(bp, Bond)

    def new_residue(self, residue_name, chain_id, pos):
        '''Create a new :class:`.Residue`.'''
        f = c_function('structure_new_residue',
                       args = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int),
                       ret = ctypes.c_void_p)
        rp = f(self._c_pointer, residue_name.encode('utf-8'), chain_id.encode('utf-8'), pos)
        return object_map(rp, Residue)

    def polymers(self, consider_missing_structure = True, consider_chains_ids = True):
        '''Return a tuple of :class:`.Residues` objects each containing residues for one polymer.
        Arguments control whether a single polymer can span missing residues or differing chain identifiers.'''
        f = c_function('structure_polymers',
                       args = (ctypes.c_void_p, ctypes.c_int, ctypes.c_int),
                       ret = ctypes.py_object)
        resarrays = f(self._c_pointer, consider_missing_structure, consider_chains_ids)
        from .molarray import Residues
        return tuple(Residues(ra) for ra in resarrays)

    def pseudobond_group(self, name, create_type = "normal"):
        '''Get or create a :class:`.PseudobondGroup` belonging to this structure.'''
        if create_type is None:
            create_arg = 0
        elif create_type == "normal":
            create_arg = 1
        else:  # per-coordset
            create_arg = 2
        f = c_function('structure_pseudobond_group',
                       args = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int),
                       ret = ctypes.c_void_p)
        pbg = f(self._c_pointer, name.encode('utf-8'), create_arg)
        return object_map(pbg, PseudobondGroupData)

    def session_info(self, ints, floats, misc):
        '''Gather session info; return version number'''
        f = c_function('structure_session_info',
                    args = (ctypes.c_void_p, ctypes.py_object, ctypes.py_object,
                        ctypes.py_object),
                    ret = ctypes.c_int)
        return f(self._c_pointer, ints, floats, misc)

    def set_color(self, rgba):
        '''Set color of atoms, bonds, and residues'''
        f = c_function('set_structure_color',
                    args = (ctypes.c_void_p, ctypes.c_void_p))
        return f(self._c_pointer, pointer(rgba))

    def _start_change_tracking(self, change_tracker):
        f = c_function('structure_start_change_tracking',
                args = (ctypes.c_void_p, ctypes.c_void_p))
        f(self._c_pointer, change_tracker._c_pointer)

    # Graphics changed flags used by rendering code.  Private.
    _gc_color = c_property('structure_gc_color', npy_bool)
    _gc_select = c_property('structure_gc_select', npy_bool)
    _gc_shape = c_property('structure_gc_shape', npy_bool)
    _gc_ribbon = c_property('structure_gc_ribbon', npy_bool)

# -----------------------------------------------------------------------------
#
class ChangeTracker:
    '''Per-session singleton change tracker keeps track of all
    atomic data changes'''

    def __init__(self):
        f = c_function('change_tracker_create', args = (), ret = ctypes.c_void_p)
        set_c_pointer(self, f())

    def add_modified(self, modded, reason):
        f = c_function('change_tracker_add_modified',
            args = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_char_p))
        from .molarray import Collection
        if isinstance(modded, Collection):
            class_num = self._class_to_int(modded.object_class)
            for ptr in modded.pointers:
                f(self._c_pointer, class_num, ptr, reason.encode('utf-8'))
        else:
            f(self._c_pointer, self._class_to_int(modded.__class__), modded._c_pointer,
                reason.encode('utf-8'))
    @property
    def changed(self):
        f = c_function('change_tracker_changed', args = (ctypes.c_void_p,), ret = npy_bool)
        return f(self._c_pointer)

    @property
    def changes(self):
        f = c_function('change_tracker_changes', args = (ctypes.c_void_p,),
            ret = ctypes.py_object)
        data = f(self._c_pointer)
        class Changes:
            def __init__(self, created, modified, reasons, total_deleted):
                self.created = created
                self.modified = modified
                self.reasons = reasons
                self.total_deleted = total_deleted
        final_changes = {}
        for k, v in data.items():
            created_ptrs, mod_ptrs, reasons, tot_del = v
            temp_ns = {}
            # can't effectively use locals() as the third argument for some
            # obscure Python 3 reason
            exec("from .molarray import {}s as collection".format(k), globals(), temp_ns)
            collection = temp_ns['collection']
            fc_key = k[:-4] if k.endswith("Data") else k
            final_changes[fc_key] = Changes(collection(created_ptrs),
                collection(mod_ptrs), reasons, tot_del)
        return final_changes

    def clear(self):
        f = c_function('change_tracker_clear', args = (ctypes.c_void_p,))
        f(self._c_pointer)

    def _class_to_int(self, klass):
        # has to tightly coordinate wih change_track_add_modified
        if klass.__name__ == "Atom":
            return 0
        if klass.__name__ == "Bond":
            return 1
        if klass.__name__ == "Pseudobond":
            return 2
        if klass.__name__ == "Residue":
            return 3
        if klass.__name__ == "Chain":
            return 4
        if klass.__name__ == "AtomicStructure":
            return 5
        if klass.__name__ == "PseudobondGroup":
            return 6
        raise AssertionError("Unknown class for change tracking")

# -----------------------------------------------------------------------------
#
class Element:
    '''A chemical element having a name, number, mass, and other physical properties.'''
    def __init__(self, element_pointer):
        set_c_pointer(self, element_pointer)

    name = c_property('element_name', string, read_only = True)
    '''Element name, for example C for carbon. Read only.'''
    number = c_property('element_number', uint8, read_only = True)
    '''Element atomic number, for example 6 for carbon. Read only.'''
    mass = c_property('element_mass', float32, read_only = True)
    '''Element atomic mass,
    taken from http://en.wikipedia.org/wiki/List_of_elements_by_atomic_weight.
    Read only.'''
    is_alkali_metal = c_property('element_is_alkali_metal', npy_bool, read_only = True)
    '''Is atom an alkali metal. Read only.'''
    is_halogen = c_property('element_is_halogen', npy_bool, read_only = True)
    '''Is atom a halogen. Read only.'''
    is_metal = c_property('element_is_metal', npy_bool, read_only = True)
    '''Is atom a metal. Read only.'''
    is_noble_gas = c_property('element_is_noble_gas', npy_bool, read_only = True)
    '''Is atom a noble_gas. Read only.'''
    valence = c_property('element_valence', uint8, read_only = True)
    '''Element valence number, for example 7 for chlorine. Read only.'''

    def get_element(name_or_number):
        '''Get the Element that corresponds to an atomic name or number'''
        if type(name_or_number) == type(1):
            f = c_function('element_number_get_element', args = (ctypes.c_int,), ret = ctypes.c_void_p)
        elif type(name_or_number) == type(""):
            f = c_function('element_name_get_element', args = (ctypes.c_char_p,), ret = ctypes.c_void_p)
        else:
            raise ValueError("'get_element' arg must be string or int")
        return _element(f(name_or_number))

# -----------------------------------------------------------------------------
#
_object_map = {}	# Map C++ pointer to Python object
def object_map(p, object_type):
    global _object_map
    o = _object_map.get(p, None)
    if o is None:
        _object_map[p] = o = object_type(p)
    return o

def add_to_object_map(object):
    _object_map[object._c_pointer.value] = object

def register_object_map_deletion_handler(omap):
    # When a C++ object such as an Atom is deleted the pointer is removed
    # from the object map if it exists and the Python object has its _c_pointer
    # attribute deleted.
    f = c_function('object_map_deletion_handler', args = [ctypes.c_void_p], ret = ctypes.c_void_p)
    p = ctypes.c_void_p(id(omap))
    global _omd_handler
    _omd_handler = Object_Map_Deletion_Handler(f(p))

_omd_handler = None
class Object_Map_Deletion_Handler:
    def __init__(self, h):
        self.h = h
        self.delete_handler = c_function('delete_object_map_deletion_handler', args = [ctypes.c_void_p])
    def __del__(self):
        # Make sure object map deletion handler is removed before Python exits
        # so later C++ deletes don't cause segfault on exit.
        self.delete_handler(self.h)

register_object_map_deletion_handler(_object_map)
