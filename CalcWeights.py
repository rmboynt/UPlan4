"""
Created on Feb 9, 2015

@author: roth
"""

import os
import multiprocessing
import numpy
import numpy.lib.recfunctions as rfn
import pandas
import arcpy
from arcpy.sa import EucDistance, Sample
import UPConfig
from operator import itemgetter # for sorting lists
from Utilities import Logger,DropNumpyField,AddNumpyField,UPCleanup_Weights,ConvertPdDataFrameToNumpyArray
import UPConfig as upc
import UIUtilities as uiut
import Utilities

class LicenseError(Exception):
    pass


def MakeUPDistTable(UPConfig):
    '''
    Create an empty table to hold distance data in the database. 
    Only call this if you want to create a new table. This
    function is not intended to overwite exising versions. 
    
    Called By:
    
    Calls:
    
    Arguments:
    UPConfig
    
    '''
    
    if not arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances')):
        Logger("Creating New up_distances table")
        arcpy.env.overwriteOutput = False
        arcpy.CreateTable_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname']), 'up_distances')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances'),'attracter', 'TEXT', "","",50)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances'),UPConfig['BaseGeom_id'], 'LONG')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances'),'distance', 'DOUBLE')
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances'),'attracter','attracter_idx' )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances'),UPConfig['BaseGeom_id'],"_".join([UPConfig['BaseGeom_id'],'idx']) )
        Logger("Created New up_distances table")
    else:
        Logger("up_distances table already exists, skipping")

def RemoveDistanceFromTable(UPConfig,layername):
    '''
    Remove records for "layername" from up_distance
    
    Called By:
    CalcDistancesLayer
    
    Calls:
    
    Arguments:
    UPConfig
    layername
    
    '''
    
    if arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances')) == True:
   
        Logger("Cleaning up_distances: {ln}".format(ln=layername))
        # Delete any records from the table for the layer
        whereclause = """attracter = '{ln}'""".format(ln=layername)
        cur = arcpy.da.UpdateCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances'),['OID@'],whereclause)
        for row in cur:
            cur.deleteRow()
    else:
        Logger("up_distances does not exist: skipping cleaning")

def WriteDistanceToTable(UPConfig, Distarr):
    '''
    Add records to up_distance. If up_distances does not exist, it is created.
    
    Called By:
    CalcDistancesLayer
    
    Calls:
    
    Arguments:
    UPConfig
    Distarr a numpy structured array with (attracter, BaseGeom_id, distance)

    
    '''
    if arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances')) == False:
        Logger("Making up_distances")
        MakeUPDistTable(UPConfig)
    
    
    Logger("Inserting to Distance Table")
    # insert for this one
    cur = arcpy.da.InsertCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances'),['attracter',UPConfig['BaseGeom_id'],'distance'])
    for ln in Distarr:
        row = (ln['attracter'],ln[UPConfig['BaseGeom_id']],ln['distance'])
        cur.insertRow(row)

def CalcDistArray(inval):
    '''
    Calculate Distance Array using the Generate Near Function.
    
    Called By:
    CalcDistancesLayer
    CalcDistanceLayerMultiple
    
    Calls:
    
    Arguments:
    inval = [UPConfig,layername]
    
    
    Returns:
    Distarray: [OBJECTID, distance, BaseGeom_id, attracter]
    
    '''

    UPConfig = inval[0]
    layername = inval[1]
    
    gn_table = arcpy.GenerateNearTable_analysis(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['BaseGeom_cent']),os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],layername), 'in_memory/temp_up_dist', "","","","CLOSEST")
    # Convert gn_table to a Numpy Array
    gn_array = arcpy.da.TableToNumPyArray(gn_table, ['IN_FID','NEAR_DIST'])
    desc = arcpy.Describe(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['BaseGeom_cent']))
    oidfieldname = desc.OIDFieldName
    gn_array.dtype.names = str(oidfieldname), 'distance'
    bg_array = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['BaseGeom_cent']),[oidfieldname,UPConfig['BaseGeom_id']])
    arr = rfn.join_by(oidfieldname, gn_array, bg_array,'outer')
    arr = AddNumpyField(arr, [('attracter','<a50')])
    for ln in arr:
        ln['attracter'] = layername
    arcpy.Delete_management('in_memory/temp_up_dist')
    return(arr)

