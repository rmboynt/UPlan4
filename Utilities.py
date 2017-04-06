'''
Created on Feb 9, 2015

@author: roth
'''
import os
import datetime
import numpy as np
import numpy.lib.recfunctions as rfn
import arcpy
import pandas as pd


def Logger(msg):
    print("| ".join([str(datetime.datetime.now()), msg]))
    
def DropNumpyField(array,fieldName):
    '''
    Return an array with the designated fielded removed
    
    Arguments: 
    array: input array
    fieldname: name of field to be dropped
    '''
    names = list(array.dtype.names)
    if fieldName in names:
        names.remove(fieldName)
    return array[names].copy()

def AddNumpyField(array, descr):
    ''' 
    Return a new structured array that is a copy of "array" but with the new field(s). The new fields are left uninitialized.
    
    Arguments:
    array: a structured numpy array
    descr: a numpy type description of the new fields

    Example:
    newarray = AddNumpyField(array, [('weight',float)])
    '''
    if array.dtype.fields is None:
        raise ValueError, "`A' must be a structured numpy array"
    array2 = np.empty(array.shape, dtype=array.dtype.descr + descr)
    for name in array.dtype.names:
        array2[name] = array[name]
    return array2

def MakeNumpyView(array, fields):
    '''
    Return a view of a structured array containing only the selected fields
    
    Arguments: 
    array: a structured numpy array
    fields: a list of field names to include in the view
    
    '''
    dtype2 = np.dtype({name:array.dtype.fields[name] for name in fields})
    return np.ndarray(array.shape,dtype2, array, 0, array.strides)

def MergeArrays(arrlist,joinfldname):
    '''
    Merge a list of arrays into a single array based on a common field and return
    
    Called by:
    
    
    Arguments:
    arrlist: a list of numpy arrays
    joinfldname: the name of the field to use for the join
    
    '''
    oarr = arrlist[0]
    for res in arrlist[1:]:
        #Logger("Merging: dist_{ts}_{att}".format(att=res[0],ts = res[1][0]))
        arr = res
        oarr = rfn.join_by(str(joinfldname), oarr, arr,'outer')
    return(oarr)

def AppendArrays(arrlist,joinfldname):
    '''
    Append a list of arrays into a single array based on a common field and return
    
    Called by:
    
    
    Arguments:
    arrlist: a list of numpy arrays
    joinfldname: the name of the field to use for the join
    
    '''
    oarr = arrlist[0]
    for res in arrlist[1:]:
        #Logger("Merging: dist_{ts}_{att}".format(att=res[0],ts = res[1][0]))
        arr = res
        oarr = rfn.join_by(str(joinfldname), oarr, arr,'outer')
        oarr = rfn.append_fields(oarr, str(newfldname), arr, usemask = False)
    return(oarr)


def MergeDataFrames(dflist,joinfldname):
    '''
    Merge a list of dataframes into a single array based on a common field and return. Make sure that the order of the input lists is what you want. 
    
    Called by:
    AllocUtilities.MakeDevSpace
    
    Arguments:
    dflist: a list of numpy arrays
    joinfldname: the name of the field to use for the join
    
    '''
    rdf = dflist[0]
    for df in dflist[1:]:
        #Logger("Merging: dist_{ts}_{att}".format(att=res[0],ts = res[1][0]))
        rdf = pd.merge(rdf,df,on=str(joinfldname), how='left')
    return(rdf)

def UPCleanup(UPConfig):
    '''
    A utility function to reset the database to a pre-uplan run state
    This removes all tables and feature classes that start with "up_" or "upo".
    
    
    Argument:
    UPConfig
    '''
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.overwriteOutput = True
    
    Logger("Cleaning up")
    fcs = arcpy.ListFeatureClasses()
    for fc in fcs:
        if fc[:3] in ["up_","upo"]:
            Logger("Deleting: {fc}".format(fc=fc))
            arcpy.Delete_management(fc)
    
    tbls = arcpy.ListTables()
    for tbl in tbls:
        if tbl[:3] in ["up_","upo"]:
            Logger("Deleting: {tbl}".format(tbl=tbl))
            arcpy.Delete_management(tbl)

    
    Logger("Done")


def UPCleanup_Alloc(UPConfig):
    '''
    A utility function to remove all tables generated as part of the allocation process
    
    
    Argument:
    UPConfig
    '''
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.overwriteOutput = True
    
    Logger("Cleaning up")
    fcs = arcpy.ListFeatureClasses()
    for fc in fcs:
        if fc[:4] =="upo_":
            Logger("Deleting: {fc}".format(fc=fc))
            arcpy.Delete_management(fc)
    
    tbls = arcpy.ListTables()
    for tbl in tbls:
        if tbl[:4] == "upo_":
            Logger("Deleting: {tbl}".format(tbl=tbl))
            arcpy.Delete_management(tbl)

    
    Logger("Done")

