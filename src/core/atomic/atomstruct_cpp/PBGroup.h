// vi: set expandtab ts=4 sw=4:

/*
 * === UCSF ChimeraX Copyright ===
 * Copyright 2016 Regents of the University of California.
 * All rights reserved.  This software provided pursuant to a
 * license agreement containing restrictions on its disclosure,
 * duplication and use.  For details see:
 * http://www.rbvi.ucsf.edu/chimerax/docs/licensing.html
 * This notice must be embedded in or attached to all copies,
 * including partial copies, of the software or any revisions
 * or derivations thereof.
 * === UCSF ChimeraX Copyright ===
 */

#ifndef atomstruct_PBGroup
#define atomstruct_PBGroup

#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include "imex.h"
#include "destruct.h"
#include "PBManager.h"
#include "Rgba.h"

// "forward declare" PyObject, which is a typedef of a struct,
// as per the python mailing list:
// http://mail.python.org/pipermail/python-dev/2003-August/037601.html
#ifndef PyObject_HEAD
struct _object;
typedef _object PyObject;
#endif
    
namespace atomstruct {

class Atom;
class CoordSet;
class Pseudobond;
class Proxy_PBGroup;
class Structure;

class ATOMSTRUCT_IMEX PBGroup: public DestructionObserver, public GraphicsContainer {
public:
    typedef std::set<Pseudobond*>  Pseudobonds;

    static int  SESSION_NUM_INTS(int /*version*/=CURRENT_SESSION_VERSION) { return 1; }
    static int  SESSION_NUM_FLOATS(int /*version*/=CURRENT_SESSION_VERSION) { return 0; }
protected:
    std::string  _category;
    Rgba  _default_color = {255,255,0,255}; // yellow
    bool  _default_halfbond = false;
    bool  _destruction_relevant;
    BaseManager*  _manager;
    friend class Proxy_PBGroup;
    Proxy_PBGroup* _proxy; // the proxy for this group

    // the manager will need to be declared as a friend...
    PBGroup(const std::string& cat, BaseManager* manager):
        _category(cat), _destruction_relevant(true), _manager(manager), _proxy(nullptr) { }
    virtual  ~PBGroup() {}

    // can't call pure virtuals from base class destructors, so
    // make the code easily available to derived classes...
    void  dtor_code();

