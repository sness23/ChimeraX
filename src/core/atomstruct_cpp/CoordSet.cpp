// vi: set expandtab ts=4 sw=4:

#include <utility>  // for pair

#include "Atom.h"
#include "AtomicStructure.h"
#include "CoordSet.h"
#include <basegeom/destruct.h>

namespace atomstruct {

CoordSet::CoordSet(AtomicStructure* as, int cs_id):
    _cs_id(cs_id), _structure(as)
{
}

CoordSet::CoordSet(AtomicStructure* as, int cs_id, int size):
    _cs_id(cs_id), _structure(as)
{
    _coords.reserve(size);
}

CoordSet::~CoordSet()
{
    if (basegeom::DestructionCoordinator::destruction_parent() != _structure)
        _structure->pb_mgr().remove_cs(this);
}

float
CoordSet::get_bfactor(const Atom *a) const
{
    std::unordered_map<const Atom *, float>::const_iterator bfi = _bfactor_map.find(a);
    if (bfi == _bfactor_map.end())
        return 0.0;
    return (*bfi).second;
}

float
CoordSet::get_occupancy(const Atom *a) const
{
    std::unordered_map<const Atom *, float>::const_iterator bfi = _occupancy_map.find(a);
    if (bfi == _occupancy_map.end())
        return 1.0;
    return (*bfi).second;
}

void
CoordSet::set_bfactor(const Atom *a, float val)
{
    _bfactor_map.insert(std::pair<const Atom *, float>(a, val));
}

void
CoordSet::set_occupancy(const Atom *a, float val)
{
    _occupancy_map.insert(std::pair<const Atom *, float>(a, val));
}

}  // namespace atomstruct
