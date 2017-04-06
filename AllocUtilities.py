'''
Created on Apr 16, 2015

@author: roth
'''
import os
import numpy as np
import arcpy
import UPConfig
import pandas as pd
import Utilities
from Utilities import Logger
from CalcDemographics import CalcRedevEmp,CalcRedevRes


def MakeMUList(UPConfig,TimeStep,gpcat):
    '''
    Make a list of the lu combos for mixed use in a GPCat
    
    
    Called By:
    CalcAvailSpace
    
    Arguments:
    UPConfig
    TimeStep
    gpcat: general plan category name
    
    Returns:
    List(Mixed Use types)
    '''
    
    MUList = []
    
    if gpcat in list(UPConfig[TimeStep[0]]['mixeduse'].keys()):
        muses = UPConfig[TimeStep[0]]['mixeduse'][gpcat]
        MUList = [OrderLU(UPConfig,mul) for mul in muses]
        return(MUList)
    else:
        return(None)

def OrderLU(UPConfig,lulist):
    """
    Take a list of land uses, and sort them into the LUPriority order
    
    Called By:
    CalcAvailSpace
    
    Arguments:
    UPConfig
    lulist: A list of land uses
    
    Returns:
    a sorted list of land uses.
    
    """
    
    olist = []
    for lu in UPConfig['LUPriority']:
        if str(lu) in lulist:
            if lu not in olist: #avoid any duplicates
                olist.append(str(lu))
    return(olist)

def MakeLUListForGP(UPConfig,TimeStep,gp):
    """
    Make a list of base land uses (not mixed-use) allowed into a general plan category in specific time step.
    
    Called By:
    CalcAvailSpace
    
    Arguments:
    UPConfig
    TimeStep
    gp: General Plan class name
    
    Returns:
    lulist: a list of base land uses that are allowed into a mixed use category
    """
    
    lulist = []
    for lu in UPConfig['LUPriority']:
        if gp in UPConfig[TimeStep[0]]['gplu'][lu]:
            lulist.append([str(lu)])
    return(lulist)

def MakePolyList(UPConfig): # was MakeAllocTable
    """
    Create the core of the allocation table for use in tracking the available space and the criteria for allocation in UPlan.
    Returns a Pandas data frame with the BaseGeomID and SubareaID for each base polygon.
    
    Called By:
    MakeDevSpace
    
    Arguments:
    UPConfig
    
    Returns:
    a pandas dataframe with the Polygon ID and subarea id for each polygon.
    
    """
    
    # Get the SA table
    array = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_sa'),[UPConfig['BaseGeom_id'],UPConfig['Subarea_id']])
    allocdf = pd.DataFrame(array)
    allocdf.columns = [[UPConfig['BaseGeom_id'],UPConfig['Subarea_id']]]
#     allocdf = allocdf.set_index([UPConfig['BaseGeom_id']])
#     allocdf[UPConfig['BaseGeom_id']] = allocdf.index
#     allocdf[UPConfig['Subarea_id']].apply(str) # Trying to force it to a string
    array = None

    return(allocdf)

