# Clone or copy a model.
def sym(session, molecules, assembly = None, clear = False, surface_only = False):
    for m in molecules:
        assem = pdb_assemblies(m)
        if clear:
            from .geometry import Place
            m.position = Place()
            for s in m.surfaces():
                s.position = Place()
        elif assembly is None:
            ainfo = '\n'.join(' %s = %s (%d copies)' % (a.id,a.description,len(a.operators)) for a in assem)
            anames = ainfo if assem else "no assemblies"
            session.logger.info('Assemblies for %s:\n%s' % (m.name, anames))
        else:
            amap = dict((a.id, a) for a in assem)
            if not assembly in amap:
                from .errors import UserError
                raise UserError('Assembly "%s" not found, have %s'
                                % (assembly, ', '.join(a.id for a in assem)))
            a = amap[assembly]
            if surface_only:
                surfs = m.surfaces()
                if len(surfs) == 0:
                    from .molsurf import surface_command
                    surfs = surface_command(session, m.atoms)
                for s in surfs:
                    s.positions = a.operators
            else:
                m.positions = a.operators

def register_sym_command():
    from .structure import AtomicStructuresArg
    from . import cli
    _sym_desc = cli.CmdDesc(
        required = [('molecules', AtomicStructuresArg)],
        keyword = [('assembly', cli.StringArg),
                   ('clear', cli.NoArg),
                   ('surface_only', cli.NoArg)],
        synopsis = 'create model copies')
    cli.register('sym', _sym_desc, sym)

def pdb_assemblies(m):
    if not hasattr(m, 'filename') or not m.filename.endswith('.cif'):
        return []
    if hasattr(m, 'assemblies'):
        return m.assemblies
    table_names = ('_pdbx_struct_assembly',
                   '_pdbx_struct_assembly_gen',
                   '_pdbx_struct_oper_list')
    from . import mmcif
    assem, assem_gen, oper = mmcif.read_mmcif_tables(m.filename, table_names)
    op_expr = assem_gen.mapping('assembly_id', 'oper_expression')
    chain_ids = assem_gen.mapping('assembly_id', 'asym_id_list')
    name = assem.mapping('id', 'details')
    ids = list(name.keys())
    ids.sort()

    ops = {}
    mat = oper.fields(('id',
                       'matrix[1][1]', 'matrix[1][2]', 'matrix[1][3]', 'vector[1]',
                       'matrix[2][1]', 'matrix[2][2]', 'matrix[2][3]', 'vector[2]',
                       'matrix[3][1]', 'matrix[3][2]', 'matrix[3][3]', 'vector[3]'))
    from .geometry import Place
    for id, m11,m12,m13,m14,m21,m22,m23,m24,m31,m32,m33,m34 in mat:
        ops[id] = Place(matrix = ((m11,m12,m13,m14),(m21,m22,m23,m24),(m31,m32,m33,m34)))

    alist = [Assembly(id, name[id], op_expr[id], chain_ids[id], ops) for id in ids]
    m.assemblies = alist
    return alist

class Assembly:
    def __init__(self, id, description, operator_expr, chain_ids, operator_table):
        self.id = id
        self.description = description
        self.operator_expr = operator_expr
        self.chain_ids = chain_ids
        self.operator_table = operator_table
        products = parse_operator_expression(operator_expr)
        self.operators = operator_products(products, operator_table)

def operator_products(products, oper_table):
    from .geometry import Places
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