    void _check_destroyed_atoms(PBGroup::Pseudobonds& pbonds, const std::set<void*>& destroyed);
    void delete_pbs_check(const std::set<Pseudobond*>& pbs) const;
public:
    virtual void  clear() = 0;
    virtual const std::string&  category() const { return _category; }
    virtual void  check_destroyed_atoms(const std::set<void*>& destroyed) = 0;
    virtual void  delete_pseudobond(Pseudobond* pb) = 0;
    virtual void  delete_pseudobonds(const std::set<Pseudobond*>& pbs) = 0;
    virtual void  destructors_done(const std::set<void*>& destroyed) {
        if (!_destruction_relevant)
            return;
        check_destroyed_atoms(destroyed);
    }
    virtual const Rgba&  get_default_color() const { return _default_color; }
    virtual bool  get_default_halfbond() const { return _default_halfbond; }
    BaseManager*  manager() const { return _manager; }
    virtual Pseudobond*  new_pseudobond(Atom* e1, Atom* e2) = 0;
    Proxy_PBGroup*  proxy() const { return _proxy; }
    virtual const Pseudobonds&  pseudobonds() const = 0;
    // version "0" means latest version
    static int  session_num_floats(int version=0) {
        return SESSION_NUM_FLOATS(version) + Rgba::session_num_floats();
    }
    static int  session_num_ints(int version=0) {
        return SESSION_NUM_INTS(version) + Rgba::session_num_ints();
    }
    virtual void  session_restore(int version, int**, float**);
    virtual void  session_save(int**, float**) const;
    virtual void  set_default_color(const Rgba& rgba) { _default_color = rgba; }
    virtual void  set_default_color(Rgba::Channel r, Rgba::Channel g, Rgba::Channel b,
        Rgba::Channel a = 255) { this->set_default_color(Rgba(r,g,b,a)); }
    virtual void  set_default_halfbond(bool hb) { _default_halfbond = hb; }
};

// in per-AtomicStructure groups there are per-CoordSet groups
// and overall groups...
class ATOMSTRUCT_IMEX StructurePBGroupBase: public PBGroup {
public:
    static int  SESSION_NUM_INTS(int /*version*/=0) { return 0; }
    static int  SESSION_NUM_FLOATS(int /*version*/=0) { return 0; }
protected:
    friend class AS_PBManager;
    void  _check_structure(Atom* a1, Atom* a2);
    Structure*  _structure;
    StructurePBGroupBase(const std::string& cat, Structure* as, BaseManager* manager):
        PBGroup(cat, manager), _structure(as) {}
    virtual  ~StructurePBGroupBase() {}
public:
    virtual Pseudobond*  new_pseudobond(Atom* e1, Atom* e2) = 0;
    std::pair<Atom*, Atom*> session_get_pb_ctor_info(int** ints) const;
    void  session_note_pb_ctor_info(Pseudobond* pb, int** ints) const;
    static int  session_num_floats(int version=0) {
        return SESSION_NUM_FLOATS(version) + PBGroup::session_num_floats();
    }
    static int  session_num_ints(int version=0) {
        return SESSION_NUM_INTS(version) + PBGroup::session_num_ints();
    }
    virtual void  session_restore(int version, int** ints, float** floats) {
        PBGroup::session_restore(version, ints, floats);
    }
    virtual void  session_save(int** ints, float** floats) const {
        PBGroup::session_save(ints, floats);
    }
    Structure*  structure() const { return _structure; }
};

class ATOMSTRUCT_IMEX StructurePBGroup: public StructurePBGroupBase {
public:
    static int  SESSION_NUM_INTS(int /*version*/=0) { return 1; }
    static int  SESSION_NUM_FLOATS(int /*version*/=0) { return 0; }
private:
    friend class Proxy_PBGroup;
    Pseudobonds  _pbonds;
protected:
    StructurePBGroup(const std::string& cat, Structure* as, BaseManager* manager):
        StructurePBGroupBase(cat, as, manager) {}
    ~StructurePBGroup() { dtor_code(); }
public:
    void  check_destroyed_atoms(const std::set<void*>& destroyed);
    void  clear();
    void  delete_pseudobond(Pseudobond* pb);
    void  delete_pseudobonds(const std::set<Pseudobond*>& pbs);
    void  delete_pseudobonds(const std::vector<Pseudobond*>& pbs) {
        delete_pseudobonds(std::set<Pseudobond*>(pbs.begin(), pbs.end()));
    }
    Pseudobond*  new_pseudobond(Atom* a1, Atom* a2);
    const Pseudobonds&  pseudobonds() const { return _pbonds; }
    int  session_num_ints(int version=0) const;
    int  session_num_floats(int version=0) const;
    void  session_restore(int version, int** , float**);
    void  session_save(int** , float**) const;
    mutable std::unordered_map<const Pseudobond*, size_t>  *session_save_pbs;
};

class ATOMSTRUCT_IMEX CS_PBGroup: public StructurePBGroupBase
{
public:
    static int  SESSION_NUM_INTS(int /*version*/=0) { return 1; }
    static int  SESSION_NUM_FLOATS(int /*version*/=0) { return 0; }
private:
    friend class Proxy_PBGroup;
    mutable std::unordered_map<const CoordSet*, Pseudobonds>  _pbonds;
    void  remove_cs(const CoordSet* cs);
protected:
    CS_PBGroup(const std::string& cat, Structure* as, BaseManager* manager):
        StructurePBGroupBase(cat, as, manager) {}
    ~CS_PBGroup();
public:
    void  check_destroyed_atoms(const std::set<void*>& destroyed);
    void  clear();
    void  delete_pseudobond(Pseudobond* pb);
    void  delete_pseudobonds(const std::set<Pseudobond*>& pbs);
    void  delete_pseudobonds(const std::vector<Pseudobond*>& pbs) {
        delete_pseudobonds(std::set<Pseudobond*>(pbs.begin(), pbs.end()));
    }
    Pseudobond*  new_pseudobond(Atom* a1, Atom* a2);
    Pseudobond*  new_pseudobond(Atom* a1, Atom* a2, CoordSet* cs);
    const Pseudobonds&  pseudobonds() const;
    const Pseudobonds&  pseudobonds(const CoordSet* cs) const { return _pbonds[cs]; }
    int  session_num_ints(int version=0) const;
    int  session_num_floats(int version=0) const;
    void  session_restore(int, int** , float**);
    void  session_save(int** , float**) const;
    mutable std::unordered_map<const Pseudobond*, size_t>  *session_save_pbs;
};

// Need a proxy class that can be contained/returned by the pseudobond
// manager and that will dispatch calls to the appropriate contained class
class ATOMSTRUCT_IMEX Proxy_PBGroup: public StructurePBGroupBase
{
private:
    friend class AS_PBManager;
    friend class StructureManager;
    friend class BaseManager;
    friend class PBManager;
    int  _group_type;
    void*  _proxied;

