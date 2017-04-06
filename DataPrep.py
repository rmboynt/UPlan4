'''
Created on Feb 18, 2015

@author: roth
'''
import os
import arcpy
import UPConfig
from Utilities import Logger, MakeNumpyView,AddNumpyField,DropNumpyField

# for Data preparation both internal to a run and prior to it.

def CalcSAInt(UPConfig):
    '''
    Create a table with the BaseGeom_id and the Subarea_id
    
    Called By:
    main
    
    Calls:
    Utilities.MakeNumpyView
    Utilities.AddNumpyField
    
    Arguments:
    UPconfig: the primary settings configuration object
    '''
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    
    if len(UPConfig['Subareas'])> 1:
        Logger("Intersecting SubAreas")
        arcpy.SpatialJoin_analysis(UPConfig['BaseGeom_cent'], UPConfig['Subarea_bnd'], 'up_sa_bg_t')
        array = arcpy.da.TableToNumPyArray('up_sa_bg_t',["*"])
        keepFields = [UPConfig['BaseGeom_id'],UPConfig['Subarea_id']]
        array = MakeNumpyView(array, keepFields)
        arcpy.da.NumPyArrayToTable(array,'up_sa_bg')
        Logger("SubAreas Intersected")
    else:
        Logger("Setting Single SubArea")
        array = arcpy.da.TableToNumPyArray(UPConfig['BaseGeom_cent'],["*"])
        keepFields = [UPConfig['BaseGeom_id']]
        array = MakeNumpyView(array, keepFields)
        array = AddNumpyField(array, [('Subarea_id','a8')])
        array = DropNumpyField(array, 'f0')
        for ln in array:
            ln['Subarea_id'] = UPConfig['Subareas'][0]
        arcpy.da.NumPyArrayToTable(array,os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_sa_bg'))
        Logger("SubArea set")
        
    


if __name__ == "__main__":
    Logger("Running Subarea Intersection")
    global UPConfig
    UPConfig = UPConfig.LoadUPConfig_python()
    CalcSAInt(UPConfig)
    
    Logger("Subarea Intersection Finished")     