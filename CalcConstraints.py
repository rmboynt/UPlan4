"""
Created on Feb 5, 2015

@author: roth
"""
import os
import datetime
import multiprocessing
import numpy.lib.recfunctions as rfn
import numpy as np
import pandas as pd
import arcpy
import UPConfig
from Utilities import AddNumpyField,DropNumpyField,Logger,ConvertPdDataFrameToNumpyArray,UPCleanup_Constraints
import UPConfig as upc
import UIUtilities as uiut
import Utilities

def CalcDevSpaceLU(mpval):
    """
    Return a list with the timestep, land use, available area calculation array (array) and the summed developable area array (sum_array)
    array will contain the developable area for each land use within each polygon that results from unioning the basegeom_bnd with all of the constraints for this timestep.
    sum_array aggregates the areas from array back into the base_geom polygons for use within UPlan.
    
    This function is intended to be multiprocessed.
    
    Called By:
    CalcDevSpace
    
    Calls:
    Utilities.ConvertPdDataFrameToNumpyArray


    Arguments:
    mpval: This is a list with the land use, timestep and UPConfig packaged together for use in multprocessing.
    
    Returns:
    a list with: [TimeStep,lu,array,sum_array]
    TimeStep
    lu
    con_array: Disagg constraint array (developable space and constraints for each sub part of a BaseGeom polgyon
    bg_devac_arr: Developable space aggreagated back up to the BaseGeom 
    """
    #import arcpy
    lu = mpval[1]
    TimeStep=mpval[0]
    UPConfig = mpval[2]
    Logger("  Working on:{lu}".format(lu=lu))
    
    cons_sum_list = []
    fldlist = ['OBJECTID',UPConfig['BaseGeom_id'],'acres_const'] + UPConfig[TimeStep[0]]['constraints']
    array = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_constraints_{ts}'.format(ts = TimeStep[0])),fldlist)
    condf = pd.DataFrame(array)
    # Add constraint proportion fields and calclate them for each of the constraints
    for const in UPConfig[TimeStep[0]]['constraints']:
        if lu in UPConfig[TimeStep[0]]['cweights'].keys():
            condf['_'.join([const,"const"])] = condf[const] * UPConfig[TimeStep[0]]['cweights'][lu][const]
        else:
            condf['_'.join([const,"const"])] = condf[const] * 0.0
    
    # summ the constraints
    const_list = ['_'.join([const,"const"]) for const in UPConfig[TimeStep[0]]['constraints']]
    condf['const_total'] = condf[const_list].sum(axis=1)
    
    # fix any summed constraints > 1.0 
    condf['const_total'][condf.const_total > 1.0] = 1.0
    
    # Calculate developable acres
    condf['developable_acres'] = condf['acres_const'] * (1.0 - condf['const_total'])
    
    # Add other fields
    condf['TimeStep'] = TimeStep[0]
    condf['lu'] = lu
    con_arr = ConvertPdDataFrameToNumpyArray(condf)
    
    devac = condf.loc[:,[UPConfig['BaseGeom_id'],'developable_acres']]
    bg_devac = devac.groupby(UPConfig['BaseGeom_id']).sum()
    bg_devac[UPConfig['BaseGeom_id']] = bg_devac.index
    bg_devac['lu'] = lu
    bg_devac['TimeStep'] = TimeStep[0]
    bg_devac_arr = ConvertPdDataFrameToNumpyArray(bg_devac)
    return([TimeStep,lu,con_arr,bg_devac_arr])

def MakeDisaggConstTable(UPConfig,TimeStep):
    '''
    Create an empty table to hold disaggregate constraint data in the database. 
    Only call this if you want to create a new table. This
    function is not intended to overwite exising versions. 
    
    Called By:
    WriteDisaggConstToTable
    
    Calls:
    
    Arguments:
    UPConfig
    TimeStep
    
    '''
    
    tablename = 'up_disagg_const_{ts}'.format(ts=TimeStep[0])
    const_list = UPConfig[TimeStep[0]]['constraints']
    
    if not arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_const')):
        Logger("Creating New up_disagg_const table")
        arcpy.env.overwriteOutput = False
        arcpy.CreateTable_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname']), tablename)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'O_OBJECTID', 'LONG')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),UPConfig['BaseGeom_id'], 'LONG')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'TimeStep', 'TEXT',"","",8)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'lu', 'TEXT',"","",8)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'developable_acres', 'DOUBLE')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'const_total', 'DOUBLE')
        for const in const_list: # Add fields for each constraint
            arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'const_{const}'.format(const=const), 'DOUBLE')
        # Indexes
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'O_OBJECTID','dconst_O_OBJECTID_idx' )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),UPConfig['BaseGeom_id'],"_".join(['dconst',UPConfig['BaseGeom_id'],'idx']) )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'lu',"_".join(['dconst','lu','idx']) )
        Logger("Created New up_disagg_const table")
    else:
        Logger("up_disagg_const table already exists, skipping")