def CalcDistArrayRaster(inval):
    
    '''
    Calculate the distances using a raster process
    
    Called By:
    CalcDistancesLayer
    CalcDistanceLayerMultiple
    
    Calls:
    
        
    Arguments:
    inval = [UPConfig, layername,cellSize]
    
    
    Returns:
    Distarray: 
    
    '''
    
    try:
        # Check out spatial analyst license
        if arcpy.CheckExtension("Spatial") == "Available":
            arcpy.CheckOutExtension("Spatial")
        else:
            raise LicenseError
        
        if len(inval)==2:
            inval.append(50)
    
        UPConfig = inval[0]
        arcpy.env.workspace = "in_memory"
        arcpy.env.overwriteOutput = True
        arcpy.env.extent = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['BaseGeom_bnd'])
        # convert the layer to raster
        arcpy.FeatureToRaster_conversion(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],inval[1]),inval[1],"_".join([inval[1],"ras"]),inval[2])
        
        # Eucliean Distance
        EucDistRast = EucDistance("_".join([inval[1],"ras"]),"",inval[2])
        
        # Sample
        Sample([EucDistRast],os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['BaseGeom_cent']),"_".join([inval[1],"samp"]),"NEAREST")
        
        distarray = arcpy.da.TableToNumPyArray("_".join([inval[1],"samp"]),["*"],skip_nulls=True)
        distDF = pandas.DataFrame(distarray)
        distDF.columns = ['oid',UPConfig['BaseGeom_id'],'x','y','distance']
        
        # get array from the centroids
        
        centArray = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['BaseGeom_cent']),["OID@",UPConfig['BaseGeom_id']],skip_nulls=True)
        centDF = pandas.DataFrame(centArray)
        centDF.columns = ['oid',UPConfig['BaseGeom_id']]
        
        # Merge
        rdf = pandas.merge(centDF,distDF,on=UPConfig['BaseGeom_id'], how='left')
        rdf['attracter'] = inval[1]
        distarray = ConvertPdDataFrameToNumpyArray(rdf)

        return(distarray)

    except LicenseError:
        Logger("Spatial Analyst License is not available")
        raise
    except Exception, e:
        Logger(arcpy.GetMessages(2))
        Logger(str(e))
        raise
    finally:
        arcpy.CheckInExtension("Spatial")
#         return(distarray)

def CalcDistancesLayer(UPConfig, layername):
    '''
    Calculate Distances for one layer and enter them to up_distances table.
    
    Called By:
    main
    
    Calls:
    CalcDistArray
    RemoveDistanceFromTable
    WriteDistancetoTable
    
    Arguments:
    UPConfig
    Layername
    '''
    
    Logger("Calculating Distances: {ln}".format(ln = layername))
    if UPConfig['DistMode'] == 'GenerateNear':
        Logger("Distance Mode=GenerateNear")
        Distarr = CalcDistArray([UPConfig,layername])
        RemoveDistanceFromTable(UPConfig, layername)
        WriteDistanceToTable(UPConfig, Distarr)
        
    elif UPConfig['DistMode'] == 'RasterEuc':
        Logger("Distance Mode=RasterEuc")
        Distarr = CalcDistArrayRaster([UPConfig,layername,50])
        RemoveDistanceFromTable(UPConfig,layername)
        WriteDistanceToTable(UPConfig, Distarr)
        pass
    
    Logger("Distance Calculated")

