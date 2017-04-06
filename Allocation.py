'''
Created on May 15, 2015

@author: roth
'''

import os
import arcpy
import UPConfig
import Utilities
import numpy as np
from Utilities import Logger
import AllocUtilities as au
import UIUtilities as uiut




def PriAllocLU(UPConfig, TimeStep,lu,demand,cumAlloc,tsAlloc,devSpaceTable,reDevTracker):
    """
    Primary Allocation function for a single land use. This function sorts the developable space table and then loops through it polygon by polygon.
    
    Features not yet implemented:
    Allocate by a system other than the standard weighted allocation.
    
    How it works:
    1. Sort the developable space table in descending order by the weights for the land use being allocated
    2. Loop through the polygons
    3. for each polygon check if there there is at least some unconstrained space potentially available for development
    4. if there is some space, calculate whether the space is available to the land use based on the general plan, and previously allocated space. Uses au.CalcAvailSpace.
    5. if space is available to this land use, assign the space to it (using au.Allocate)
    
    Called By:
    PriAlloc
    
    Calls:
    au.CalcAvailSpace
    au.Allocate
    
    Arguments:
    UPConfig
    TimeStep
    lu
    demand
    cumAlloc: cumulative Allocation Table
    tsAlloc: time step allocation table
    devSpaceTable
    reDevTracker: list [pop,emp]

    """
    
    Logger("TimeStep: {ts}, Land Use: {lu}".format(ts = TimeStep[1],lu=lu))
    
    # Needs to handle alternate allocation systems.
    # TODO: Alternative allocation systems
    
    if UPConfig['AllocMethods'][lu] == 1:
        numrecs = len(devSpaceTable)
        
        devSpaceTable['rand'] = np.random.randn(numrecs) # Set a random number for each polygon
        
        # Sort devSpaceTable by weight
        sort_devSpaceTable = devSpaceTable.sort(['wt_{ts}_{lu}'.format(ts = TimeStep[0],lu=lu),'rand'], ascending=[False,False])
        
        #debug only
        #sort_devSpaceTable.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\DevSpaceSorted.csv")
        
        # Loop through rows
        
        for idx, row in sort_devSpaceTable.iterrows():
            pclid = row[UPConfig['BaseGeom_id']] # Fixing a missmatch in the index with the pclid.
#             if pclid == 30: # for debugging
#                 Logger("Debug")
            try:
                sa = row[UPConfig['Subarea_id']]
                try:
                    if demand[sa][lu] > 0: # Demand for the land use in the subarea is greater than zero
                        if row['uncon_ac_{ts}_{lu}'.format(ts = TimeStep[0], lu = lu)] > 0: # Amount of unconstrained space for that land use > 0
                            availSpace = au.CalcAvailSpace(UPConfig,TimeStep,lu,row,cumAlloc)
#                             avs = float(availSpace[0]) # Checking what's being converted to float
                            if availSpace[0] > 0.0:
                                allocResults = au.Allocate(UPConfig, TimeStep, sa, lu, pclid, availSpace, cumAlloc, tsAlloc, demand)
                                cumAlloc = allocResults[0]
                                tsAlloc = allocResults[1]
                                demand = allocResults[2]
                                if availSpace[2] == False:
                                    # add pop and emp from row to reDevTracker
                                    if UPConfig['Redev'] != None:
