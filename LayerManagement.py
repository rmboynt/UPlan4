'''
Created on Mar 20, 2015

@author: bjorkman, boynton
'''
import os
import datetime
import numpy as np
import numpy.lib.recfunctions as rfn
import arcpy
import pandas as pd
from Utilities import Logger, FieldExist
from arcpy import env
import UPConfig as upc
import UIUtilities as uiut

def CalculateFieldTo1(InWorkspace, LayerName):
    '''
    Creates a new integer field with the same name as the layer and calculates all rows equal to 1
    
    Called by:
    ImportConstraintLayer
    ImportAttractorLayer
    
    Arguments:
    InWorkspace: The GDB that contains the layer
    LayerName: The name of the layer
    
    Returns: None
    '''    
    #Add a new field, integer type, with name = to layer name and calculate the field =1
    InLayer = os.path.join(InWorkspace, LayerName)
             
    #Add new field to constraint layer
    arcpy.AddField_management(InLayer, LayerName, "SHORT")
    
    #Calculate field layer_num = 1
    arcpy.CalculateField_management(InLayer, LayerName, 1, "PYTHON_9.3")

def AddToUPC_Layers(InWorkspace, LayerName, long_name, LayerRole):
    '''
    Adds a row to the upc_layers table to log when the layer was added to the GDB and what Role it is assigned to
    
    Called by:
    ImportBaseGeom
    ImportConstraintLayer
    ImportAttractorLayer
    ImportGPLayer
    ImportSALayer
    
    Arguments:
    InWorkspace: The GDB that contains the layer
    LayerName: Name of the layer that was added to the GDB
    long_name: The descriptive name of the layer
    LayerRole: The Role the layer was assigned to
    
    Returns: None
    '''  
    #Add a row to the existing upc_layers table with the name of the constraint layer, the long name, the date added and the role (constraint)  
    InTable = os.path.join(InWorkspace, 'upc_layers')
      
    #Add layer to upc_layers table
    fields = ['FCName', 'LongName', 'DateAdded', 'Role']
    cur = arcpy.da.InsertCursor(InTable, fields)
    
    Date = str(datetime.datetime.now().date())
    cur.insertRow((LayerName, long_name, Date, LayerRole))
    del cur
    
def UpdateUPCKeyTable(InWorkspace,KeyName,KeyValue):
    '''
    Pass this function a key to add top the upc_key table
    If this key already exists, it will update the table otherwise it will create a new row
    '''
    arcpy.env.workspace = InWorkspace
    
    Rows = arcpy.SearchCursor('upc_key', where_clause = r"KeyName = '" + KeyName + r"'")
    Row = Rows.next()
    if Row == None:
        #the key doesn't exist, add it
        cur = arcpy.da.InsertCursor('upc_key',['KeyName','KeyValue'])
        cur.insertRow((KeyName,KeyValue))
        del cur
    else:
        #the key exists, update it
        cur = arcpy.UpdateCursor('upc_key', where_clause = r"KeyName = '" + KeyName + r"'")
        URow = cur.next()
        URow.setValue('KeyValue',KeyValue)
        cur.updateRow(URow)
        del cur