def WriteDisaggConstToTable(UPConfig,TimeStep,lu,constarr):
    '''
    Add records to up_disag_const{ts}. This also removes records that duplicate the timestep and lu to be written.
    
    Called By:
    CalcDevSpace
    
    Calls:
    MakeDisaggConstTable
    RemoveDisaggConstTable
    
    Arguments:
    UPConfig
    TimeStep
    lu
    constarr: array with the disaggregate constraint data, note the number and names of fields are varaible depending on the constraints
    '''
    
    const_list = UPConfig[TimeStep[0]]['constraints']
    tablename = 'up_disagg_const_{ts}'.format(ts=TimeStep[0])
    const_fldlist = ['const_{const}'.format(const= c) for c in const_list ]
    
    if arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename)) == False:
        Logger("up_disagg_const does not exist, creating")
        MakeDisaggConstTable(UPConfig,TimeStep)

    # Remove any existing records for this timestep and land use
    RemoveDisaggConstFromTable(UPConfig, TimeStep, lu)
    
    Logger("Inserting to up_disagg_const Table: {ts} and {lu}".format(ts=TimeStep[0], lu=lu))
    # insert for this one
    flds = ['O_OBJECTID',UPConfig['BaseGeom_id'],'TimeStep','lu','developable_acres','const_total'] + const_fldlist
    cur = arcpy.da.InsertCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),flds)
    for ln in constarr:
        row = (ln['OBJECTID'],ln[UPConfig['BaseGeom_id']],ln['TimeStep'],ln['lu'], ln['developable_acres'],ln['const_total'])
        for const in const_list:
            row = row + (ln['{const}_const'.format(const=const)],)
        
        cur.insertRow(row)

def RemoveDisaggConstFromTable(UPConfig,TimeStep, lu):
    '''
    Remove records for land use and timestep from up_disagg_const
    
    Called By:
    WriteDisaggConstToTable
    
    Calls:
    
    Arguments:
    UPConfig
    TimeStep
    lu
    
    '''
    
    tablename = 'up_disagg_const_{ts}'.format(ts=TimeStep[0])
    Logger("Cleaning up_disagg_const: {lu} and {ts}".format(lu=lu, ts=TimeStep[0]))
    # Delete any records from the table for the layer
    whereclause = """TimeStep = '{ts}' AND lu = '{lu}'""".format(lu=lu, ts=TimeStep[0])
    cur = arcpy.da.UpdateCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),['OID@'],whereclause)
    for row in cur:
        cur.deleteRow()
        
def MakeConstTable(UPConfig):
    '''
    Create an empty table to hold constraint data in the database. 
    Only call this if you want to create a new table. This
    function is not intended to overwite exising versions. 
    
    Called By:
    WriteConstToTable
    
    Calls:
    
    Arguments:
    UPConfig
    
    '''
    
    tablename = 'up_const'

    
    if not arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_const')):
        Logger("Creating New up_const table")
        arcpy.env.overwriteOutput = False
        arcpy.CreateTable_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname']), tablename)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),UPConfig['BaseGeom_id'], 'LONG')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'TimeStep', 'TEXT',"","",8)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'lu', 'TEXT',"","",8)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'developable_acres', 'DOUBLE')
        # indexes
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),UPConfig['BaseGeom_id'],"_".join(['const',UPConfig['BaseGeom_id'],'idx']) )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'lu',"_".join(['const','lu','idx']) )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),'TimeStep',"_".join(['const','ts','idx']) )
        Logger("Created New up_const table")
    else:
        Logger("up_const table already exists, skipping")

def WriteConstToTable(UPConfig,TimeStep,lu,constarr):
    '''
    Add records to up_const
    
    Called By:
    CalcDevSpace
    
    Calls:
    MakeConstTable
    RemoveConstFromTable
    
    Arguments:
    UPConfig
    TimeStep
    lu
    constarr: array with constraint data for the BaseGeom_id and developable_acres
    '''

    tablename = 'up_const'
    
    if arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename)) == False:
        Logger("up_const does not exist, creating")
        MakeConstTable(UPConfig)

    # Remove any existing records for this timestep and land use
    RemoveConstFromTable(UPConfig, TimeStep, lu)
    
    Logger("Inserting to up_const Table: {ts} and {lu}".format(ts=TimeStep[0], lu=lu))
    # insert for this one
    flds = [UPConfig['BaseGeom_id'],'TimeStep','lu','developable_acres'] 
    cur = arcpy.da.InsertCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),flds)
    for ln in constarr:
        row = (ln[UPConfig['BaseGeom_id']],ln['TimeStep'],ln['lu'], ln['developable_acres'])
        
        
        cur.insertRow(row)

