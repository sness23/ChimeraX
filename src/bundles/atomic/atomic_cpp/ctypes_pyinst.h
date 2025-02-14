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

#ifndef atomic_ctypes_pyinst
#define atomic_ctypes_pyinst

#define GET_PYTHON_INSTANCES(FNAME, CLASSNAME) \
extern "C" EXPORT \
PyObject* FNAME##_py_inst(void* ptr) \
{ \
   CLASSNAME *p = static_cast<CLASSNAME *>(ptr); \
   try { \
       return p->py_instance(true); \
   } catch (...) { \
       molc_error(); \
       return nullptr; \
   } \
} \
\
extern "C" EXPORT \
PyObject* FNAME##_existing_py_inst(void* ptr) \
{ \
   CLASSNAME *p = static_cast<CLASSNAME *>(ptr); \
   try { \
       return p->py_instance(false); \
   } catch (...) { \
       molc_error(); \
       return nullptr; \
   } \
}

#define SET_PYTHON_INSTANCE(FNAME, CLASSNAME) \
extern "C" EXPORT \
void set_##FNAME##_py_instance(void* FNAME, PyObject* py_inst) \
{ \
   CLASSNAME *p = static_cast<CLASSNAME *>(FNAME); \
   try { \
       p->set_py_instance(py_inst); \
   } catch (...) { \
       molc_error(); \
   } \
} \

#define SET_PYTHON_CLASS(FNAME, CLASSNAME) \
extern "C" EXPORT void set_##FNAME##_pyclass(PyObject* py_class) \
{ \
   try { \
       CLASSNAME::set_py_class(py_class); \
   } catch (...) { \
       molc_error(); \
   } \
} \

#endif  // atomic_ctypes_pyinst