def ImportBaseGeom(UPlanGDB,InSHP,DescName,CentInside):
    '''
    *Imports a Base Geometry layer to the GDB 
    *Adds a field called up_polyid and calculates it equal to the ObjectID
    *Creates a Centroid layer from the Base Geometry layer and names it BaseGeom_cent
    *Adds a record to the upc_layers table for this Base Geometry layer and the centroid layer
    *updates the upc_keys table with the new base geometry info
    *updates pickle file
    
    Calls: 
    AddToUPC_Layers
    
    Called by:
    The Import Base Geometry Toolbox
    
    Arguments:
    UPlanGDB: The UPlan GDB (where the layer will be imported)
    InSHP: The shapefile to import
    DescName: The descriptive name of the layer
    CentInsdie = True if you want to force the centroid inside of the polygons, false for true centroid
    
    Returns: None
    '''  
    arcpy.env.workspace = UPlanGDB
    arcpy.env.overwriteOutput = True
    
    #Register it with the layer tracker
    if os.path.basename(InSHP)[-4:]==".shp":
        SHPName = os.path.basename(InSHP)[:-4]
        #if the shp has a field named "OBJECTID", it needs to be deleted
        #(SHPs use FID, so if OBJECT ID is there, it's from copying form a GDB 
        #when copied back into the UPlan GDB it creates OBJECTID_1 instead of OBJECTID if OBJECTID isn't deleted)
        if FieldExist(InSHP, 'OBJECTID'):
            arcpy.DeleteField_management(InSHP, 'OBJECTID')
    else: 
        SHPName = os.path.basename(InSHP)
    AddToUPC_Layers(UPlanGDB,SHPName,DescName, 'BaseGeom_bnd')
    
    #delete up_polyid field if it exists
    if FieldExist(InSHP, 'up_polyid'):
        arcpy.DeleteField_management(InSHP, 'up_polyid')
    
    #Import the shp to the GDB
    arcpy.FeatureClassToFeatureClass_conversion(InSHP,UPlanGDB,SHPName)
    
    #Add int field called "up_polyid" and calc = to object ID
    arcpy.AddField_management(SHPName,"up_polyid","LONG")
    arcpy.CalculateField_management(SHPName,"up_polyid","!OBJECTID!","PYTHON_9.3")
    
    #Create centroid layer and drop all fields except for "up_polyid" (and shape and objectid).
    if arcpy.ProductInfo() == 'ArcInfo':
        if CentInside:
            CentType = 'INSIDE'
        else:
            CentType = 'CENTROID'
        arcpy.FeatureToPoint_management(SHPName,"poly_cent",CentType)
    else:
        CreateCentroids(UPlanGDB,SHPName)

    Fields = arcpy.ListFields("poly_cent")
    FieldList = []
    for Field in Fields:
        if not Field.required:
            if not Field.name == "up_polyid":
                FieldList.append(Field.name)
    arcpy.DeleteField_management("poly_cent",FieldList)   
    
    #add centroid layer to layer tracker table 
    AddToUPC_Layers(UPlanGDB,'poly_cent','Base Geometry Centroids (Created from: ' + SHPName + ')','BaseGeom_cent')
    
    #update upc_key table with base geometry info
    UpdateUPCKeyTable(UPlanGDB,'BaseGeom_bnd', SHPName)
    UpdateUPCKeyTable(UPlanGDB,'BaseGeom_cent', 'poly_cent')
    UpdateUPCKeyTable(UPlanGDB,'BaseGeom_id', 'up_polyid')
    
    #update pickle file
    DBSplit = uiut.SplitPath(UPlanGDB)
    UPConfig = {}
    UPConfig = upc.ReadUPConfigFromGDB(DBSplit[0],DBSplit[1])
    uiut.MakePickle(UPConfig, UPlanGDB)

def CreateCentroids(UPlanGDB,InSHPname):
    #based off of esri support - Knowlege Base - Technical Articles
    #http://support.esri.com/cn/knowledgebase/techarticles/detail/41027
    #creates centroids without using the polygon to point tool
    
    arcpy.env.workspace = UPlanGDB
    arcpy.env.overwriteOutput = True
    
    cur = arcpy.da.SearchCursor(InSHPname, "SHAPE@XY")
    CentroidCoords = []
    for feature in cur:
        CentroidCoords.append(feature[0])
        
    point = arcpy.Point()
    pointGeometryList = []
    
    for pt in CentroidCoords:        
        if pt[0] != None:
            point.X = pt[0]
            point.Y = pt[1]
        
            pointGeometry = arcpy.PointGeometry(point)
            pointGeometryList.append(pointGeometry)
    
    arcpy.CopyFeatures_management(pointGeometryList, 'in_memory/poly_cent_noatt')
    arcpy.Intersect_analysis(['in_memory/poly_cent_noatt',InSHPname],'poly_cent')
    
