'''
Created on Feb 5, 2015

@author: roth
'''
import os
import arcpy
import UPConfig
import multiprocessing
from Utilities import Logger,AddNumpyField,DropNumpyField,MergeArrays,UPCleanup_GeneralPlans


def CalcGPInt(TimeStep, UPConfig):
    '''
    Create a feature class with the general plan category and the polygon id for the specified timestep
    
    Called By:
    CalcGP
    
    
    Arguments:
    Timestep: which time step is being processed
    UPconfig: the primary settings configuration object
    
    '''
    
    #TODO: Convert to multiprocess
    
    Logger("Intersecting General Plan")
    arcpy.SpatialJoin_analysis(UPConfig['BaseGeom_cent'], UPConfig[TimeStep[0]]['gp'][0], 'up_bg_gp_{ts}'.format(ts=TimeStep[0]))
    
    #delete any datetime fields - creating an array later will fail if not
    DateFields = arcpy.ListFields('up_bg_gp_{ts}'.format(ts=TimeStep[0]),'*','Date')
    if len(DateFields) != 0:
        DeleteFields = []
        for DateField in DateFields:
            DeleteFields.append(DateField.name)
        arcpy.DeleteField_management('up_bg_gp_{ts}'.format(ts=TimeStep[0]),DeleteFields)
    
    arcpy.AddIndex_management('up_bg_gp_{ts}'.format(ts=TimeStep[0]),UPConfig['BaseGeom_id'], 'idx_bg_gp_pclid_{ts}'.format(ts=TimeStep[0]),'UNIQUE','ASCENDING')
    
    Logger("General Plan Intersected")

def CalcGPAvail(mpval):
    """
    Calculate the availablity of each polygon to each land use based on the time series and general plan. Return as a numpy array.
    
    Called by:
    CalcGPAvailablity
    
    Arguments:
    mpval: a list with [UPConfig,TimeStep,lu]
    
    """
    
    UPConfig = mpval[0]
    TimeStep = mpval[1]
    lu = mpval[2]
    
     
    Logger("Calculating GP Availablity for: {lu}".format(lu=lu))
    
    array = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_bg_gp_{ts}'.format(ts=TimeStep[0])),["*"])
    array = AddNumpyField(array,[('gp_{lu}'.format(lu=lu),'i4')] )
    for ln in array:
        if ln[UPConfig[TimeStep[0]]['gp'][1]] in UPConfig[TimeStep[0]]['gplu'][lu]:
            ln['gp_{lu}'.format(lu=lu)] = 1
        else:
            ln['gp_{lu}'.format(lu=lu)] = 0
    
    keepFields = [str(UPConfig['BaseGeom_id']),'gp_{lu}'.format(lu=lu)]
    array = array[keepFields].copy()
    return(array,TimeStep,lu)

    
def CalcGPAvailablity(TimeStep, UPConfig, runMulti=True):
    '''
    Create A table with the parcel id, gp category, and permissions for each land use for the parcel.
    
    Called by:
    CalcGP
    
    Calls:
    CalcGPAvail
    Utilities.MergeArrays
    
    Arguments:
    Timestep: which time step is being processed
    UPconfig: the primary settings configuration object
    '''

    
    mplist = []
    for lu in UPConfig['LUPriority']:
        # prep mpvals
        mplist.append([UPConfig, TimeStep, lu])
        
    if runMulti == True:
        Logger("Starting Multiprocess: Calculating GPAvailablity")
        pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)
        results_array = pool.map(CalcGPAvail,mplist)
        pool.close()
        pool.join()
        Logger("End Multiprocess")
    
    else:
        results_array = []
        for mpval in mplist:
            results_array.append(CalcGPAvail(mpval))
    
    arrlist = [el[0] for el in results_array]
    array = MergeArrays(arrlist,UPConfig['BaseGeom_id'])
    arcpy.da.NumPyArrayToTable(array,os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_bg_gp_avail_{ts}'.format(ts=TimeStep[0])))
    
def CalcGP(UPConfig):
    '''
    Make tables with the parcel id, gp category, and permissions for each land use for the parcel, buy TimeStep

    Called by:
    main
    
    Calls:
    CalcGPInts
    CalcGPAvailability
    
    Arguments:
    UPconfig: the primary settings configuration object

    
    '''
    Logger("Processing General Plans")
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    for ts in UPConfig['TimeSteps']:
        Logger("Working on Time Step: {ts}".format(ts=ts[1]))
        CalcGPInt(ts,UPConfig)
        CalcGPAvailablity(ts,UPConfig,False)
    
    
    Logger("General Plan Processing Complete")
    
    
# if __name__ == "__main__":
#     Logger("Running GP Calcs")
#     dbpath = r"G:\Public\UPLAN\Amador"
#     dbname = "Run_4_Recreate.gdb"
#     UPConfig2 = UPConfig.ReadUPConfigFromGDB(dbpath,dbname)
#     
#     UPCleanup_GeneralPlans(UPConfig2)
#     CalcGP(UPConfig2)
# 
#     Logger("GP Calcs Finished")   