def Allocate(UPConfig,TimeStep,sa,lu,pclid,availSpace,cumAlloc,tsAlloc,demand):
    """
    Assign land use to a polygon and update the cumulative allocation, 
    timestep allocation, and demand values to account for the allocation.
    
    If the land use being allocated has a higher priority than ones already in place, 
    the others are removed, added to the demand and will be allocated as part of that land use's
    allocation process. 
    
    Called By:
    Allocation.PriAllocLU
    
    Arguments:
    UPConfig
    TimeStep
    sa: the short subarea name associated with the polygon.
    lu: the LU being allocated
    pclid: the id for the polygon
    availSpace: amount of space available to the land use in the polygon
    cumAlloc: cumulative allocation table
    tsAlloc: time step allocation table
    demand: The remaining demand for this time step (dictionary of the timestep that includes the subareas).
    
    Returns:
    cumAlloc: updated to account for allocation
    tsAlloc: updated to account for allocation
    demand: updated to account for allocation
    """
    
    
    # Add allocation to cumAlloc, tsAlloc
    fldname = "alloc_ac_{lu}".format(lu=lu)
    
    # Calculate how much demand is needed.
    allocAc = min([availSpace[0],demand[sa][lu]])
    
    # Allocate landuse to cumulative allocation and timestep allocation
    cumAlloc.loc[cumAlloc[UPConfig['BaseGeom_id']]== pclid,fldname] = cumAlloc.loc[cumAlloc[UPConfig['BaseGeom_id']]== pclid,fldname] + allocAc
    tsAlloc.loc[tsAlloc[UPConfig['BaseGeom_id']]== pclid,fldname] = tsAlloc.loc[tsAlloc[UPConfig['BaseGeom_id']]== pclid,fldname] + allocAc
    
    # Subtract allocated amount from demand
    demand[sa][lu] = demand[sa][lu] - allocAc
    
    if availSpace[1] != []: # handle other land uses that are lower priority and are being pushed out.
        for luc in availSpace[1]:
            fldname = "alloc_ac_{lu}".format(lu=luc)
            pac = cumAlloc.loc[cumAlloc[UPConfig['BaseGeom_id']]== pclid,fldname] # get the prior allocated space for land uses that are getting pushed out.
            demand[sa][luc] = demand[sa][luc] + float(pac.values[0]) # Add it back to the demand. This should b
            cumAlloc.loc[cumAlloc[UPConfig['BaseGeom_id']]== pclid,fldname] = 0
            tsAlloc.loc[tsAlloc[UPConfig['BaseGeom_id']]== pclid,fldname] = 0

        
    
    return(cumAlloc,tsAlloc,demand)

def MakeAllocTables(UPConfig):
    """
    Make an empty allocation table. This could be cumAlloc, tsAlloc
    
    Called By:
    Allocation.Allocate
    Allocation.AllocateTimeStep
    
    Arguments:
    UPConfig
    
    Returns:
    an empty allocation table (pandas dataframe) with allocation (acres) set to 0 for each polygon
    """
    allocTable = MakePolyList(UPConfig)
    for lu in UPConfig['LUPriority']:
        #allocTable['alloc_pct_{lu}'.format(lu=lu)] = 0.0
        allocTable['alloc_ac_{lu}'.format(lu=lu)] = 0.0
    return(allocTable)

def WriteAllocTables(UPConfig,allocTable, allocTableName):
    """
    Write the allocation table to disk
    
    Called By:
    Allocation.Allocate
    
    Arguments:
    UPConfig
    allocTable: alloc table (either cumulative or timestep) to be written
    allocTableName: the name of the table to be written
    """
    
    allocNPA = Utilities.ConvertPdDataFrameToNumpyArray(allocTable)
    dtype = allocNPA.dtype.descr
#     dtype[0] = (dtype[0][0],'|S8')
    dtype[1] = (dtype[1][0],'|S8')
    dtype = np.dtype(dtype)
    allocNPA = allocNPA.astype(dtype)
    dbpath = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],allocTableName)
    arcpy.da.NumPyArrayToTable(allocNPA, dbpath)

def WriteRedev(UPConfig,cumRedev,tblName):
    """
    Write population and employment that was redeveloped. 
    
    Called By:
    Allocation.Allocate
    
    Arguments:
    UPConfig
    undAlloc: the remaining demand
    tblName: the name of the table to be written
    """
    # make the table
    arcpy.CreateTable_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname']),tblName)
    arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tblName),"Pop","LONG" )
    arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tblName),"Emp","LONG" )

    
    # open cursor
    cur = arcpy.da.InsertCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tblName),['Pop','Emp'])
    cur.insertRow((cumRedev[0],cumRedev[1]))
    del cur