def RemoveConstFromTable(UPConfig,TimeStep, lu):
    '''
    Remove records for land use and timestep from up_const
    
    Called By:
    WriteConstToTable
    
    Calls:
    
    Arguments:
    UPConfig
    TimeStep
    lu
    
    '''
    
    tablename = 'up_const'
    Logger("Cleaning up_const: {lu} and {ts}".format(lu=lu, ts=TimeStep[0]))
    # Delete any records from the table for the layer
    whereclause = """TimeStep = '{ts}' AND lu = '{lu}'""".format(lu=lu, ts=TimeStep[0])
    cur = arcpy.da.UpdateCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tablename),['OID@'],whereclause)
    for row in cur:
        cur.deleteRow()

def CalcDevSpace(TimeStep, UPConfig,runMulti=True,writeResults=True):
    '''
    Returns (optionally) a array of results from running CalcDevSpaceLU for each land use.
    This calls CalcDevSpaceLU for each of the land uses in the timestep. Allows for parallelization, though there are data handling challenges. 
     
    Requires that CalcConstUnion has completed successfully.
     
    Called By:
    CalcConstraints
     
    Calls: 
    CalcDevSpaceLU
    WriteDisaggConstToTable
    WriteConstToTable
     
    Arguments:
    TimeStep
    UPConfig
    runMulti: a boolean that determines whether the process will be run as a multiprocess, or in an iterated loop. True = multiprocess, False = Loop
    writeResults: a boolean that determines whether disaggregate constraint results are written to disk.
    '''
    mplist = []
    for lu in UPConfig['LUPriority']:
        mplist.append([TimeStep,lu,UPConfig])
     
    if runMulti == True:
        Logger("Starting Multiprocess: Calculating Constraints")
        pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)
        results_array = pool.map(CalcDevSpaceLU,mplist)
        pool.close()
        pool.join()
        Logger("End Multiprocess")
    else:
        results_array = []
        for lu in UPConfig['LUPriority']:
            results_array.append(CalcDevSpaceLU([TimeStep,lu,UPConfig]))
    
    # Write results

    for ra in results_array:
        if writeResults == True:
            # Write full disagg
            WriteDisaggConstToTable(UPConfig,TimeStep,ra[1],ra[2])
        else:
            # Make sure potentiall incorrect results aren't hanging around.
            if arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_const_{ts}'.format(ts=TimeStep[0]))):
                arcpy.Delete_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_const_{ts}'.format(ts=TimeStep[0])))
                
        WriteConstToTable(UPConfig,TimeStep,ra[1],ra[3])
            
     
    return(results_array)


def CalcConstUnion(TimeStep, UPConfig):
    '''
    Write a unioned set of the basegeom_bnd and the constraints to the run geodatabase for this time step.
    
    Called By:
    CalcConstraints
    
    Arguments:
    TimeStep
    UPconfig
    '''
    Logger("Unioning constraints")
    if arcpy.ProductInfo() == 'ArcInfo':
        arcpy.Union_analysis([UPConfig['BaseGeom_bnd']] + UPConfig[TimeStep[0]]['constraints'], 'in_memory/union')
        UnionName = 'in_memory/union'
    else:
        UnionNames = []
        ConstCount = 1
        for ConstName in UPConfig[TimeStep[0]]['constraints']:
            Constraint = []
            Constraint.append(ConstName)
            if ConstCount == 1:
                arcpy.Union_analysis([UPConfig['BaseGeom_bnd']] + Constraint, 'in_memory/union1')
                ConstCount += 1
                UnionName = 'in_memory/union1'
                UnionNames.append(UnionName)
            else:
                InputUnion = []
                InputUnion.append(UnionName)
                UnionName = 'in_memory/union' + str(ConstCount)
                arcpy.Union_analysis(InputUnion + Constraint, UnionName)
                ConstCount += 1
                UnionNames.append(UnionName)
    diss_fields = [UPConfig['BaseGeom_id']] + UPConfig[TimeStep[0]]['constraints']
    #arcpy.Dissolve_management('in_memory/union','in_memory/diss',diss_fields )#[UPConfig['BaseGeom_id'],'acres', 'acres_p'] + UPConfig[TimeStep[0]]['constraints'])
    arcpy.Dissolve_management(UnionName,'in_memory/diss',diss_fields )#[UPConfig['BaseGeom_id'],'acres', 'acres_p'] + UPConfig[TimeStep[0]]['constraints'])
    
    Logger("Adding and Calculating area fields") #TODO some of this might be faster as numpy array or as an arcpy.da update cursor
    arcpy.AddField_management('in_memory/diss','acres',"DOUBLE")
    arcpy.AddField_management('in_memory/diss','acres_const',"DOUBLE")
    arcpy.AddField_management('in_memory/diss','acres_const_p',"DOUBLE")
    arcpy.CalculateField_management('in_memory/diss','acres_const','!shape.area@ACRES!','PYTHON_9.3')
    arcpy.Statistics_analysis('in_memory/diss','in_memory/sstats', [['acres_const','SUM']],UPConfig['BaseGeom_id'])
    # Index creation doesn't seem to work on in memory databases