def CalcDistanceLayerMultiple(UPConfig,layerlist,runMulti=True):
    '''
    Calculate Distances for multiple layer and enter them to up_distances table.
    
    Called By:
    
    
    Calls:
    RemoveDistanceFromTable
    WriteDistancetoTable
    CalcDistArray
    
    Arguments:
    UPConfig
    Layerlist: a list of the layer names to compute
    runMulti: if True (default) this will run as a multiprocessed step. if not, it will run them individual in order.
    
    
    Returns:
   
    '''
    Logger("Calculating Distances Multiple Layers")
    
    if arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances')) == False:
        MakeUPDistTable(UPConfig)
    
    
    if UPConfig['DistMode'] == 'GenerateNear':
        Logger("Distance Mode=GenerateNear")
        procList = []
        for ln in layerlist:
            procList.append([UPConfig,ln])
            
            
        if runMulti:
            Logger("Starting Multiprocess: Calculating Distances")
            pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)
            results_array = pool.map(CalcDistArray,procList)
            pool.close()
            pool.join()
            Logger("End Multiprocess")
        else:
            results_array = []
            for proc in procList:
                results_array.append(CalcDistArray(proc))
        
        tpl_results_array = tuple(results_array)
        DistArray = numpy.concatenate(tpl_results_array,axis = 0)
        

       
        for ln in layerlist:
            RemoveDistanceFromTable(UPConfig,ln)
        
        WriteDistanceToTable(UPConfig,DistArray)
   
    elif UPConfig['DistMode'] == 'RasterEuc':
        Logger("Distance Mode=RasterEuc")
        procList = []
        for ln in layerlist:
            procList.append([UPConfig,ln,50])
        
        runMulti = False # Multiprocessing doesn't seem to work well with rasters    
            
        if runMulti:
            Logger("Starting Multiprocess: Calculating Distances")
            pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)
            results_array = pool.map(CalcDistArrayRaster,procList)
            pool.close()
            pool.join()
            Logger("End Multiprocess")
        else:
            results_array = []
            for proc in procList:
                results_array.append(CalcDistArrayRaster(proc))
        
        tpl_results_array = tuple(results_array)
        DistArray = numpy.concatenate(tpl_results_array,axis = 0)
        

       
        for ln in layerlist:
            RemoveDistanceFromTable(UPConfig,ln)
        
        WriteDistanceToTable(UPConfig,DistArray)
    
    Logger("Distance Calculated")

def CalcWt(wtranges, xval):
    """
    Return the weight for the specified polygon based on the wtranges passed in.
     
    Called By: 
    GetWeightsByLuAtt
     
    Arguments:
    wtranges: a list of wtrange dictionaries (a dictionary generated in CalcWeight())
    xval: the distance from the attractor to be used with the wtranges
     
    """
    val = None
    for wtrange in wtranges:
        # Find the weight range that xval falls into.
        if (xval >= wtrange['sx'] and  xval < wtrange['ex']):
            # Calculate the weight based on the slope, xval, xrange's starting point (sx), and the range's starting weight (sy)
            val = wtrange['m']*(xval - wtrange['sx']) + wtrange['sy']
            return val
    if val == None:
        # if there's no wtrange that matches the xval then return a zero weight
        return 0

def MakeWtRange(wtpoints):
    '''
    Make a weight range list that contains the start, end, and regression formula for points between the start and end points
    to be used for calculating the weights
    
    Called By:
    GetWeightsByLuAtt

    returns:
    wtRanges
    
    '''
    
    
    wtranges = []
    if len(wtpoints) == 1:
        wtrange = {}
        wtrange['sx'] = wtpoints[0][0]
        wtrange['sy'] = wtpoints[0][1]
        wtrange['ex'] = wtpoints[0][0] + 0.1
        wtrange['ey'] = 0
        wtrange['m'] = (float(wtrange['ey']) - float(wtrange['sy']))/ \
            (float(wtrange['ex'])-float(wtrange['sx']))
        wtranges.append(wtrange)
    else:    
        for i in range(1,len(wtpoints)):
            wtrange = {}
            wtrange['sx'] = wtpoints[i-1][0]
            wtrange['sy'] = wtpoints[i-1][1]
            wtrange['ex'] = wtpoints[i][0]
            wtrange['ey'] = wtpoints[i][1]
            wtrange['m'] = (float(wtrange['ey']) - float(wtrange['sy']))/ \
                (float(wtrange['ex'])-float(wtrange['sx']))
            wtranges.append(wtrange)
    return(wtranges)

