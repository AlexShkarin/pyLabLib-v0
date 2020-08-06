import pytest

import numpy as np




##### Basic import tests #####

def test_imports():
    """Test general non-failing of imports"""
    import pylablib.core.utils.ctypes_wrap
    import pylablib.core.utils.dictionary
    import pylablib.core.utils.files
    import pylablib.core.utils.funcargparse
    import pylablib.core.utils.functions
    import pylablib.core.utils.general
    import pylablib.core.utils.ipc
    import pylablib.core.utils.iterator
    import pylablib.core.utils.library_parameters
    import pylablib.core.utils.log
    import pylablib.core.utils.module
    import pylablib.core.utils.net
    import pylablib.core.utils.numclass
    import pylablib.core.utils.numerical
    import pylablib.core.utils.observer_pool
    import pylablib.core.utils.plotting
    import pylablib.core.utils.pstorage
    import pylablib.core.utils.py3
    import pylablib.core.utils.rpyc
    import pylablib.core.utils.serializable
    import pylablib.core.utils.strdump
    import pylablib.core.utils.string
    import pylablib.core.utils.strpack
    import pylablib.core.utils.thread
    import pylablib.core.utils.versioning




##### String tests #####

from pylablib.core.utils import string

def test_string():
    """Test to/from string conversion consistency"""
    # scalars
    for v in [True,False,None,0,1,2,1.5,1+2j,"abc"]:
        assert string.from_string(string.to_string(v))==v
    # lists/arrays
    assert string.to_string([1,2,3])=="[1, 2, 3]"
    assert string.from_string("[1, 2, '3']")==[1,2,"3"]
    assert string.to_string(np.arange(3))=="[0, 1, 2]"
    assert string.to_string(np.arange(3),use_classes=True)=="array([0, 1, 2])"
    assert string.from_string("[1,2,3+4j,(3+4j),[5,6,(7,8)],{'a':9,'b':10}]")==[1,2,3+4j,(3+4j,),[5,6,(7,8)],{'a':9,'b':10}]
    assert string.from_string("[1,2,(3+4j),(3+4j,),[5,6,(7,8)],{'a':9,'b':10}]",parenthesis_rules="python")==[1,2,3+4j,(3+4j,),[5,6,(7,8)],{'a':9,'b':10}]
    varlst=[1, 2, 3, "abc", "[ 3, 4, '5']", "[6, 7]", (), (1,2, [3,4]), {"x":5, "y":10, "z":[15, (20,30)]},
        None, True, False, 3.5, 1+2j, "", "1+2j", "(1+2j)", ("1+2j",), (1,), (1j,), (1+2j,), (("1+2j",),)]
    assert string.from_string(string.to_string(varlst))==varlst
    nplst=[np.arange(3), [0,1,2]]
    assert string.from_string(string.to_string(nplst,use_classes=False))==[nplst[1],nplst[1]]
    assert isinstance(string.from_string(string.to_string(nplst,use_classes=True))[0],np.ndarray)
    assert np.all(string.from_string(string.to_string(nplst,use_classes=True))[0]==nplst[0])
    # tuples
    assert string.to_string((1,2,3))=="(1, 2, 3)"
    assert string.from_string("(1, 2, '3')")==(1,2,"3")
    assert string.from_string("(1,2,3+4j,(3+4j),[5,6,(7,8)],{'a':9,'b':10})")==(1,2,3+4j,(3+4j,),[5,6,(7,8)],{'a':9,'b':10})
    assert string.from_string("(1,2,(3+4j),(3+4j,),[5,6,(7,8)],{'a':9,'b':10})",parenthesis_rules="python")==(1,2,3+4j,(3+4j,),[5,6,(7,8)],{'a':9,'b':10})
    assert string.from_string(string.to_string(tuple(varlst)))==tuple(varlst)