#                                         if row[UPConfig['Redev_pop']] > 0:
#                                             Logger("Pause")
#                                         if row[UPConfig['Redev_emp']] > 0:
#                                             Logger("Pause")
                                        reDevTracker[0] = reDevTracker[0] + row[UPConfig['Redev_pop']]
                                        reDevTracker[1] = reDevTracker[1] + row[UPConfig['Redev_emp']]

                except Exception, e:
                    Logger("Polygon id {pid} has a null subarea. Skipping".format(pid = str(pclid)))
            except Exception, e:
                Logger("Error in Allocation")
                print(str(e))
                raise(e)
    elif UPConfig['AllocMethods'][lu] == 2: # Random Allocation
        
        numrecs = len(devSpaceTable)
        
        devSpaceTable['wt_{ts}_{lu}'.format(ts = TimeStep[0],lu=lu)] = np.random.randn(numrecs) # Set a random number for each polygon
        
        # Sort devSpaceTable by weight
        sort_devSpaceTable = devSpaceTable.sort(['wt_{ts}_{lu}'.format(ts = TimeStep[0],lu=lu)], ascending=False) # Sort it based on the random number
        
        # Loop through rows
        
        for idx, row in sort_devSpaceTable.iterrows():
            pclid = row[UPConfig['BaseGeom_id']]
    #         if pclid == 194: # for debugging
    #             Logger("Debug")
            try:
                sa = row[UPConfig['Subarea_id']]
                try:
                    if demand[sa][lu] > 0: # Demand for the land use in the subarea is greater than zero
                        if row['uncon_ac_{ts}_{lu}'.format(ts = TimeStep[0], lu = lu)] > 0: # Amount of unconstrained space for that land use > 0
                            availSpace = au.CalcAvailSpace(UPConfig,TimeStep,lu,row,cumAlloc)
                            if availSpace[0] > 0:
                                allocResults = au.Allocate(UPConfig, TimeStep, sa, lu, pclid, availSpace, cumAlloc, tsAlloc, demand)
                                cumAlloc = allocResults[0]
                                tsAlloc = allocResults[1]
                                demand = allocResults[2]
                                if availSpace[2] == False:
                                    # add pop and emp from row to reDevTracker
                                    if UPConfig['Redev'] != None:
                                        reDevTracker[0] = reDevTracker[0] + row[UPConfig['Redev_pop']]
                                        reDevTracker[1] = reDevTracker[1] + row[UPConfig['Redev_emp']]
                except Exception, e:
                    Logger("Polygon id {pid} has a null subarea. Skipping".format(pid = str(pclid)))
            except Exception, e:
                Logger("Error in Allocation")
                print(str(e))
                raise(e)
        
    else:
        Logger("This allocation method is not supported")
                    
    return([cumAlloc,tsAlloc,demand,reDevTracker])


def PriAlloc(UPConfig,TimeStep,demand,cumAlloc,tsAlloc):
    """
    Manages the primary allocation for a TimeStep.
    
    How it works: 
    1. Create the devSpaceTable (using au.MakeDevSpace) which contains the amount of unconstrained space in each polygon for each land use.
    2. Pulls the land use demand values from UPConfig
    3. Loops through the land uses in the priority order handing them to PriAllocLU for allocation.
    4. Accept the results from PriAllocLU and get it ready for the next land use.
    
    
    Called By:
    AllocateTimeStep
    
    Calls:
    au.MakeDevSpace
    PriAllocLU
    
    Arguments:
    UPConfig
    TimeStep
    cumAlloc: cumulative allocation table
    tsAlloc: timestep allocation table
    """
    
    Logger("Allocation for TimeStep: {ts}".format(ts=TimeStep[1]))
    # Calculate Developable Space
    devSpaceTable = au.MakeDevSpace(UPConfig, TimeStep)
#     devSpaceTable.to_csv(r"G:\Public\UPLAN\Uplan4\testing\TestAllocation\temp\devSpaceTable.csv")
    
    # reDevTracker
    reDevTracker = [0,0]
    
    # Basic Demand
#     demand = UPConfig[TimeStep[0]]['Demand']
    
    # Loop Land Uses
    for lu in UPConfig['LUPriority']:
        result = PriAllocLU(UPConfig, TimeStep,lu,demand,cumAlloc,tsAlloc,devSpaceTable,reDevTracker)
        cumAlloc = result[0]
        tsAlloc = result[1]
        demand = result[2]
        reDevTracker = result[3]
    
    NoSpace = au.CalcNoSpace(UPConfig,demand)
    
    
    return([cumAlloc,tsAlloc,demand,NoSpace,reDevTracker])


def AllocateTimeStep(UPConfig,TimeStep,cumAlloc):
    """
    Manages the allocation a Timestep including all subareas, landuses, and redevelopment
    
    Features not yet implemented:
    Redevelopment

    How it works:
    1. Creates the empty allocation tables for time step (tsAlloc). 
    2. Passes parameters to PriAlloc
    3. Accepts results and prepares them to be passed on to the next time step (returned to Allocate)

    
    Called By:
    Allocate
    
    Calls:
    au.MakeAllocTables
    PriAlloc
    
    Arguments:
    UPConfig
    TimeStep
    cumAlloc: Cumulative allocation table

    """
    
    tsAlloc = au.MakeAllocTables(UPConfig)
    
    #reDev = True #TODO, make this a setting

    # get the demand
    demand = UPConfig[TimeStep[0]]['Demand']
    
    AllocComplete = False    
    # Primary Allocation
    i = 0 # Iteration Counter
    cumRedev = [0,0]
    while AllocComplete == False:
        i += 1 
        Logger("Allocation iteration: {it}".format(it = str(i)))
        PAResults = PriAlloc(UPConfig,TimeStep,demand,cumAlloc,tsAlloc)
        cumAlloc = PAResults[0]
        tsAlloc = PAResults[1]
        demand = PAResults[2] # unsatisfied demand
        NoSpace = PAResults[3]
        reDevTracker = PAResults[4]
        
        if (UPConfig['Redev'] != None): # and i < 2): # for the time being only do redev on the first iteration