def GetWeightsByLuAtt(invals):
    '''
    Returns an array that contains the BaseGeom_id, distance, and weight for a timeseries, land use, and attracter.
    
    Called By:
    GetWeightsByTs
    
    Calls:
    MakeWtRange
    AddNumpyField
    CalcWt
    
    Returns:
    array: [attracter,BaseGeom_id,distance,weight]
    '''
    UPConfig = invals[0]
    ts = invals[1]
    lu = invals[2]
    att = invals[3]
    aweights = UPConfig[ts[0]]['aweights'][lu][att]
    
    # get distance Array
    whereclause = """ "attracter" = '{att}'""".format(att=att)
    distArray = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_distances'),['attracter',UPConfig['BaseGeom_id'],'distance'],whereclause)
    distArray = AddNumpyField(distArray,  [('weight','<f8')])
    # make WeightRanges
    wtranges = MakeWtRange(aweights)
    # Assign Weights
    for ln in distArray:
            ln['weight'] = CalcWt(wtranges,ln['distance'])
    return(distArray)

def GetWeightsByLu(mpval): #[UPConfig,TimeStep,lu,runMulti=False]
    '''
    Calculate Weights for a land use by timestep. This iterates over all of the attractors.
    
    This does not write the results to table.
    
    Called By:
    GetWeightsByTs
    
    Calls:
    GetWeightsByLuAtt
    DropNumpyField
    
    Arguments:
    list [UPConfig,TimeStep,lu]
    
    
    Returns:
    array: [Disaggwt_array, netweight_array, TimeStep[0], lu]
    '''
    UPConfig = mpval[0]
    TimeStep = mpval[1]
    lu = mpval[2]
    runMulti = mpval[3]
    Logger("Calculating Weights for {lu} in {ts}".format(lu=lu, ts=TimeStep[0]))
    
    
    # get weights list
    aweights = UPConfig[TimeStep[0]]['aweights'][lu]
    attlist = list(aweights.keys())
    
    procList = []
    for att in attlist:
        procList.append([UPConfig,TimeStep,lu,att])
        
    if runMulti:
        Logger("Starting Multiprocess: Calculating Weights")
        pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)
        results_array = pool.map(GetWeightsByLuAtt,procList)
        pool.close()
        pool.join()
        Logger("End Multiprocess")
    else:
        Logger("Starting Serial: Calculating Weights")
        results_array = []
        for proc in procList:
            results_array.append(GetWeightsByLuAtt(proc))
    
    tpl_results_array = tuple(results_array)
    WtArray = numpy.concatenate(tpl_results_array,axis = 0)
    WtDF = pandas.DataFrame(WtArray)
    sumWtDF = WtDF.groupby(str(UPConfig['BaseGeom_id'])).sum()
    sumWtDF = sumWtDF.drop('distance',1)
    # Convert Pandas DataFrame Back to Array
    exdf = sumWtDF.loc[:,['pclid','weight']]
    exdf['polyid'] = exdf.index
    netwtarr = numpy.array(exdf.to_records(False))
    pclid = str(UPConfig['BaseGeom_id'])
    netwtarr.dtype.names = 'nn','weight', pclid
    netwtarr = DropNumpyField(netwtarr, 'nn')
    #sumWtDF = sumWtDF[[UPConfig['BaseGeom_id'],'weight']]
    return([WtArray,netwtarr,TimeStep[0],lu])