def ImportConstraintLayer(InConstraint, UPlanGDB, LongName):
    '''
    *Imports a Constraint layer to the GDB
    *Creates a field with the same name as the layer and calculates it equal to 1
    *Adds a record to the upc_layers table for this constraint layer
    
    Calls: 
    CalculateFieldTo1
    AddToUPC_Layers
    
    Called by:
    Import Constraint Toolbox
    
    Arguments:
    InConstraint: The layer to be added to the GDB as a constraint
    UPlanGDB: The UPlan GDB (where the layer will be imported)
    LongName: The descriptive name of the layer
    
    Returns: None
    '''  
    #Import a feature class layer to the existing geodatabase as a constraint
  
    # Set workspace
    env.workspace = UPlanGDB
    if os.path.basename(InConstraint)[-4:]==".shp":
        SHPName = os.path.basename(InConstraint)[:-4]
    else: 
        SHPName = os.path.basename(InConstraint)
        
    #Add layer to geodatabase
    arcpy.FeatureClassToGeodatabase_conversion(InConstraint, UPlanGDB)
    
    #calculate a new field = 1
    CalculateFieldTo1(UPlanGDB, SHPName)
    
    #add constraint layer to layer tracker table 
    AddToUPC_Layers(UPlanGDB, SHPName, LongName, 'Constraint')

def ImportReDevTable(InTable, UPlanGDB, LongName, PopField, EmpField):
    '''
    *Imports a redevelopment table to the GDB
    *Adds Redev keys to the upc_key table
    *Adds a record to the upc_layers table for this redev table
    
    Calls: 
    AddToUPC_Layers
    
    Called by:
    Import Redevelopment Table Toolbox
    
    Arguments:
    InTable: The table to be added to the GDB
    UPlanGDB: The UPlan GDB (where the table will be imported)
    LongName: The descriptive name of the table
    PopField: Field that contains the number of people
    EmpField: Field that contains the number of employees
    
    Returns: None
    '''   
    # Set workspace
    env.workspace = UPlanGDB
    
    RedevTableName = os.path.basename(InTable)
    
    #Add table to geodatabase
    arcpy.TableToGeodatabase_conversion(InTable, UPlanGDB)
    
    #update upc_key table with redev info
    UpdateUPCKeyTable(UPlanGDB,'Redev', RedevTableName)
    UpdateUPCKeyTable(UPlanGDB,'Redev_pop', PopField)
    UpdateUPCKeyTable(UPlanGDB,'Redev_emp', EmpField)
    
    #add redev table to layer tracker table 
    AddToUPC_Layers(UPlanGDB, RedevTableName, LongName, 'RedevTable')

def ImportZonalLayer(InZoneLayer, UPlanGDB, LongName):
    '''
    *Imports a Zonal layer to the GDB
    *Adds a record to the upc_layers table for this constraint layer
    
    Calls: 
    AddToUPC_Layers
    
    Called by:
    Import Zone Layer Toolbox
    
    Arguments:
    InZoneLayer: The layer to be added to the GDB as a zonal layer
    UPlanGDB: The UPlan GDB (where the layer will be imported)
    LongName: The descriptive name of the layer
    
    Returns: None
    '''    
    # Set workspace
    env.workspace = UPlanGDB
    if os.path.basename(InZoneLayer)[-4:]==".shp":
        SHPName = os.path.basename(InZoneLayer)[:-4]
    else: 
        SHPName = os.path.basename(InZoneLayer)
        
    #Add layer to geodatabase
    arcpy.FeatureClassToGeodatabase_conversion(InZoneLayer, UPlanGDB)
    
    #add zonal layer to layer tracker table 
    AddToUPC_Layers(UPlanGDB, SHPName, LongName, 'ZonalSummary')
    
def ImportAttractorLayer(InAttractor, UPlanGDB, LongName):
    '''
    *Imports an Attractor layer to the GDB
    *Creates a field with the same name as the layer and calculates it equal to 1
    *Adds a record to the upc_layers table for this attractor layer
    
    Calls: 
    CalculateFieldTo1
    AddToUPC_Layers
    
    Called by:
    Import Attractor Toolbox
    
    Arguments:
    InAttractor: The layer to be added to the GDB as an attractor
    UPlanGDB: The UPlan GDB (where the layer will be imported)
    LongName: The descriptive name of the layer
    
    Returns: None
    '''  
    #Import a layer to use as an attractor and record it to the Layer Tracker Table
    
    # Set workspace
    env.workspace = UPlanGDB
    if os.path.basename(InAttractor)[-4:]==".shp":
        SHPName = os.path.basename(InAttractor)[:-4]
    else: 
        SHPName = os.path.basename(InAttractor)
    #Add layer to geodatabase
    arcpy.FeatureClassToGeodatabase_conversion(InAttractor, UPlanGDB)
    
    #calculate a new field = 1
    CalculateFieldTo1(UPlanGDB, SHPName)
    
    #add constraint layer to layer tracker table 
    AddToUPC_Layers(UPlanGDB, SHPName, LongName, 'Attractor')

