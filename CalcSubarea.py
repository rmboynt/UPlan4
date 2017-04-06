'''
Created on Mar 9, 2015

@author: roth
'''
import arcpy
import UPConfig
import os
from Utilities import Logger,AddNumpyField, UPCleanup_Subareas



def CalcSA(UPConfig):
    '''
    Make tables with the parcel id and Subarea ID

    Called by:
    main
    
    Calls:
    
    
    Arguments:
    UPConfig: the primary settings configuration object

    
    '''
    Logger("Processing Subareas")
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.overwriteOutput = True

    
    if UPConfig['Subarea_bnd'] == '':
        Logger("Single Subarea: Default Subarea name is 'sa1'")
        # No separate subareas are being used. All polygons are considered to be part of the first subarea
        sa = 'sa1' # UPConfig['Subareas']['sa']
        arrsa = arcpy.da.TableToNumPyArray(UPConfig['BaseGeom_cent'],[UPConfig['BaseGeom_id']])
        arrsa = AddNumpyField(arrsa,[('up_said','a8')])
        for ln in arrsa:
            ln['up_said'] = sa
        arcpy.da.NumPyArrayToTable(arrsa,os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_sa'))
    
    else:
        Logger("Multiple Subareas")
        # Multiple subareas are available.
        arcpy.SpatialJoin_analysis(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['BaseGeom_cent']),os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['Subarea_bnd']),"in_memory/sa_join","JOIN_ONE_TO_ONE","KEEP_ALL","","CLOSEST",UPConfig['Subarea_search'])
        desc = arcpy.Describe("in_memory/sa_join")
        keepfields = [UPConfig['BaseGeom_id'],UPConfig['Subarea_id'],desc.OIDFieldName,desc.shapeFieldName]
        fldlist = arcpy.ListFields("in_memory/sa_join")
        delfields = []
        for fld in fldlist:
            if fld.name not in keepfields:
                delfields.append(fld.name)
        arcpy.DeleteField_management("in_memory/sa_join", delfields)
        arcpy.CopyRows_management("in_memory/sa_join", os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_sa'))


if __name__ == "__main__":
    Logger("Calculating Subareas")
    UPConfig = UPConfig.LoadUPConfig_python(True,True) # Switch to True for multi-subarea 
    UPCleanup_Subareas(UPConfig)
    CalcSA(UPConfig)
    Logger("Subarea Calculation Complete")   