def MakeUPDisaggWeightsTable(UPConfig,ts,lu):
    '''
    Create an empty table to hold distance data in the database. 
    Only call this if you want to create a new table. This
    function is not intended to overwite exising versions. 
    
    Called By:
    WriteDisaggWeightsByLu
    
    Calls:
    
    Arguments:
    UPConfig
    
    '''
    
    if not arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights')):
        Logger("Creating New up_disagg_weights table")
        arcpy.env.overwriteOutput = False
        arcpy.CreateTable_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname']), 'up_disagg_weights')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),'timestep', 'TEXT', "","",8)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),'lu', 'TEXT', "","",8)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),'attracter', 'TEXT', "","",50)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),UPConfig['BaseGeom_id'], 'LONG')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),'weight', 'DOUBLE')
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),'timestep','timestep_wt_idx' )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),'lu','lu_wt_idx' )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),'attracter','attracter_wt_idx' )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),UPConfig['BaseGeom_id'],"_".join([UPConfig['BaseGeom_id'],'wt','idx']) )
        Logger("Created New up_disagg_weights table")
    else:
        Logger("up_disagg_weights table already exists, skipping")

def WriteDisaggWeightsByLu(UPConfig,ts,lu,weights):
    '''
    Write disaggregate weight to table by lu. 
    Creates the table if it doesn't exist, and empties potentially confilicting data
    
    Called By:
    GetWeightsByTs
    main
    
    Calls:
    makeUPDisaggWeightsTable
    RemoveDisaggWeightsFromTableByLu
    
    
    '''
    if not arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights')):
        MakeUPDisaggWeightsTable(UPConfig,ts,lu)
    else:
        RemoveDisaggWeightsFromTableByLu(UPConfig,ts,lu)
        
    
    Logger("Writing Disaggregate Weights")
    cur = arcpy.da.InsertCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),['timestep','lu','attracter',UPConfig['BaseGeom_id'],'weight'])
    for ln in weights:
        row = (ts[0],lu,ln['attracter'],ln[UPConfig['BaseGeom_id']],ln['weight'])
        cur.insertRow(row)
    Logger("Weights Written")
    
def RemoveDisaggWeightsFromTableByLu(UPConfig,ts,lu):
    '''
    Remove records for "layername" from up_distance
    
    Called By:
    WriteDisaggWeightsByLu
    
    Calls:
    
    Arguments:
    UPConfig
    layername
    
    '''
    Logger("Cleaning DisaggWeight Table: {ts}, {lu}".format(ts=ts[0],lu=lu))
    # Delete any records from the table for the layer
    whereclause = """lu = '{lu}' AND timestep = '{ts}'""".format(ts=ts[0],lu=lu)
    cur = arcpy.da.UpdateCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'),['OID@'],whereclause)
    for row in cur:
        cur.deleteRow()

def MakeUPNetWeightsTable(UPConfig,ts,lu):
    '''
    Create an empty table to hold weights data in the database. 
    Only call this if you want to create a new table. This
    function is not intended to overwite exising versions. 
    
    Called By:
    WriteNetWeightsByLu
    
    Calls:
  
    Arguments:
    UPConfig
    
    '''
    
    if not arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights')):
        Logger("Creating New up_net_weights table")
        arcpy.env.overwriteOutput = False
        arcpy.CreateTable_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname']), 'up_net_weights')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),'timestep', 'TEXT', "","",8)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),'lu', 'TEXT', "","",8)
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),UPConfig['BaseGeom_id'], 'LONG')
        arcpy.AddField_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),'weight', 'DOUBLE')
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),'timestep','timestep_nwt_idx' )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),'lu','lu_nwt_idx' )
        arcpy.AddIndex_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),UPConfig['BaseGeom_id'],"_".join([UPConfig['BaseGeom_id'],'nwt','idx']) )
        Logger("Created New up_net_weights table")
    else:
        Logger("up_net_weights table already exists, skipping")    