    Proxy_PBGroup(BaseManager* manager, const std::string& cat):
        StructurePBGroupBase(cat, nullptr, manager) { init(AS_PBManager::GRP_NORMAL); }
    Proxy_PBGroup(BaseManager* manager, const std::string& cat, Structure* as):
        StructurePBGroupBase(cat, as, manager) { init(AS_PBManager::GRP_NORMAL); }
    Proxy_PBGroup(BaseManager* manager, const std::string& cat, Structure* as, int grp_type):
        StructurePBGroupBase(cat, as, manager) { init(grp_type); }
    ~Proxy_PBGroup() {
        _destruction_relevant = false;
        auto du = DestructionUser(this);
        manager()->change_tracker()->add_deleted(this);
        if (_group_type == AS_PBManager::GRP_NORMAL)
            delete static_cast<StructurePBGroup*>(_proxied);
        else
            delete static_cast<CS_PBGroup*>(_proxied);
    }
    void  init(int grp_type) {
        _group_type = grp_type;
        if (grp_type == AS_PBManager::GRP_NORMAL)
            _proxied = new StructurePBGroup(_category, _structure, _manager);
        else
            _proxied = new CS_PBGroup(_category, _structure, _manager);
        _proxy = this;
        static_cast<PBGroup*>(_proxied)->_proxy = this;
    }
    void  remove_cs(const CoordSet* cs) {
        if (_group_type == AS_PBManager::GRP_PER_CS)
            static_cast<CS_PBGroup*>(_proxied)->remove_cs(cs);
    }

public:
    const std::string&  category() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->category();
        return static_cast<CS_PBGroup*>(_proxied)->category();
    }
    void  check_destroyed_atoms(const std::set<void*>& destroyed) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->check_destroyed_atoms(destroyed);
        static_cast<CS_PBGroup*>(_proxied)->check_destroyed_atoms(destroyed);
    }
    void  clear() {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->clear();
        static_cast<CS_PBGroup*>(_proxied)->clear();
    }
    void  delete_pseudobond(Pseudobond* pb) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->delete_pseudobond(pb);
        return static_cast<CS_PBGroup*>(_proxied)->delete_pseudobond(pb);
    }
    void  delete_pseudobonds(const std::set<Pseudobond*>& pbs) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->delete_pseudobonds(pbs);
        return static_cast<CS_PBGroup*>(_proxied)->delete_pseudobonds(pbs);
    }
    void  delete_pseudobonds(const std::vector<Pseudobond*>& pbs) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->delete_pseudobonds(pbs);
        return static_cast<CS_PBGroup*>(_proxied)->delete_pseudobonds(pbs);
    }
    void  destroy() {
        if (structure() == nullptr)
            static_cast<PBManager*>(_manager)->delete_group(this);
        else
            static_cast<AS_PBManager*>(_manager)->delete_group(this);
    }
    const Rgba&  get_default_color() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->get_default_color();
        return static_cast<CS_PBGroup*>(_proxied)->get_default_color();
    }
    bool  get_default_halfbond() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->get_default_halfbond();
        return static_cast<CS_PBGroup*>(_proxied)->get_default_halfbond();
    }
    int  group_type() const { return _group_type; }
    Pseudobond*  new_pseudobond(Atom* a1, Atom* a2) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->new_pseudobond(a1, a2);
        return static_cast<CS_PBGroup*>(_proxied)->new_pseudobond(a1, a2);
    }
    Pseudobond*  new_pseudobond(Atom* const ends[2]) {
        // should be in base class, but C++ won't look in base
        // classes for overloads!
        return new_pseudobond(ends[0], ends[1]);
    }
    Pseudobond*  new_pseudobond(Atom* a1, Atom* a2, CoordSet* cs) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            throw std::invalid_argument("Not a per-coordset pseudobond group");
        return static_cast<CS_PBGroup*>(_proxied)->new_pseudobond(a1, a2, cs);
    }
    Pseudobond*  new_pseudobond(Atom* const ends[2], CoordSet* cs) {
        return new_pseudobond(ends[0], ends[1], cs);
    }
    const Pseudobonds&  pseudobonds() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->pseudobonds();
        return static_cast<CS_PBGroup*>(_proxied)->pseudobonds();
    }
    const Pseudobonds&  pseudobonds(const CoordSet* cs) const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            throw std::invalid_argument("Not a per-coordset pseudobond group");
        return static_cast<CS_PBGroup*>(_proxied)->pseudobonds(cs);
    }
    int  session_num_ints() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->session_num_ints();
        return static_cast<CS_PBGroup*>(_proxied)->session_num_ints();
    }
    int  session_num_floats() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->session_num_floats();
        return static_cast<CS_PBGroup*>(_proxied)->session_num_floats();
    }
    void  session_restore(int version, int** ints, float** floats) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->session_restore(version, ints, floats);
        return static_cast<CS_PBGroup*>(_proxied)->session_restore(version, ints, floats);
    }
    void  session_save(int** ints, float** floats) const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->session_save(ints, floats);
        return static_cast<CS_PBGroup*>(_proxied)->session_save(ints, floats);
    }
    void  set_default_color(const Rgba& rgba) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->set_default_color(rgba);
	else
	    static_cast<CS_PBGroup*>(_proxied)->set_default_color(rgba);
    }
    void  set_default_color(Rgba::Channel r, Rgba::Channel g, Rgba::Channel b,
        Rgba::Channel a = 255) { set_default_color(Rgba(r,g,b,a)); }
    void  set_default_halfbond(bool hb) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->set_default_halfbond(hb);
	else
	    static_cast<CS_PBGroup*>(_proxied)->set_default_halfbond(hb);
    }
    Structure*  structure() const { 
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->structure();
        return static_cast<CS_PBGroup*>(_proxied)->structure();
    }

    void  gc_clear() {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->gc_clear();
	else
	    static_cast<CS_PBGroup*>(_proxied)->gc_clear();
    }
    bool  get_gc_color() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->get_gc_color();
        return static_cast<CS_PBGroup*>(_proxied)->get_gc_color();
    }
    bool  get_gc_select() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->get_gc_select();
        return static_cast<CS_PBGroup*>(_proxied)->get_gc_select();
    }
    bool  get_gc_shape() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->get_gc_shape();
        return static_cast<CS_PBGroup*>(_proxied)->get_gc_shape();
    }
    bool  get_gc_ribbon() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->get_gc_ribbon();
        return static_cast<CS_PBGroup*>(_proxied)->get_gc_ribbon();
    }
    int   get_graphics_changes() const {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            return static_cast<StructurePBGroup*>(_proxied)->get_graphics_changes();
        return static_cast<CS_PBGroup*>(_proxied)->get_graphics_changes();
    }
    void  set_gc_color() {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->set_gc_color();
	else
	    static_cast<CS_PBGroup*>(_proxied)->set_gc_color();
    }
    void  set_gc_select() {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->set_gc_select();
	else
	    static_cast<CS_PBGroup*>(_proxied)->set_gc_select();
    }
    void  set_gc_shape() {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->set_gc_shape();
	else
	    static_cast<CS_PBGroup*>(_proxied)->set_gc_shape();
    }
    void  set_gc_ribbon() {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->set_gc_ribbon();
	else
	    static_cast<CS_PBGroup*>(_proxied)->set_gc_ribbon();
    }
    void  set_graphics_changes(int change) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->set_graphics_changes(change);
	else
	    static_cast<CS_PBGroup*>(_proxied)->set_graphics_changes(change);
    }
    void  set_graphics_change(ChangeType type) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->set_graphics_change(type);
	else
	    static_cast<CS_PBGroup*>(_proxied)->set_graphics_change(type);
    }
    void  clear_graphics_change(ChangeType type) {
        if (_group_type == AS_PBManager::GRP_NORMAL)
            static_cast<StructurePBGroup*>(_proxied)->clear_graphics_change(type);
	else
	    static_cast<CS_PBGroup*>(_proxied)->clear_graphics_change(type);
    }
};

}  // namespace atomstruct

#endif  // atomstruct_PBGroup