def WriteUndAlloc(UPConfig,undAlloc,tblName):
    """
    Write the underallocation (left over demand for a time step) to disk. 
    
    Called By:
    Allocation.Allocate
    
    Arguments:
    UPConfig
    undAlloc: the remaining demand
    tblName: the name of the table to be written
    """
    # make the table
    arcpy.CreateTable_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname']),tblName)
    arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tblName),"Subarea","TEXT","","",12 )
    arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tblName),"LU","TEXT","","",12 )
    arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tblName),"UnderAllocation","DOUBLE")
    
    # open cursor
    cur = arcpy.da.InsertCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tblName),['Subarea','LU','UnderAllocation'])
       
    for sa in UPConfig['Subareas']:
        for lu in UPConfig['LUPriority']:
            cur.insertRow((sa['sa'],lu,undAlloc[sa['sa']][lu]))
    del cur


def AddLUField(UPConfig,tblName):
    """
    Add a field to a written out Allocation Table (File Geodatabase)
    
    Called By:
    Allocation.Allocate
    
    Arguments:
    UPConfig
    tblName: the name of the allocation table (stored in the file geodatabase) to have land uses added
    """
    
    arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tblName), "LUDesc","TEXT","","",20)
    
    fields = ["alloc_ac_{lu}".format(lu=lu) for lu in UPConfig['LUPriority']]
    fields = fields + ['LUDesc']
    
    cur = arcpy.da.UpdateCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],tblName),fields)
    
    for row in cur:
        lus = []
        i = 0
        for lu in UPConfig['LUPriority']:
            if row[i] > 0:
                lus.append(lu)
            i += 1
        if len(lus) > 1:
            luname = "_".join(lus)
        elif len(lus) == 1:
            luname = lus[0]
        else:
            luname = ""
        row[len(fields)-1] = luname
        cur.updateRow(row)
        
def MakeDevSpace(UPConfig,TimeStep):
    """
    Make the devSpaceTable to contain the list of unconstrained space for each land use in each polygon.
    This accounts for the effects of all constraints. It also contains the general plan class for each polygon.
    The last step fills in all No Data values with 0 (assuming that if there is no data, there is also no available space). 
    
    Called By:
    Allocation.PriAlloc
    
    Calls:
    MakePolyList
    MakeGPList
    Utilities.MergeDataFrames
    
    Arguments:
    UPConfig
    TimeStep (as list) - ['ts1','timestep1']
    
    Returns:
    devSpaceTable
    """

    # Build DevSpaceTable for this time step
    Logger("Preparing Developable Space Table")
    devSpaceTable = MakePolyList(UPConfig)
    
    
    for lu in UPConfig['LUPriority']: 

        # get unconstrained space
        dswhereclause = """ TimeStep = '{ts}' and lu = '{lu}' """.format(ts= TimeStep[0],lu=lu)
        dsarray = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_const'),[UPConfig['BaseGeom_id'],'developable_acres'],dswhereclause) # TODO: rename this to unconstrained_acres
        dsdf = pd.DataFrame(dsarray)
        dsdf.columns = [[UPConfig['BaseGeom_id'],'uncon_ac_{ts}_{lu}'.format(ts=TimeStep[0],lu=lu)]]
        dsarray = None
        # get gp permissablity (boolean)
        gparray = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_bg_gp_avail_{ts}'.format(ts=TimeStep[0])),[UPConfig['BaseGeom_id'],'gp_{lu}'.format(lu=lu)])
        gpdf = pd.DataFrame(gparray)
        gpdf.columns = [[UPConfig['BaseGeom_id'],'gp_{ts}_{lu}'.format(ts=TimeStep[0],lu=lu)]]
        gparray = None
        # get net weights
        wtwhereclause = """ timestep = '{ts}' and lu = '{lu}' """.format(ts= TimeStep[0],lu=lu)
        wtarray = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),[UPConfig['BaseGeom_id'],'weight'],wtwhereclause)
        wtdf = pd.DataFrame(wtarray)
        wtdf.columns = [[UPConfig['BaseGeom_id'],'wt_{ts}_{lu}'.format(ts=TimeStep[0],lu=lu)]]
        wtarray = None
        
#         #for debug
#         if lu == 'RH':
#             df1 = Utilities.ConvertPdDataFrameToNumpyArray(devSpaceTable)
#             df2 = Utilities.ConvertPdDataFrameToNumpyArray(gpdf)
#             df3 = Utilities.ConvertPdDataFrameToNumpyArray(dsdf)
#             df4 = Utilities.ConvertPdDataFrameToNumpyArray(wtdf)
            