def WriteNetWeightsByLu(UPConfig,ts,lu,weights):
    '''
    Writes net weights to table. Creates the table if needed and removes potentially conflicting data.
    
    Called By:
    GetWeightsByTs
    
    Calls:
    MakeUPNetWeightsTable
    RemoveNetWeightsFromTableByLu
    '''
    
    if not arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights')):
        MakeUPNetWeightsTable(UPConfig,ts,lu)
    else:
        RemoveNetWeightsFromTableByLu(UPConfig,ts,lu)
    
    Logger("Writing Net Weights")
    cur = arcpy.da.InsertCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),['timestep','lu',UPConfig['BaseGeom_id'],'weight'])
    for ln in weights:
        row = (ts[0],lu,ln[UPConfig['BaseGeom_id']],ln['weight'])
        cur.insertRow(row)
    Logger("Weights Written")

def RemoveNetWeightsFromTableByLu(UPConfig,ts,lu):
    '''
    Remove records for "layername" from up_distance
    
    Called By:
    CalcDistancesLayer
    
    Calls:
    
    Arguments:
    UPConfig
    TimeStep
    lu
    '''
    Logger("Cleaning Net Table: {ts}, {lu}".format(ts=ts[0],lu=lu))
    # Delete any records from the table for the layer
    whereclause = """lu = '{lu}' AND timestep = '{ts}'""".format(ts=ts[0],lu=lu)
    cur = arcpy.da.UpdateCursor(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),['OID@'],whereclause)
    for row in cur:
        cur.deleteRow()