#     arcpy.AddIndex_management('in_memory/diss', UPConfig['BaseGeom_id'],'diss_pclid_idx')
#     arcpy.AddIndex_management('in_memory/sstats', UPConfig['BaseGeom_id'],'sstats_pclid_idx')
    arcpy.MakeFeatureLayer_management('in_memory/diss','diss_lyr_{ts}'.format(ts = TimeStep[0]))
    arcpy.AddJoin_management('diss_lyr_{ts}'.format(ts = TimeStep[0]),UPConfig['BaseGeom_id'],'in_memory/sstats',UPConfig['BaseGeom_id'])
    arcpy.CalculateField_management('diss_lyr_{ts}'.format(ts = TimeStep[0]),'acres','!sstats.SUM_acres_const!','PYTHON_9.3')
    arcpy.CalculateField_management('diss_lyr_{ts}'.format(ts = TimeStep[0]),'acres_const_p','!acres_const!/!acres!','PYTHON_9.3')
    
   
    Logger("Copying Union to Database and cleanup")
    if arcpy.Exists('up_constraints_{ts}'.format(ts=TimeStep[0])) == True:
        arcpy.Delete_management('up_constraints_{ts}'.format(ts=TimeStep[0]))
    arcpy.CopyFeatures_management('in_memory/diss','up_constraints_{ts}'.format(ts=TimeStep[0]))
    arcpy.Delete_management('in_memory/diss_lyr_{ts}'.format(ts = TimeStep[0]))
    arcpy.Delete_management('in_memory/diss')
    if arcpy.ProductInfo() == 'ArcInfo':
        arcpy.Delete_management('in_memory/union')
    else:
        for TempRas in UnionNames:
            arcpy.Delete_management(TempRas)
    arcpy.Delete_management('in_memory/sstats')
    Logger("Constraints Union Complete")

def CalcConstraints(UPConfig):
    '''
    Loops through each time step and coordinates the running of the substeps.
    
    Calls: 
    CalcConstUnion
    CalcDevSpace
    
    Arguments:
    UPConfig
    '''
    Logger("Processing Constraints")
    arcpy.env.workspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname']) 
    for ts in UPConfig['TimeSteps']:
        Logger("Working on Time Step: {ts}".format(ts=ts[1]))
        CalcConstUnion(ts,UPConfig)
        CalcDevSpace(ts,UPConfig,False, True) # first boolean is multiProcessiing, Second is writing disaggregate results to table.
   
    
    Logger("Constraint Processing Complete")
    


if __name__ == "__main__":
    Logger("Running Constraints")
#     UPConfig = UPConfig.LoadUPConfig_python(True,True)
#     UPCleanup_Constraints(UPConfig)
    
    dbpath = r"..\testing" 
    dbname = 'calaveras_template_testing.gdb'
    
    UPGDB = os.path.join(dbpath,dbname)
#         UPGDB = r"..\\testing\calaveras.gdb"
#         picklepath = "\\".join([UPGDB,"UPConfig.p"])
#         UPConfig = uiut.LoadPickle(picklepath)
    splitpath = uiut.SplitPath(UPGDB)
    UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
    
    ts = ['ts1', 'TimeStep 1']
    CalcConstUnion(ts,UPConfig)
    
#     Logger("Cleaning up Constraints")
#     Utilities.UPCleanup_Constraints(UPConfig)
#     Logger("Calculating Constraints")
#     CalcConstraints(UPConfig)
    Logger("Constraints Complete")
    