#             arcpy.da.NumPyArrayToTable(devSpaceTable,r"G:\Public\UPLAN\Calaveras\Debug\devSpaceTable.csv")
#             arcpy.da.NumPyArrayToTable(gpdf,r"G:\Public\UPLAN\Calaveras\Debug\gpdf.csv")
#             arcpy.da.NumPyArrayToTable(dsdf,r"G:\Public\UPLAN\Calaveras\Debug\dsdf.csv")
#             arcpy.da.NumPyArrayToTable(wtdf,r"G:\Public\UPLAN\Calaveras\Debug\wtdf.csv")
            
#             Utilities.SavePdDataFrameToTable(df1, r"G:\Public\UPLAN\Calaveras\Debug", 'devSpaceTable.csv')
#             Utilities.SavePdDataFrameToTable(df2, r"G:\Public\UPLAN\Calaveras\Debug", 'gpdf.csv')
#             Utilities.SavePdDataFrameToTable(df3, r"G:\Public\UPLAN\Calaveras\Debug", 'dsdf.csv')
#             Utilities.SavePdDataFrameToTable(df4, r"G:\Public\UPLAN\Calaveras\Debug", 'wtdf.csv')
            
        # create table with developable space, gp availablity (boolean), and net weight for each parcel
        devSpaceTable = Utilities.MergeDataFrames([devSpaceTable, gpdf,dsdf,wtdf], str(UPConfig['BaseGeom_id']))
#         devSpaceTable.set_index([UPConfig['BaseGeom_id']])
#         devSpaceTable[UPConfig['BaseGeom_id']] = devSpaceTable.index #- this causes a change in parcelIDs
        
        #for debug
#         Utilities.SavePdDataFrameToTable(devSpaceTable, r"G:\Public\UPLAN\Calaveras\Debug", 'devSpaceTable.csv')
#         Utilities.SavePdDataFrameToTable(gpdf, r"G:\Public\UPLAN\Calaveras\Debug", 'gpdf.csv')
#         Utilities.SavePdDataFrameToTable(dsdf, r"G:\Public\UPLAN\Calaveras\Debug", 'dsdf.csv')
#         Utilities.SavePdDataFrameToTable(wtdf, r"G:\Public\UPLAN\Calaveras\Debug", 'wtdf.csv')
           
    # get General Plans
    gplans = MakeGPList(UPConfig,TimeStep)
     
    # Redev Table. 
    if UPConfig['Redev'] != None:
        redevTable = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['Redev'])
        flds = [UPConfig['BaseGeom_id'],UPConfig['Redev_pop'],UPConfig['Redev_emp']]
        redevarray = arcpy.da.TableToNumPyArray(redevTable,flds,skip_nulls=True)
        reDevDF = pd.DataFrame(redevarray) 
        devSpaceTable = Utilities.MergeDataFrames([devSpaceTable, gplans,reDevDF], UPConfig['BaseGeom_id'])
    else:
        devSpaceTable = Utilities.MergeDataFrames([devSpaceTable, gplans], str(UPConfig['BaseGeom_id']))
         
    # fix null values 
    devSpaceTable = devSpaceTable.fillna(0)
    
    return(devSpaceTable)

def CalcRedevAc(UPConfig,TimeStep,reDevPop,reDevEmp):
    """
    Calculates the acres needed of each land use in each subarea
    """
    
#     resReDev = CalcRedevRes(UPConfig, UPConfig['TimeSteps'][0], reDevPop)
#     empReDev = CalcRedevEmp(UPConfig, UPConfig['TimeSteps'][0], reDevEmp)
    resReDev = CalcRedevRes(UPConfig, TimeStep, reDevPop)
    empReDev = CalcRedevEmp(UPConfig, TimeStep, reDevEmp)
    
    ReDevAc = {}
    for sa in UPConfig['Subareas']:
        ReDevAc[sa['sa']] = {}
        for lu in resReDev[0][sa['sa']].keys():
            ReDevAc[sa['sa']][lu] = resReDev[0][sa['sa']][lu]
        for lu in empReDev[0][sa['sa']].keys():
            ReDevAc[sa['sa']][lu] = empReDev[0][sa['sa']][lu]
            
    

    return(ReDevAc,[resReDev[1],empReDev[1]])