def GetWeightsByTs(gwbt_vals):#[UPConfig,ts,writeResults,runMulti]
    # generate weights for all lu in ts. assumes that all distances are already calculated.
    '''
    Write tables with weights for each BaseGeom_id for each landuse for a timestep.
    This is multi-processable. 
    

    Called By:
    main
    
    
    Calls:
    GetWeightsByLu
    WriteDisaggWeightsByLu
    RemoveDisaggWeightsFromTableByLu
    WriteNetWeightsByLu
    
    Arguments:
    list[UPConfig,TimeStep,writeResults,runMulti] runMulti is a boolean, writResults determines if disaggregate weights are saved. This is the most time consuming part of the process by far.
    
    Returns:
    (optional) array with weights for each landuse in a time series by BaseGeom_id
    '''
    UPConfig = gwbt_vals[0]
    ts = gwbt_vals[1]
    writeResults = gwbt_vals[2]
    runMulti = gwbt_vals[3]
    

    Logger("Calculating Weights for all Land uses in Timestep: {ts}".format(ts=ts[0]))
    mpvals = []
    for lu in UPConfig['LUPriority']:
        if UPConfig['AllocMethods'][lu]==1:
            mpvals.append([UPConfig,ts,lu,False]) # note cannot multiprocess from within a multi-process
    
    if runMulti:
        
        pool = multiprocessing.Pool(multiprocessing.cpu_count()-1)
        results_array = pool.map(GetWeightsByLu,mpvals) # Each item in results_array = [WtArray,netwtarr,TimeStep[0],lu] 
        pool.close()
        pool.join()
    else:
        results_array = []
        for mpval in mpvals:
            results_array.append(GetWeightsByLu(mpval))
    Logger("Calculated Weights")
    
    for r in results_array:
        Logger("Writing Weights for {lu} in {ts}".format(lu = r[3],ts=ts[0]))
        if writeResults == True:
            Logger("Writing Disaggregate Weights for {lu} in {ts}".format(lu = r[3],ts=ts[0]))
            WriteDisaggWeightsByLu(UPConfig,ts,r[3],r[0])
        else:
            if arcpy.Exists(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights')) == True:
                #RemoveDisaggWeightsFromTableByLu(UPConfig,ts,r[3])
                arcpy.Delete_management(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_disagg_weights'))
        Logger("Writing Net Weights for {lu} in {ts}".format(lu = r[3],ts=ts[0]))
        WriteNetWeightsByLu(UPConfig,ts,r[3],r[1])
    
    Logger("Calculated Weights for all Land uses in Timestep: {ts}".format(ts=ts[0]))
    return(results_array)
       
     
if __name__ == "__main__":
    Logger("Calculating Weights")
    dbpath = r"..\testing\TestAllocation" 
    dbname = 'AllocTest.gdb'
    UPGDB = os.path.join(dbpath,dbname)
    saveDisaggWts = True
#         UPGDB = r"..\\testing\calaveras.gdb"
#         saveDisaggWts = False
#         picklepath = "\\".join([UPGDB,"UPConfig.p"])
#         UPConfig = uiut.LoadPickle(picklepath)
    splitpath = uiut.SplitPath(UPGDB)
    UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
    Logger("Cleaning up Weights")
    Utilities.UPCleanup_Weights(UPConfig)
    Logger("Calculating Distances")
    # Get unique set of attractors
    attractors = []
    for TimeStep in UPConfig['TimeSteps']: # Build a list of all attractors used in the run.
        newattractors = UPConfig[TimeStep[0]]['attractors']
        attractors = attractors + newattractors
    attractors = set(attractors)
    CalcDistanceLayerMultiple(UPConfig,attractors,False) # False disables multi processing.
     
    for TimeStep in UPConfig['TimeSteps']:
        Logger("Working on time step: {ts}".format(ts = TimeStep[0]))
        GetWeightsByTs([UPConfig,TimeStep,saveDisaggWts,False]) #[UPConfig,ts,writeResults,runMulti]
         
    Logger("Weights Complete")
    
    
    
    
#     
#     UPConfig = UPConfig.ReadUPConfigFromGDB(dbpath, dbname)
#     #UPConfig = UPConfig.LoadUPConfig_python(True,True)
#      
#     # Cleanup
#     UPCleanup_Weights(UPConfig) # removes all from including up_distance and up_net_weights
#      
#     # switch to raster
#     #UPConfig['DistMode'] = 'RasterEuc'
#      
#    
#      
#     # Test making table
#     #MakeUPDistTable(UPConfig)
#      
#     # Test individual Layer distance calc.
#     #CalcDistancesLayer(UPConfig, 'rds_shwy')
#      
#     # Test Calculating Distances
#     attractors = []
#     for TimeStep in UPConfig['TimeSteps']:
#         newattractors = UPConfig[TimeStep[0]]['attractors']
#         attractors = attractors + newattractors
#     attractors = set(attractors)
#     CalcDistanceLayerMultiple(UPConfig, attractors)
#      
#     # Test raster distance Calculation
# #     resultVec = CalcDistArray([UPConfig,'rds_shwy'])
# #     resultRas = CalcDistArrayRaster([UPConfig,'rds_shwy', 50])
#      
#     Logger("pause")
#      
#      
#     # Test making weights (one land use)
# # Weights = GetWeightsByLu([UPConfig, UPConfig['TimeSteps'][0],'ind',True]) # Weights is a list Weights[0] is the weights by attractor, Weights[1] is a pandas df with net weights
#      
#     # Test run weights for all land uses in time step (saving disagg weights):
#     #results = GetWeightsByTs([UPConfig,UPConfig['TimeSteps'][0],True,True]) #[UPConfig,ts,writeResults,runMulti]
#     # Test run weights for all land uses not saving disagg weights
#     #results = GetWeightsByTs([UPConfig,UPConfig['TimeSteps'][0],False,True]) #[UPConfig,ts,writeResults,runMulti]
#     #results = GetWeightsByTs([UPConfig,UPConfig['TimeSteps'][1],False,True])
#      
#      
#      
#     # Run use in a model.
# #     CalcDistanceLayerMultiple(UPConfig, ['rds_shwy','rds_main','cp_tc','angels_bnd'])
#     for TimeStep in UPConfig['TimeSteps']:
#         print(TimeStep)
#         results = GetWeightsByTs([UPConfig,TimeStep,False,False]) #[UPConfig,ts,writeResults,runMulti]
# #     results = GetWeightsByTs([UPConfig,UPConfig['TimeSteps'][1],False,False])
#      
#     Logger("Weights Calculated")  