def ImportGPLayer(InGPLayer, UPlanGDB, LongName):
    '''
    *Imports an General Plan layer to the GDB
    *Adds a record to the upc_layers table for this attractor layer
    
    Calls: 
    AddToUPC_Layers
    
    Called by:
    Import General Plan Toolbox
    
    Arguments:
    InGPLayer: The layer to be added to the GDB as a general plan
    UPlanGDB: The UPlan GDB (where the layer will be imported)
    LongName: The descriptive name of the layer
    
    currently disabled...
    Timesteps: What timestep(s) to assign this general plan layer to
    
    Returns: None
    '''  
    #Import a general plan layer record it's role, and record the gp class field name.
    arcpy.env.workspace = UPlanGDB
    if os.path.basename(InGPLayer)[-4:]==".shp":
        SHPName = os.path.basename(InGPLayer)[:-4]
    else: 
        SHPName = os.path.basename(InGPLayer)
        
    #Add layer to geodatabase
    arcpy.FeatureClassToGeodatabase_conversion(InGPLayer, UPlanGDB)
    
    #add general plan layer to layer tracker table 
    AddToUPC_Layers(UPlanGDB, SHPName, LongName, 'GeneralPlan')
    
#     #update the upc_timesteps table
#     for Timestep in Timesteps:
#         cur = arcpy.UpdateCursor('upc_timesteps',where_clause = r"Code = '" + Timestep + r"'")
#         row = cur.next()
#         row.setValue('GPLayer',SHPName)
#         row.setValue('GPField',GPCatField)
#         cur.updateRow(row)

def ImportSALayer(InSALayer, UPlanGDB, LongName, SAIDField, SANameField, SearchLength):
    '''
    *Imports an SubArea layer to the GDB
    *Adds a record to the upc_layers table for this SubArea layer
    *Updates the upc_subareas table with the new SubAreas
    *Updates the 3 SubArea KeyNames in the upc_key table
    *Updates UPConfig.p
    
    Calls: 
    AddToUPC_Layers
    
    Called by:
    Import General Plan Toolbox
    
    Arguments:
    InSALayer: The layer to be added to the GDB as SubAreas
    UPlanGDB: The UPlan GDB (where the layer will be imported)
    LongName: The descriptive name of the layer
    SAIDField: Field within the layer that contains the SubArea codes (or IDs)
    SANameField: Field within the layer that contains the SubArea descriptions (or Names)
    SearchLength: When assigning Base Geometry centroids to SubAreas, this is the maximum distance a centroid can be outside of a SubArea polygon and still be assigned to it 
    
    Returns: None
    '''  
    #Create a function to import a Subarea Layer, record the subarea_id and replace any prior subarea records
    arcpy.env.workspace = UPlanGDB
    if os.path.basename(InSALayer)[-4:]==".shp":
        SHPName = os.path.basename(InSALayer)[:-4]
    else: 
        SHPName = os.path.basename(InSALayer)
        
    #Add layer to geodatabase
    arcpy.FeatureClassToGeodatabase_conversion(InSALayer, UPlanGDB)
    
    #add general plan layer to layer tracker table 
    AddToUPC_Layers(UPlanGDB, SHPName, LongName, 'Subareas')
    
    #clear sub areas table
    arcpy.DeleteRows_management('upc_subareas')
    
    #populate sub areas table with attributes from the new layer
    Subareas= []
    rows = arcpy.SearchCursor(SHPName)
    for row in rows:
        SA = {}
        SA['sa']= row.getValue(SAIDField)
        SA['SAName'] = row.getValue(SANameField)
        if SA not in Subareas: # don't add a SA that is already in the list
            Subareas.append(SA)   
    print(Subareas)
    
    fields = ['Code','Name']
    cur = arcpy.da.InsertCursor('upc_subareas',fields)
    for x in range(0,len(Subareas)):
        sa = Subareas[x]['sa']
        SAName = Subareas[x]['SAName']
        cur.insertRow((sa,SAName))
    del cur
    
    #update the upc_key table with the new subarea - 
    UpdateUPCKeyTable(UPlanGDB,'Subarea_bnd',SHPName)
    UpdateUPCKeyTable(UPlanGDB,'Subarea_id',SAIDField)
    UpdateUPCKeyTable(UPlanGDB,'Subarea_search',str(SearchLength)) 
    
    #update pickle file
    DBSplit = uiut.SplitPath(UPlanGDB)
    UPConfig = {}
    UPConfig = upc.ReadUPConfigFromGDB(DBSplit[0],DBSplit[1])
    uiut.MakePickle(UPConfig, UPlanGDB)
    
