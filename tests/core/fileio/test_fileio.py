import pytest

import numpy as np
import pandas as pd
import os




##### Basic import tests #####

def test_imports():
    """Test general non-failing of imports"""
    import pylablib.core.fileio.binio
    import pylablib.core.fileio.datafile
    import pylablib.core.fileio.dict_entry
    import pylablib.core.fileio.loadfile
    import pylablib.core.fileio.location
    import pylablib.core.fileio.logfile
    import pylablib.core.fileio.parse_csv
    import pylablib.core.fileio.savefile




##### Table saving tests #####

import pylablib as pll
from pylablib.core.fileio import loadfile, savefile
from pylablib.core.datatable.table import DataTable

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
    _builder.kind=kind
    return _builder

def compare_tables(t1, t2):
    """Compare two tables (type, shape, content, etc.)"""
    assert type(t1)==type(t2)
    assert isinstance(t1,(np.ndarray,DataTable,pd.DataFrame))
    assert np.shape(t1)==np.shape(t2)
    if isinstance(t1,DataTable):
        assert all([np.all(t1.c[i]==t2.c[i]) for i in range(np.shape(t1)[1])])
    else:
        assert np.all(t1==t2)
    if isinstance(t1,DataTable):
        assert t1.get_column_names()==t2.get_column_names()
    if isinstance(t1,pd.DataFrame):
        assert np.all(t1.columns==t2.columns)
def test_tables_saving(table_builder, tmpdir):
    """Test saving/loading consistency"""
    save_path=os.path.join(tmpdir,"table.dat")
    kind=table_builder.kind

    data=np.column_stack((np.arange(10),np.zeros(10)))
    columns=["X","Y"]
    table=table_builder(data,columns)
    save_path=os.path.join(tmpdir,"table.dat")
    savefile.save(table,save_path,"bin")
    new_table=loadfile.load(save_path,"bin",columns=columns,out_type=kind)
    compare_tables(table,new_table)
    if kind==pll.par["fileio/loadfile/csv/out_type"]:
        new_table=loadfile.load(save_path,"bin",columns=columns)
        compare_tables(table,new_table)
    if kind=="array":
        new_table=loadfile.load(save_path,"bin",columns=2,out_type="array")
        compare_tables(table,new_table)
        new_table=loadfile.load(save_path,"bin",out_type="array").reshape((-1,2))
        compare_tables(table,new_table)

    data=np.column_stack((np.arange(10),np.zeros(10),np.arange(10)**2+1j))
    columns=["X","Y","Z"]
    table=table_builder(data,columns)
    savefile.save(table,save_path)
    new_table=loadfile.load(save_path,"csv",out_type=kind)
    compare_tables(table,new_table)
    if kind==pll.par["fileio/loadfile/csv/out_type"]:
        new_table=loadfile.load(save_path,"csv")
        compare_tables(table,new_table)

    if kind in ["table","pandas"]:
        data=list(zip(np.arange(10),["t{}".format(i) for i in np.arange(10)]))
        columns=["X","tX"]
        table=table_builder(data,columns)
        savefile.save(table,save_path)
        new_table=loadfile.load(save_path,"csv",dtype="generic",out_type=table_builder.kind)
        compare_tables(table,new_table)