def UPCleanup_Subareas(UPConfig):
    '''
    A utility function to remove tables generated as part of the subarea calculations
    
    
    Argument:
    UPConfig
    '''
    
    Logger("Cleanup: Subareas")
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.overwriteOutput = True
    
    tbls = arcpy.ListTables()
    for tbl in tbls:
        if tbl[:5] == "up_sa":
            Logger("Deleting: {tbl}".format(tbl=tbl))
            arcpy.Delete_management(tbl)
    
    Logger("Done")

def UPCleanup_Weights(UPConfig):
    '''
    A utility function to remove tables generated as part of the weights calculation step
    
    
    Argument:
    UPConfig
    '''
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.overwriteOutput = True
    
    Logger("Cleaning up")
    tbls = arcpy.ListTables()
    for tbl in tbls:
        if tbl[:12] == "up_distances":
            Logger("Deleting: {tbl}".format(tbl=tbl))
            arcpy.Delete_management(tbl)
        if tbl[:14] == "up_net_weights":
            Logger("Deleting: {tbl}".format(tbl=tbl))
            arcpy.Delete_management(tbl)
    
    Logger("Done")


    
def UPCleanup_Constraints(UPConfig):
    '''
    A utility function to remove tables generated as part of the constraints calculation process
    
    
    Argument:
    UPConfig
    '''
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.overwriteOutput = True
    
    Logger("Cleaning up")
    fcs = arcpy.ListFeatureClasses()
    for fc in fcs:
        if fc[:14] =="up_constraints":
            Logger("Deleting: {fc}".format(fc=fc))
            arcpy.Delete_management(fc)
    
    tbls = arcpy.ListTables()
    for tbl in tbls:
        if tbl[:8] == "up_const":
            Logger("Deleting: {tbl}".format(tbl=tbl))
            arcpy.Delete_management(tbl)
            
        if tbl[:15] == "up_disagg_const":
            Logger("Deleting: {tbl}".format(tbl=tbl))
            arcpy.Delete_management(tbl)

    
    Logger("Done")
 
def UPCleanup_GeneralPlans(UPConfig):
    '''
    A utility function to remove tables that are generated as part of the General Plan preparation
    
    
    Argument:
    UPConfig
    '''
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.overwriteOutput = True
    
    Logger("Cleaning up")
    fcs = arcpy.ListFeatureClasses()
    for fc in fcs:
        if fc[:8] =="up_bg_gp":
            Logger("Deleting: {fc}".format(fc=fc))
            arcpy.Delete_management(fc)
    
    tbls = arcpy.ListTables()
    for tbl in tbls:
        if tbl[:8] == "up_bg_gp":
            Logger("Deleting: {tbl}".format(tbl=tbl))
            arcpy.Delete_management(tbl)
            
    
    Logger("Done") 
 
    
def ConvertPdDataFrameToNumpyArray(df):
    '''
    A utility function to convert a pandas dataframe to a structured numpy array.
    
    Argument:
    df: the dataframe to convert
    dtypes: a dtypes specification for the output structured array.
    '''
    arr = np.array(df.to_records(False))
    return(arr)

def SavePdDataFrameToTable(df,path, tablename):
    '''
    A utility function to save a pandas dataframe to a table.
    
    Argument:
    df: the dataframe to convert
    tablename: the table name to save as.
    '''
    nparray = ConvertPdDataFrameToNumpyArray(df)
    
    dts = nparray.dtype.descr
    i = 0
    for dt in dts:
        print(dt[1][0:2])
        if dt[1][0:2] == "|O":
            dts[i] = (dt[0],"".join(['|S',dt[1][2:]]))
            pass
        i += 1
           
    dts = np.dtype(dts)
    nparray = nparray.astype(dts)
    
    # Format output
    outpath = os.path.join(path,tablename)
    
    try:
        arcpy.da.NumPyArrayToTable(nparray,outpath)
    except Exception, e:
        Logger("Error Saving Pandas DataFrame to table: \n {err}".format(err = str(e)))
        raise e
    
def OrderLU(UPConfig,lulist):
    '''
    Sort a list of land uses into the order specified in UPConfig['LUPrioirty']
    
    Arguments:
    UPConfig
    A list of land uses (short names)
    
    Returns:
    A the list sorted to match the order of the LU Priority.
    
    '''
    olist = []
    for lu in UPConfig['LUPriority']:
        if lu in lulist:
            if lu not in olist: #avoid any duplicates
                olist.append(lu)
    return(olist)

def FieldExist(featureclass, fieldname):
    '''
    If the field exists, this will return true
    Source: http://gis.stackexchange.com/questions/26892/search-if-field-exists-in-feature-class (Bjorn Kuiper's function)    
    '''
    fieldList = arcpy.ListFields(featureclass, fieldname)

    fieldCount = len(fieldList)

    if (fieldCount == 1):
        return True
    else:
        return False