#         if (UPConfig['Redev'] != None and i < 2):
            # Calculate population and emp displacement:
            
            reDevPop = reDevTracker[0] #Sample
            reDevEmp = reDevTracker[1] #Sample
            cumRedev[0] = cumRedev[0] + reDevPop
            cumRedev[1] = cumRedev[1] + reDevEmp

            
            reDevDemand =  au.CalcRedevAc(UPConfig,TimeStep,reDevPop,reDevEmp)
            demand = au.MergeDemand(UPConfig, demand, reDevDemand[0])
            reDevTracker = [0,0]
        
        
        AllocComplete = au.TestUnderAlloc(UPConfig,demand,NoSpace)
        
    
    Logger("TimeStep Allocation Complete: {ts}".format(ts = TimeStep[1]))
    return([cumAlloc,tsAlloc,demand,cumRedev])


def Allocate(UPConfig):
    """
    Manages the full allocation including all timesteps, subareas, landuses, and redevelopment
    
    How it works:
    1. Creates the cumulative allocation table
    2. Loops through the time steps
    3. For each time step:
        1. Call AllocateTimeStep()
        2. Collect the results
        3. Write the cumulative allocation, time step allocation, and any underallocation to disk. 
    4. Move to next time step.
    
    
    Called By: 
    Python Toolbox
    
    Calls:
    au.MakeAllocTables
    AllocateTimeStep
    au.WriteAllocTables
    au.AllLUField
    
    Arguments:
    UPConfig
    
    
    """
    
    # make cumAlloc
    cumAlloc = au.MakeAllocTables(UPConfig)
    
    # for TimeStep in UPConfig:
    for TimeStep in UPConfig['TimeSteps']:
        Logger("Working on Timestep: {ts}".format(ts = TimeStep[1]))
        
        TSResults = AllocateTimeStep(UPConfig, TimeStep, cumAlloc)

        
        # Save Cumulative Allocation at this point
        Logger("Writing Cumulative Allocation")
        au.WriteAllocTables(UPConfig, TSResults[0], "upo_cum_alloc_{ts}".format(ts=TimeStep[0]))
        au.AddLUField(UPConfig, "upo_cum_alloc_{ts}".format(ts=TimeStep[0]))
        
        #Save the TimeStep's Allocation
        Logger("Writing TimeStep Allocation")
        au.WriteAllocTables(UPConfig, TSResults[1], "upo_ts_alloc_{ts}".format(ts=TimeStep[0]))
        
        #Save any underallocation for the TimeStep
        Logger("Writing UnderAllocation")
        au.WriteUndAlloc(UPConfig, TSResults[2],"upo_und_alloc_{ts}".format(ts=TimeStep[0])) # AllocTables(UPConfig, TSResults[2], "upo_und_alloc_{ts}".format(ts=TimeStep[0]))
        
        Logger("Writing Redevelopment Pop and Emp")
        au.WriteRedev(UPConfig,TSResults[3],"upo_redev_{ts}".format(ts=TimeStep[0]))
        
        





if __name__ == "__main__":
    """
    Call the primary function for this module for testing purposes.
    """
    
#     dbpath = r"G:\Public\UPLAN\Uplan4\testing\TestAllocation"
#     dbname = "AllocTest_ReDev.gdb"
    dbpath = r"G:\Public\UPLAN\Calaveras\Debug"
    dbname = "RyanTest_Calaveras.gdb"

    
    #global UPConfig
#     UPConfig = UPConfig.LoadUPConfig_python(True,True)
    UPConfig = UPConfig.ReadUPConfigFromGDB(dbpath, dbname)
    UPConfig['Redev'] = None
##########uncomment this line if redev isn't working 
#     UPConfig['Redev'] = None
#     picklepath = "\\".join([dbpath,dbname,"UPConfig.p"])
#     UPConfig2 = uiut.LoadPickle(picklepath)

    Logger("Cleanup and Prep") # So it doesn't error out when trying to overwrite tables.
    Utilities.UPCleanup_Alloc(UPConfig)
    
    Logger("Run Full Allocation")
    Allocate(UPConfig)
    Logger("Allocation Complete")