# def CreateOrUpdateSATable(db):
#     arcpy.env.workspace = db
#     if arcpy.Exists('upc_subareas'):
#         arcpy.Delete_management('upc_subareas')
#     
#     arcpy.CreateTable_management(db, 'upc_subareas')
#     SAFields = ['Code','Name']
#     SAFieldTypes = {'Code':'TEXT','Name':'TEXT'}
#     for SAField in SAFields:
#         arcpy.AddField_management('upc_subareas',SAField,SAFieldTypes[SAField])
    
if __name__ == "__main__":
    Logger("Layer management")
    dbpath = r"..\testing" 
    dbname = 'calaveras_template_testing.gdb'
    #db = os.path.join(dbpath,dbname)
    #InSHP = r'G:\Public\UPLAN\Uplan4\testdata\NewParcels.shp'
    db = r"G:\Public\UPLAN\Uplan4\testing\EucDist\Ryan.gdb"
    InSHPname = 'apnhum51sp_CANAD83'
    
    #UpdateUPCKeyTable(db,'TestKey', 'test input3')
    CreateCentroids(db,InSHPname)
      
#     ###Add Base Gemoetry Tool
#     InGDB = r"D:\Projects\UPlan\UPlan4\testing\calaveras.gdb"
#     InSHP = r"D:\Projects\AmadorUPlan\UPlan2_6\data\Amador_working.gdb\Parcels_20130405" 
#     LongName = 'Amador Parcels'   
#        
#     Logger("Importing Base Geometry")
#     ImportBaseGeom(InGDB,InSHP, LongName)

#     ###Add Constraint Tool  
#     GDB = os.path.join(dbpath,dbname)
#     LongName='tricolored blackbird layer'
#     #InConstraint = r'D:\Projects\RAMP2014\GIS\2015\TCB_habitat.shp'
#     InConstraint = r'G:\Public\RAMP\PilotProject2014\SpatialData_Feb15Update\TCB\tcb_4mi_diss.shp'
#      
#     Logger("Importing Constraint Layer")  
#     ImportConstraintLayer(InConstraint, GDB, LongName)
#     
#     ###Add Attractor Tool
#     GDB = os.path.join(dbpath,dbname)
#     LongName='Pacific Ocean'
#     InAttractor = r'G:\Public\StatewideData\Ocean\ocean.shp'
#       
#     Logger("Importing Attraction Layer")  
#     ImportAttractorLayer(InAttractor, GDB, LongName)
#     
#     ###Add General Plan Tool
#     GDB = os.path.join(dbpath,dbname)
#     LongName=r"Riverbank's General Plan"
#     InGP = r'G:\Public\Greenprint\SJV\Collection\GIS\LandusePlanning\FromCity\stan\Riverbank_GeneralPlan_CANAD83.shp'
#     GPCatField = "LEGEND"
#     #This timestep needs to exist already:
#     Timesteps = ['ts1']
#      
#     Logger("Importing General Plan Layer")  
#     ImportGPLayer(InGP, GDB, GPCatField, LongName,Timesteps)
# 
#     ###Add SubArea Tool
#     GDB = os.path.join(dbpath,dbname)
#     SAshp = r'C:\Projects\UPlan4\testing\subarea2.shp'
#     SHPname = 'New Cities May 2015'
#     SACodeField = 'sa'
#     SANameField = 'saname'
#     SALength = 10
#       
#     Logger("Importing SubArea Layer")
#     ImportSALayer(SAshp,GDB,SHPname,SACodeField,SANameField,SALength)

    Logger("Management Complete") 
    
    print('Script Finished!')