def TestUnderAlloc(UPConfig,demand,NoSpace):
    """
    Test whether the only subareas and land uses with remaining demand are ones where there is no space left.
    
    return true if all remaining demand is in land uses and locations that cannot be allocated.
    
       
    """
    
    retValue = True
    
    for sa in UPConfig['Subareas']:
        for lu in UPConfig['LUPriority']:
            if NoSpace[sa['sa']][lu] == False:
                if (demand[sa['sa']][lu] > 0):
                    retValue = False
                    break
                    
    return(retValue)
    


def MergeDemand(UPConfig, demand1,demand2):
    """
    Combine two demand sets into one
    """
    
    for sa in UPConfig['Subareas']:
        for lu in UPConfig['LUPriority']:
            demand1[sa['sa']][lu] =  demand1[sa['sa']][lu] +  demand2[sa['sa']][lu]
    
    return(demand1)

def CalcNoSpace(UPConfig,demand):
    
    NoSpace = {}
    for sa in UPConfig['Subareas']:
        NoSpace[sa['sa']] = {}
        for lu in UPConfig['LUPriority']:
            DemandSpace = demand[sa['sa']][lu]
            print('DemandSpace = ' + str(DemandSpace))
            if float(DemandSpace) > 0.0:
                NoSpace[sa['sa']][lu] = True
            else:
                NoSpace[sa['sa']][lu] = False
    
    return(NoSpace)


def CalcAvailSpace(UPConfig,TimeStep,lu,row,cumAlloc):
    """
    Calculate the amount of available space for a land use in a polygon based on unconstrained acres, cumulative allocation, and general plan settings.
    
    Called By:
    Allocation.PriAllocLU
    
    Calls:
    OrderLU
    MakeLUListForGP
    MakeMUList
    
    Arguments:
    UPConfig
    TimeStep
    lu: the land use being tested for allocation.
    row: the row from devSpaceTable
    cumAlloc: cumulative allocation table
    """
    pclid = row[UPConfig['BaseGeom_id']]
    
#     if pclid == 30:
#         print("Stop here")
    
    # get cumAlloc row for polygon
    try:
        caRow = cumAlloc.loc[cumAlloc[UPConfig['BaseGeom_id']]== pclid] #cumAlloc.loc[pclid]
    except Exception, e:
        availableSpace = 0
        remList = [] 
        Logger("Error, AllocUtilities.CalcAvailSpace")
        Logger(str(e))
        #raise(e)
        return([availableSpace,remList])
    

    # get GP
    gp = row[UPConfig[TimeStep[0]]['gp'][1]]
    
    # get list of existing land use allocations
    exlu = []
    for lup in UPConfig['LUPriority']:
        palloc = caRow['alloc_ac_{lup}'.format(lup = lup)]
        if float(palloc) > 0.0:
            exlu.append(lup)
    
    if lu not in exlu:
        poslu = [lu] + exlu
    else:
        poslu = exlu # Fixing this should have all of the existing lu plus the potential new one.
    
    poslu = OrderLU(UPConfig, poslu)
    
    # get list of allowed base gp
    allowedLU = MakeLUListForGP(UPConfig, TimeStep, gp)
    
    # get list of allowe mu
    allowedMU = MakeMUList(UPConfig, TimeStep, gp)
    
    if allowedMU != None:
        avlist = allowedLU + allowedMU
    else:
        avlist = allowedLU
        
    if [lu] in avlist: # Land use is in the allowed list
        if poslu in avlist:
            # new land use is allowed, calculate available space
            availableSpace = float(row['uncon_ac_{ts}_{lu}'.format(ts = TimeStep[0], lu = lu)] - caRow['alloc_ac_{lu}'.format(lu = lu)])
            remList = [] # list of land uses that if it's allocated need to be removed.
            if exlu != []:
                hasDev = True
            else:
                hasDev = False
        elif IsHigherPriority(UPConfig, lu, exlu): # Check if the new land use is higher priority than the old one
            availableSpace = float(row['uncon_ac_{ts}_{lu}'.format(ts = TimeStep[0], lu = lu)] - caRow['alloc_ac_{lu}'.format(lu = lu)])
            remList = exlu # list of land uses to remove and add back to demand.
            if exlu != []:
                hasDev = True
            else:
                hasDev = False
        else: # Catch landuses that would be allowed except that there's a higher priority land use already there.
            availableSpace = 0
            remList = []
            if exlu != []:
                hasDev = True
            else:
                hasDev = False        
    
    else:
        #new land use is not allowed
 
        availableSpace = 0
        remList = [] 
        hasDev = True
    
    return([availableSpace,remList,hasDev])
    
