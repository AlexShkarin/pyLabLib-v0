import pytest

import numpy as np
import pandas as pd




##### Basic import tests #####

def test_imports():
    """Test general non-failing of imports"""
    import pylablib.core.datatable.column
    import pylablib.core.datatable.datatable_utils
    import pylablib.core.datatable.indexing
    import pylablib.core.datatable.table_storage
    import pylablib.core.datatable.table
    import pylablib.core.datatable.wrapping



##### Wrapping methods #####

from pylablib.core.datatable.table import DataTable
from pylablib.core.datatable.wrapping import wrap

@pytest.fixture(params=["array","table","pandas"])
def table_builder(request):
    """Function which returns a table of a given kind (numpy array, datatable, or pandas table) from data and column names"""
    kind=request.param
    def _builder(data, columns):
        if kind=="array":
            return np.array(data)
        elif kind=="table":
            return DataTable(data,columns,transposed=False)
        else:
            return pd.DataFrame(data,columns=columns)
    return _builder

def compare_tables(t1, t2):
    """Compare two tables (type, shape, content, etc.)"""
    assert type(t1)==type(t2)
    assert isinstance(t1,(np.ndarray,DataTable,pd.DataFrame))
    assert np.shape(t1)==np.shape(t2)
    if isinstance(t1,DataTable):
        assert all([np.all(t1.c[i]==t2.c[i]) for i in range(t1.ncols())])
    else:
        assert np.all(t1==t2)
    if isinstance(t1,DataTable):
        assert t1.get_column_names()==t2.get_column_names()
    if isinstance(t1,pd.DataFrame):
        assert np.all(t1.columns==t2.columns)
def test_wrapping(table_builder):
    """Test wrapping methods"""
    data=np.column_stack((np.arange(10),np.zeros(10),np.arange(10)**2+1j))
    columns=["X","Y","Z"]
    table=table_builder(data,columns)
    wrapped=wrap(table)
    compare_tables(wrapped[:],data)
    compare_tables(wrapped[:,:],data)
    new_table=wrapped.array_replaced(data.copy(),wrapped=False)
    compare_tables(table,new_table)
    data_columns=list(data.T)
    new_table=wrapped.columns_replaced(data_columns,wrapped=False)
    compare_tables(table,new_table)
    compare_tables(wrapped.copy().cont,table)
    compare_tables(np.asarray(wrapped.r[1]),data[1,:])
    compare_tables(np.asarray(wrapped.c[1]),data[:,1])
    compare_tables(wrapped.t[:,:],table)