def IsHigherPriority(UPConfig,lu,lulist):
    
    """
    Test whether a land use has a higher priority than any of the existing land uses in a list.
    
    Called By:
    CalcAvailSpace
    
    Arguments:
    UPConfig
    lu: the land use being tested
    lulist: the list of land uses
    
    Returns:
    True/False
    """

    luidx = UPConfig['LUPriority'].index(lu)
    
    lulstidx = UPConfig['LUPriority'].index(lulist[0])
    
    if luidx < lulstidx:
        return(True)
    else:
        return(False)

def MakeGPList(UPConfig,TimeStep):
    """
    Make a list of the general for each polygon for the timestep
    
    Called By:
    MakeDevSpace
    
    Arguments:
    UPConfig
    TimeStep
    
    Returns:
    a pandas dataframe with the general plan class for each polygon.
    """
    
    
    # Join in the GP Class for each polygon
    gparray = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_bg_gp_{ts}'.format(ts=TimeStep[0])),[UPConfig['BaseGeom_id'],UPConfig[TimeStep[0]]['gp'][1]])
    gplans = pd.DataFrame(gparray)
    gplans.columns = [[UPConfig['BaseGeom_id'],UPConfig[TimeStep[0]]['gp'][1]]]
#     gplans = gplans.set_index([UPConfig['BaseGeom_id']])
#     gplans[UPConfig['BaseGeom_id']] = gplans.index
    gparray = None
    
    return(gplans)

if __name__ == "__main__":
    """
    Testing functions within this utility module.
    """
    
    
    Logger("Beginning Tests")
    global UPConfig
    UPConfig = UPConfig.ReadUPConfigFromGDB("..//testing","calaveras_complete.gdb")
    TimeStep = UPConfig['TimeSteps'][0]
    
#     Logger("Testing Making Allocation Table")
#     allocTable = MakeAllocTables(UPConfig)
#     Logger("Testing Saving Allocation Table")
#     try:
#         Utilities.SavePdDataFrameToTable(allocTable, "..//testing/Calaveras.gdb", 'z_testTable')
#     except Exception, e:
#         Logger("Saving Allocation Table Failed: {err}".format(err=str(e)))
         
    
    Logger("Testing DevSpace Calculations")
    devSpace = MakeDevSpace(UPConfig, TimeStep)
    Utilities.SavePdDataFrameToTable(devSpace, "..//testing/Calaveras.gdb", "z_devspace")
    Logger("DevSpace Calculation Complete")
     
    Logger("Testing Is Higher Priority")
     
    print(IsHigherPriority(UPConfig,'rm',['rh','rm','rl'],[])) # should return True
    print(IsHigherPriority(UPConfig,'rm',['rh','rm','rl'],['rl'])) # should return True
    print(IsHigherPriority(UPConfig,'rm',['rh','rm','rl'],['rh'])) # should return False
    print(IsHigherPriority(UPConfig,'rh',['rh','rm','rl'],['rh'])) # should return True
     
    Logger("Testing Is Higher Priority Complete")
    
    
#     Logger("Test Add LU Field")
#     AddLUField(UPConfig,"upo_cum_alloc_ts1")
    
    
    Logger("End Tests")
    
    # Cleanup
    Logger("Cleaning Up From Test")
   




            
            
        
    