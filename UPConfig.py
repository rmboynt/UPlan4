'''
Created on Feb 5, 2015

@author: roth, boynton
'''
import os
import arcpy
import datetime
import copy
import cPickle as pickle
from Utilities import Logger,OrderLU
import UIUtilities as uiut

# make a change

def EmptyUPCTables(UPConfig,UPCTables):
    '''
    Deletes all the rows in the upc_* tables
    
    Called by:
    WriteUPConfigToGDB
    
    Arguments:
    UPConfig: default UPlan configuration database
    UPCTables: A list of the table names to be emptied
    
    Returns: None
    '''
    
    #set the workspace
    InWorkspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.workspace = InWorkspace 
    
    #Empty tables (if needed)
    for UPCTable in UPCTables:
        if arcpy.Exists(UPCTable):
            Logger("Emptying Table: " + UPCTable)
            arcpy.DeleteRows_management(UPCTable)
    

def CreateUPCTables(UPConfig,UPCTables,UPCTableFields):
    '''
    Creates the upc_* tables
    
    Called by:
    WriteUPConfigToGDB
    
    Arguments:
    UPConfig: default UPlan configuration database
    UPCTables: A list of the table names to be created
    UPCTableFields: A dictionary that holds the fields to be created for each table
    
    Returns: None
    '''
    
    #set the workspace
    InWorkspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.workspace = InWorkspace 
    
    #field types
    FieldTypes = {'KeyName':'TEXT',
                 'KeyValue':'TEXT',
                 'TSOrder':'SHORT',
                 'Code':'TEXT',
                 'Name':'TEXT',
                 'GPLayer':'TEXT',
                 'GPField':'TEXT',
                 'LUType':'TEXT',
                 'AllocMethod':'TEXT',
                 'Priority':'SHORT',
                 'TSCode':'TEXT',
                 'SACode':'TEXT',
                 'LUCode':'TEXT',
                 'Acres':'DOUBLE',
                 'GPCat':'TEXT',
                 'CLayer':'TEXT',
                 'Weight':'DOUBLE',
                 'AttLayer':'TEXT',
                 'Dist':'DOUBLE',
                 'FCName':'TEXT',
                 'LongName':'TEXT',
                 'DateAdded':'DATE',
                 'Role':'TEXT'}
    
    #Create tables (if needed)
    for UPCTable in UPCTables:
        if not arcpy.Exists(UPCTable):
            #create the table
            Logger("Creating Table: " + UPCTable)
            arcpy.CreateTable_management(InWorkspace, UPCTable)
            #add the field(s)
            for Field in UPCTableFields[UPCTable]:
                arcpy.AddField_management(UPCTable,Field,FieldTypes[Field])

def WriteUPConfigToGDB(UPConfig):
    '''
    Write the contents of a UPConfig dictionary to tables in a file geodatabase. This will assume that there no existing tables, or that if they are there, they should be overwritten.
    
    Steps:
    1. Create tables (if needed)
    2. Empty tables (if needed)
    3. Populate the tables
    
    Calls:
    EmptyUPCTables
    CreateUPCTables
    
    Called by:
    
    
    Arguments:
    UPConfig: default UPlan configuration database
    dbpath: the path to the datbase
    dbname: the name of the file geodatabase
    
    Returns: None
    '''
    Logger("Writing UPConfig to database")
    
    #table names
    UPCTables = ['upc_key','upc_timesteps','upc_subareas','upc_lu','upc_demand','upc_gp','upc_gplu','upc_mu',
                 'upc_constraints','upc_cweights','upc_attractors','upc_aweights'] #,'upc_layers']
    
    UPCTableFields = {'upc_key':['KeyName','KeyValue'],
                  'upc_timesteps':['TSOrder','Code','Name','GPLayer','GPField'],
                  'upc_subareas':['Code','Name'],
                  'upc_lu':['Code','Name','LUType','AllocMethod','Priority'],
                  'upc_demand':['TSCode','SACode','LUCode','Acres'],
                  'upc_gp':['TSCode'],
                  'upc_gplu':['TSCode','LUCode','GPCat'],
                  'upc_mu':['TSCode','GPCat','LUCode'],
                  'upc_constraints':['TSCode','Name'],
                  'upc_cweights':['TSCode','LUCode','CLayer','Weight'],
                  'upc_attractors':['TSCode','Name'],
                  'upc_aweights':['TSCode','LUCode','AttLayer','Dist','Weight']}
                  #'upc_layers':['FCName','LongName','DateAdded','Role']} # remove upc_layers from this. 
    
    #empty the tables
    EmptyUPCTables(UPConfig,UPCTables)
    
    #create the tables
    CreateUPCTables(UPConfig,UPCTables,UPCTableFields)
    
    #populate the tables
    InWorkspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.workspace = InWorkspace 

    #populate upc_key table
    Logger("Populating upc_key table")
    fields = UPCTableFields['upc_key']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_key'),fields)
    
    cur.insertRow(('BaseGeom_bnd',UPConfig['BaseGeom_bnd']))
    cur.insertRow(('BaseGeom_cent',UPConfig['BaseGeom_cent']))
    cur.insertRow(('BaseGeom_id',UPConfig['BaseGeom_id']))
    cur.insertRow(('Subarea_bnd',UPConfig['Subarea_bnd']))
    cur.insertRow(('Subarea_id',UPConfig['Subarea_id']))
    cur.insertRow(('Subarea_search',UPConfig['Subarea_search']))
    cur.insertRow(('DistMode',UPConfig['DistMode']))
    if 'Redev' in UPConfig.keys():
        cur.insertRow(('Redev',UPConfig['Redev']))
        cur.insertRow(('Redev_pop',UPConfig['Redev_pop']))
        cur.insertRow(('Redev_emp',UPConfig['Redev_emp']))
    del cur
    
    #populate upc_timesteps table
    Logger("Populating upc_timesteps table")
    fields = UPCTableFields['upc_timesteps']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_timesteps'),fields)
    
    for x in range(0,len(UPConfig['TimeSteps'])):
        ts = UPConfig['TimeSteps'][x][0]
        Order = x + 1
        TimeStep = UPConfig['TimeSteps'][x][1]
        if UPConfig[ts]['gp'] != []:
            GPLayer = UPConfig[ts]['gp'][0]
            GPField = UPConfig[ts]['gp'][1]
        else:
            GPLayer = ""
            GPField = ""
        cur.insertRow((Order,ts,TimeStep,GPLayer,GPField))
    del cur
    
    #populate upc_subareas table
    Logger("Populating upc_subareas table")
    fields = UPCTableFields['upc_subareas']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_subareas'),fields)
    
    for x in range(0,len(UPConfig['Subareas'])):
        sa = UPConfig['Subareas'][x]['sa']
        SAName = UPConfig['Subareas'][x]['SAName']
        cur.insertRow((sa,SAName))
    del cur
    
    #populate upc_lu table
    Logger("Populating upc_lu table")
    fields = UPCTableFields['upc_lu']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_lu'),fields)
    
    Priority = 1
    for x in range(0,len(UPConfig['LUPriority'])):
        lu = UPConfig['LUPriority'][x]
        LUName = UPConfig['LUNames'][lu]
        AllocMethod = UPConfig['AllocMethods'][lu]
        LUType = UPConfig['LUTypes'][lu]
        cur.insertRow((lu,LUName,LUType,AllocMethod,Priority))
        Priority += 1
    del cur
    
    #populate upc_demand table
    Logger("Populating upc_demand table")
    fields = UPCTableFields['upc_demand']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_demand'),fields)
      
    for t in range(0,len(UPConfig['TimeSteps'])):
        ts = UPConfig['TimeSteps'][t][0]
        if UPConfig[ts]['Demand'] != {}:
            for s in range(0,len(UPConfig['Subareas'])):
                SACode = UPConfig['Subareas'][s]['sa']
                if len(UPConfig[ts]['Demand'][SACode].values()) != 0:
                    for l in range(0,len(UPConfig['LUPriority'])):
                        #ts = UPConfig['TimeSteps'][t][0]
                        sa = UPConfig['Subareas'][s]['sa'] 
                        lu = UPConfig['LUPriority'][l]
                        Demand = UPConfig[ts]['Demand'][sa][lu]
                        cur.insertRow((ts,sa,lu,Demand))
    del cur
                
    #populate upc_gplu table
    Logger("Populating upc_gplu table")
    fields = UPCTableFields['upc_gplu']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_gplu'),fields)
    
    for t in range(0,len(UPConfig['TimeSteps'])):
        ts = UPConfig['TimeSteps'][t][0]
        if UPConfig[ts]['gplu'] != {}: 
            for l in range(0,len(UPConfig['LUPriority'])):
                #ts = UPConfig['TimeSteps'][t][0]
                lu = UPConfig['LUPriority'][l]
                for x in range(0,len(UPConfig[ts]['gplu'][lu])):
                    GPCat = UPConfig[ts]['gplu'][lu][x]
                    cur.insertRow((ts,lu,GPCat))
    del cur
    
    #populate upc_mu table
    Logger("Populating upc_mu table")
    fields = UPCTableFields['upc_mu']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_mu'),fields)
     
    for t in range(0,len(UPConfig['TimeSteps'])):
        ts = UPConfig['TimeSteps'][t][0]
        if UPConfig[ts]['mixeduse'] != {}:
            for x in list(UPConfig[ts]['mixeduse'].keys()):
                try:
                    for y in range(0,len(UPConfig[ts]['mixeduse'][x])):
                        LUCodes = UPConfig[ts]['mixeduse'][x][y]
                        LUCodes2 = OrderLU(UPConfig,LUCodes)
                        LUCodes3=''
                        for z in range(0,len(LUCodes2)):
                            if not z == len(LUCodes2)-1:
                                LUCodes3 = LUCodes3 + LUCodes2[z] + "-"
                            else:LUCodes3 = LUCodes3 +  LUCodes2[z]
                        cur.insertRow((ts,x,LUCodes3))
                except:
                    print("Timestep =", ts)
                    print("UPConfig mulist=", UPConfig[ts]['mixeduse'])
                    print("mu key =",x )
                    print("lus=",y)
                
    #populate upc_constraints table
    Logger("Populating upc_constraints table")
    fields = UPCTableFields['upc_constraints']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_constraints'),fields)
    
    for t in range(0,len(UPConfig['TimeSteps'])):
        ts = UPConfig['TimeSteps'][t][0]
        if UPConfig[ts]['constraints'] != []:
            for x in range(0,len(UPConfig[ts]['constraints'])):
                Constraint = UPConfig[ts]['constraints'][x]
                cur.insertRow((ts,Constraint))
    del cur
    
    #populate upc_cweights table
    Logger("Populating upc_cweights table")
    fields = UPCTableFields['upc_cweights']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_cweights'),fields)
     
    for t in range(0,len(UPConfig['TimeSteps'])):
        ts = UPConfig['TimeSteps'][t][0]
        if UPConfig[ts]['cweights'] != {}:
            for l in range(0,len(UPConfig['LUPriority'])):
                lu = UPConfig['LUPriority'][l]
                if lu in UPConfig[ts]['cweights'].keys():
                    for c in range(0,len(UPConfig[ts]['constraints'])):
                        Constraint = UPConfig[ts]['constraints'][c]
                        if Constraint in UPConfig[ts]['cweights'][lu].keys():
                            Weight = UPConfig[ts]['cweights'][lu][Constraint]
                        else:
                            Weight = 0.0
                        cur.insertRow((ts,lu,Constraint,Weight))
    del cur
    
    #populate the upc_attractors table
    Logger("Populating upc_attractors table")
    fields = UPCTableFields['upc_attractors']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_attractors'),fields)
    
    for t in range(0,len(UPConfig['TimeSteps'])):
        ts = UPConfig['TimeSteps'][t][0]
        if UPConfig[ts]['attractors'] != []:
            for x in range(0,len(UPConfig[ts]['attractors'])):
                Attractor = UPConfig[ts]['attractors'][x]
                cur.insertRow((ts,Attractor))
    del cur
    
    #populate the upc_aweights table
    Logger("Populating upc_aweights table")
    fields = UPCTableFields['upc_aweights']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_aweights'),fields)
     
    for t in range(0,len(UPConfig['TimeSteps'])):
        ts = UPConfig['TimeSteps'][t][0]
        if UPConfig[ts]['aweights'] != {}:
            for l in range(0,len(UPConfig['LUPriority'])):
                lu = UPConfig['LUPriority'][l]
                for x in list(UPConfig[ts]['aweights'][lu].keys()):
                    for y in range(0,len(UPConfig[ts]['aweights'][lu][x])):
                        Dist = UPConfig[ts]['aweights'][lu][x][y][0]
                        Weight = UPConfig[ts]['aweights'][lu][x][y][1]
                        cur.insertRow((ts,lu,x,Dist,Weight))         
    del cur
    

def WriteUPCLayers(UPConfig):
    '''
    Write the contents of a UPConfig dictionary to tables in a file geodatabase. This will assume that there no existing tables, or that if they are there, they should be overwritten.
    
    Steps:
    1. Create tables (if needed)
    2. Empty tables (if needed)
    3. Populate the tables
    
    Calls:
    EmptyUPCTables
    CreateUPCTables
    
    Called by:
    
    
    Arguments:
    UPConfig: default UPlan configuration database
    dbpath: the path to the datbase
    dbname: the name of the file geodatabase
    
    Returns: None
    '''
    #table names
    UPCTables = ['upc_layers']
    
    UPCTableFields = {'upc_layers':['FCName','LongName','DateAdded','Role']} 
    
    #empty the tables
    EmptyUPCTables(UPConfig,UPCTables)
    
    #create the tables
    CreateUPCTables(UPConfig,UPCTables,UPCTableFields)
    
    #populate the tables
    InWorkspace = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.workspace = InWorkspace 
    
    #populate the upc_layers table
    Logger("Populating upc_layers table")
    fields = UPCTableFields['upc_layers']
    cur = arcpy.da.InsertCursor(os.path.join(InWorkspace,'upc_layers'),fields)
    
    #BaseGeom_bnd
    FCName = UPConfig['BaseGeom_id']
    LongName = "Base Geometry Polys (Automatic Import)"
    Date = str(datetime.datetime.now().date())
    Role = 'BaseGeom_bnd'
    cur.insertRow((FCName,LongName,Date,Role))
    
    #BaseGeom_cent
    FCName = UPConfig['BaseGeom_cent']
    LongName = "Base Geometry Centroids (Automatic Import)"
    Date = str(datetime.datetime.now().date())
    Role = 'BaseGeom_cent'
    cur.insertRow((FCName,LongName,Date,Role))
    
    #Subareas
    FCName = UPConfig['Subarea_bnd']
    LongName = "Subarea Boundary (Automatic Import)"
    Date = str(datetime.datetime.now().date())
    Role = 'Subareas'
    cur.insertRow((FCName,LongName,Date,Role))
    
    for t in range(0,len(UPConfig['TimeSteps'])):
        ts = UPConfig['TimeSteps'][t][0]
        #GeneralPlan
        FCName = UPConfig[ts]['gp'][0]
        LongName = "General Plan (Automatic Import)"
        Date = str(datetime.datetime.now().date())
        Role = 'GeneralPlan'
        cur.insertRow((FCName,LongName,Date,Role))
        
        #Constraints
        for c in range(0,len(UPConfig[ts]['constraints'])):
            Constraint = UPConfig[ts]['constraints'][c]
            LongName = UPConfig[ts]['constraints'][c] + " (Automatic Import)"
            Date = str(datetime.datetime.now().date())
            Role = 'Constraint'
            cur.insertRow((Constraint,LongName,Date,Role))
        #Attractors
        for a in range(0,len(UPConfig[ts]['attractors'])):
            Attractor = UPConfig[ts]['attractors'][a]
            LongName = UPConfig[ts]['attractors'][a] + " (Automatic Import)"
            Date = str(datetime.datetime.now().date())
            Role = 'Attractor'
            cur.insertRow((Attractor,LongName,Date,Role))
    del cur

def unique_values(table, field):
    '''
    This function can be used to return a unique list of field values.
    Source: ArcPy Cafe (https://arcpy.wordpress.com/2012/02/01/create-a-list-of-unique-field-values/)
    
    Called by:
    ReadUPConfigFromGDB
    
    Arguments:
    table: The table that contains the field you want to get unique vales from
    field: the field you want to get a list of unique values from
    
    Returns: a list of unique values
    '''
  
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return(sorted({row[0] for row in cursor}))

# def unique_values2(table, AllFields):
#     '''
#     Same as the other function, but returns unique values from more than one field
#     '''
#     
#     with arcpy.da.SearchCursor(table, AllFields) as cursor:
#         ListUnique = sorted({(row[0]+ ':' + row[1]) for row in cursor})
#         ReturnList = []
#         for i in ListUnique:
#             ReturnList.append(i.split(':'))
#         return(ReturnList)
    
def ReadUPConfigFromGDB(dbpath,dbname):
    '''
    Reads the contents of a UPlan file geodatabase's configuration tables into a UPConfig dictionary
    
    Calls:
    unique_values
    
    Called by:
    
    Arguments:
    dbpath: the path to the datbase
    dbname: the name of the file geodatabase
    
    Returns: UPConfig
    '''
    Logger("Reading UPConfig from database")
    UPConfig = {}
    
    paths={'dbpath':dbpath, 'dbname':dbname}
    UPConfig['paths'] = paths # this should be created on the fly when UPConfig is created, not stored in the database to allow for flexibility
    
    #connect to the gdb
    GDB = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    arcpy.env.workspace = GDB 
    
    #retrieve values from upc_key table
    rows = arcpy.SearchCursor('upc_key')
    for row in rows:
        UPConfig[row.KeyName]=str(row.KeyValue)
    
    #is there a subarea_bnd in UPConfig...if not set = '' and id = 'up_said'
    #TODO test this
    if not 'Subarea_bnd' in UPConfig.keys():
        UPConfig['Subarea_bnd'] = ''
        UPConfig['Subarea_id'] = ''
        UPConfig['Subarea_search'] = 0
        
    #read in the upc_subareas table
    Subareas= []
    rows = arcpy.SearchCursor('upc_subareas')
    for row in rows:
        SA = {}
        SA['sa']= str(row.getValue('Code'))
        SA['SAName'] = str(row.getValue('Name'))
        Subareas.append(SA)
    UPConfig['Subareas'] = Subareas

    #retrieve values from upc_lu table
    LUCodes = []
    LUNames = {}
    AllocMethods = {}
    LUTypes = {}
    rows = arcpy.SearchCursor('upc_lu', sort_fields = 'Priority A')
    for row in rows:
        LUCode = str(row.getValue('Code'))
        LUName = str(row.getValue('Name'))
        AllocMethod = int(row.getValue('AllocMethod'))
        LUType = str(row.getValue('LUType'))
        
        LUCodes.append(LUCode)
        LUNames[LUCode] = LUName
        AllocMethods[LUCode] = AllocMethod
        LUTypes[LUCode] = LUType
    UPConfig['LUPriority'] = LUCodes
    UPConfig['LUNames'] = LUNames
    UPConfig['AllocMethods'] = AllocMethods
    UPConfig['LUTypes'] = LUTypes

    #everything else is dependent on the timestep, so start a timestep loop
    TimeSteps = []
    TSrows = arcpy.SearchCursor('upc_timesteps', sort_fields = 'TSOrder A') #upc_timesteps, need to enforce order
    for TSrow in TSrows:
        #retrieve values from upc_timesteps table
        TSCode = str(TSrow.getValue('Code'))
        TimeStep = [TSCode,str(TSrow.getValue('Name'))]
        TimeSteps.append(TimeStep)
        
        #Add an empty placeholder for the dictionary that'll be filled for this TimeStep
        UPConfig[TSCode] = {}
        
        #Get the GP layer name and field from upc_timesteps table
        UPConfig[TSCode]['gp'] = [str(TSrow.getValue('GPLayer')), str(TSrow.getValue('GPField'))]
        
        #retrieve values from upc_gplu table
        gplu    = {}
        #get the GP categories by LU
        for x in range(0,len(UPConfig['LUPriority'])):
            LUCode = UPConfig['LUPriority'][x]
            rows = arcpy.SearchCursor('upc_gplu', where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + LUCode + r"'")
            GPCats = []
            for row in rows:
                GPCat = str(row.getValue('GPCat'))
                GPCats.append(GPCat)
            gplu[LUCode] = GPCats
        UPConfig[TSCode]['gplu'] = gplu
        
        #retrieve values from upc_mu table
        mixeduse = {}
        #get LUCodes by GP categories
        for GPCat in unique_values('upc_mu','GPCat'):
            rows = arcpy.SearchCursor('upc_mu', where_clause = r"TSCode = '" + TSCode + r"' AND GPCat = '" + GPCat + r"'")
            LUCodePairs = []
            for row in rows:
#                 LUCodes = str(row.getValue('LUCode'))
#                 LUCodes = LUCodes.replace('-',r"','")
#                 LUCodes = r"'" + LUCodes + r"'"
                LUCodes = str(row.getValue('LUCode')).split('-')
                LUCodePairs.append(LUCodes)
            mixeduse[str(GPCat)] = LUCodePairs
        UPConfig[TSCode]['mixeduse'] = mixeduse
        
        #retrieve values from upc_constraints table
        rows = arcpy.SearchCursor('upc_constraints', where_clause = r"TSCode = '" + TSCode + r"'")
        Constraints = []
        for row in rows:
            Constraints.append(str(row.getValue('Name')))
        UPConfig[TSCode]['constraints'] = Constraints
        
        #retrieve values from upc_cweights table
        cweights = {}
        #get constraints and their weights by land use
        for LUCode in unique_values('upc_cweights','LUCode'):
            rows = arcpy.SearchCursor('upc_cweights', where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + LUCode + r"'")
            WeightByCon = {}
            for row in rows:
                WeightByCon[str(row.getValue('CLayer'))] = row.getValue('Weight')
            cweights[str(LUCode)] = WeightByCon
        UPConfig[TSCode]['cweights'] = cweights
        
        #retrieve values from upc_attractors table
        rows = arcpy.SearchCursor('upc_attractors', where_clause = r"TSCode = '" + TSCode + r"'")
        Attractors = []
        for row in rows:
            Attractors.append(str(row.getValue('Name')))
        UPConfig[TSCode]['attractors'] = Attractors
        
        #retrieve values from upc_demand table
        Demand = {}
        #get acres by SA and LU
        
        for SACode in unique_values('upc_subareas', 'Code'):
            LUDemand = {}
            for LUCode in unique_values('upc_lu','Code'):
                rows = arcpy.SearchCursor('upc_demand',where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + LUCode + r"' AND SACode = '" + SACode + r"'")
                for row in rows:
                    LUDemand[str(LUCode)]=row.getValue('Acres')
            Demand[str(SACode)]=LUDemand
        UPConfig[TSCode]['Demand']=Demand
        
        #retrieve values from upc_aweights table
        aweights = {}
        #get distance and weight by land use and attraction layer        
        for LUCode in UPConfig['LUPriority']:
            WeightByAtt = {}
            for AttLayer in UPConfig[TSCode]['attractors']:
                RowCheck = False
                rows = arcpy.SearchCursor('upc_aweights', 
                                          where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + LUCode + r"' AND AttLayer = '" + AttLayer + r"'",
                                          sort_fields = 'Dist A')
                DistWeights = []
                for row in rows:
                    DistWeights.append([row.getValue('Dist'), row.getValue('Weight')])
                    RowCheck = True
                if not (RowCheck == False):
                    WeightByAtt[AttLayer]=DistWeights
            aweights[LUCode] = WeightByAtt
        UPConfig[TSCode]['aweights']=aweights
        
    UPConfig['TimeSteps'] = TimeSteps
     
    return UPConfig

def LoadUPConfig_python(MultiSA = False,MultiTS = False):
    '''
    Creates a UPConfig dictionary from manual settings entered below.
    
    Arguments:
    MultiSA: Boolean, true indicates that the UPConfig should be a Multiple Subarea Version, False it'll be set up for a single subarea 
    
    Returns:
    UPConfig
    '''
    
    UPConfig = {}
    
    dbpath = r"..\testing" 
    dbname = 'calaveras.gdb'
    paths={'dbpath':dbpath, 'dbname':dbname}
    UPConfig['paths'] = paths # this should be created on the fly when UPConfig is created, not stored in the database to allow for flexibility
    
    UPConfig['BaseGeom_bnd'] = 'pcl_bnd' # Must have an acres field: upc_key
    UPConfig['BaseGeom_cent'] = 'pcl_cent' # upc_key
    UPConfig['BaseGeom_id'] = 'pclid' # upc_key
    UPConfig['Redev'] = 'redev_src' # upc_key, set to None for no redev.
    UPConfig['Redev_pop'] = 'pop' # upc_key
    UPConfig['Redev_emp'] = 'emp' # upc_key
    
    #upc_timesteps, need to enforce order
    if MultiTS:
        TimeSteps = [['ts1','TimeStep 1'],['ts2','TimeStep 2']]
    else:
        TimeSteps = [['ts1','TimeStep 1']]
    
    UPConfig['TimeSteps'] = TimeSteps
    UPConfig['ts1'] = {} # Adding an empty placeholder for the dictionary that'll be filled for TimeStep1
    if MultiTS:
        UPConfig['ts2'] = {}
    
    # Short and long names for the subarea. sa is the short name, and it is the name that should be in the feature class in the subarea field name
    # this first is for a single subarea only one of the two blocks should be used at a time.
    
    if MultiSA:
        # for multiple subareas
        Subareas = [{'sa':'sa1','SAName':'Subarea 1'},{'sa':'sa2','SAName':'Subarea 2'} ] #upc_subareas
        UPConfig['Subareas'] = Subareas # upc_key
        UPConfig['Subarea_bnd'] = 'subareas'# boundary featureclass name # upc_key
        UPConfig['Subarea_id'] = 'sa' # string with the id field for subarea names. # upc_key
        UPConfig['Subarea_search'] = 100 # Set a search radius for matching BaseGeom_cent points to subareas. # upc_key
    else:
        Subareas = [{'sa':'sa1','SAName':'Subarea 1'}] #upc_subareas
        UPConfig['Subareas'] = Subareas # upc_key
        UPConfig['Subarea_bnd'] = ''# boundary featureclass name # upc_key
        UPConfig['Subarea_id'] = 'up_said' # string with the id field for subarea names. # upc_key
        UPConfig['Subarea_search'] = 0 # Set a search radius for matching BaseGeom_cent points to subareas. # upc_key

    LUPriorities= ['ind','ret','ser','rh','rm','rl','rvl'] # upc_lu, enforce order
    UPConfig['LUPriority'] = LUPriorities
    
    #add long names for LU
    LUNames = {}
    LUNames['ind'] = 'Industrial' #upc_lu
    LUNames['ret'] = 'Retail'
    LUNames['ser'] = 'Service'
    LUNames['rh'] = 'Residential High'
    LUNames['rm'] = 'Residential Medium'
    LUNames['rl'] = 'Residential Low'
    LUNames['rvl'] = 'Residential Very Low'
    UPConfig['LUNames'] = LUNames
    
    #Set allocation methods
    # 1 = Normal
    # 2 = Random
    # 3 = Weighted Random
    AllocMethods = {}
    AllocMethods['ind'] = 1 #upc_lu
    AllocMethods['ret'] = 1 #
    AllocMethods['ser'] = 1
    AllocMethods['rh'] = 1
    AllocMethods['rm'] = 1
    AllocMethods['rl'] = 1
    AllocMethods['rvl'] = 2 
    UPConfig['AllocMethods'] = AllocMethods
    
    #Set LUType
    LUTypes = {}
    LUTypes['ind'] = 'emp'
    LUTypes['ret'] = 'emp' 
    LUTypes['ser'] = 'emp'
    LUTypes['rh'] = 'res'
    LUTypes['rm'] = 'res'
    LUTypes['rl'] = 'res'
    LUTypes['rvl'] = 'res'
    UPConfig['LUTypes'] = LUTypes
    
    # Set the distance calculation mode
    # options 'GenerateNear', 'RasterEuc'
    UPConfig['DistMode'] = 'GenerateNear' #upc_key
    

    UPConfig['ts1']['Demand'] = {}
    Demand = {} 
    d_ind = 40
    d_ret = 80
    d_ser = 100
    d_rh  = 42
    d_rm  = 2000
    d_rl  = 3000
    d_rvl = 25000
    
    
    Demand['ind'] = d_ind
    Demand['ret'] = d_ret
    Demand['ser'] = d_ser
    Demand['rh'] = d_rh
    Demand['rm'] = d_rm
    Demand['rl'] = d_rl
    Demand['rvl'] = d_rvl
    UPConfig['ts1']['Demand']['sa1'] = Demand #upc_demand by ts, sa
       
    
    # Added data for a second subarea
    if MultiSA:
        Demand = {} 
        d_ind = 3
        d_ret = 10
        d_ser = 100
        d_rh  = 5
        d_rm  = 20
        d_rl  = 100
        d_rvl = 500
        
        Demand['ind'] = d_ind
        Demand['ret'] = d_ret
        Demand['ser'] = d_ser
        Demand['rh'] = d_rh
        Demand['rm'] = d_rm
        Demand['rl'] = d_rl
        Demand['rvl'] = d_rvl
        UPConfig['ts1']['Demand']['sa2'] = Demand #upc_demand by ts, sa
    
    if MultiTS:
        UPConfig['ts2']['Demand'] = {}
        Demand = {} 
        d_ind = 40
        d_ret = 80
        d_ser = 100
        d_rh  = 42
        d_rm  = 2000
        d_rl  = 3000
        d_rvl = 25000
        
        
        Demand['ind'] = d_ind
        Demand['ret'] = d_ret
        Demand['ser'] = d_ser
        Demand['rh'] = d_rh
        Demand['rm'] = d_rm
        Demand['rl'] = d_rl
        Demand['rvl'] = d_rvl
        UPConfig['ts2']['Demand']['sa1'] = Demand #upc_demand by ts, sa
           
        
        # Added data for a second subarea
        if MultiSA:
            Demand = {} 
            d_ind = 3
            d_ret = 10
            d_ser = 100
            d_rh  = 5
            d_rm  = 20
            d_rl  = 100
            d_rvl = 500
            
            Demand['ind'] = d_ind
            Demand['ret'] = d_ret
            Demand['ser'] = d_ser
            Demand['rh'] = d_rh
            Demand['rm'] = d_rm
            Demand['rl'] = d_rl
            Demand['rvl'] = d_rvl
            UPConfig['ts2']['Demand']['sa2'] = Demand #upc_demand by ts, sa
        
    
        
    
               
    # General Plan Settings
    UPConfig['ts1']['gp'] = ['gp','gp_class'] #upc_gp by ts
    if MultiTS:
        UPConfig['ts2']['gp'] = ['gp','gp_class']
    
    
    gplu    = {}
    gp_ind  = ['I','PD-I']
    gp_ret  = ['Commercial','Commercial - Recreation',r'PS/SC','SC','CC',r'CC/H','PD',r'R1/SC','C-PD','CCH','CCL','CCR','CO','CR']
    gp_ser  = ['Commercial','Commercial - Recreation',r'PS/SC','SC','CC',r'CC/H','PD',r'R1/SC','C-PD','CCH','CCL','CCR','CO','CR','PI']
    gp_rh   = ['Residential - Medium - 6,000 sq ft','Residential - Low - 14,500 sq ft','R3','R3-PD','CC',r'CC/H','PD','CCR','RHD']
    gp_rm   = ['Residential - Low - 14,500 sq ft','Residential - Low - 21,800','Residential - Low - 21,800 sq ft','Residential - Low - 1 acre',
              'Residential - Rural - 2 acres','Residential - Rural - 5 acres','Residential - Agricultural',
              'R3','R3-PD','R1','R1-PD','R2',r'RA/R1',r'R1/SC','C-PD','CCH','CCL','CCR','RHD','RMD','RLD','RH']
    gp_rl   = ['Residential - Low - 1 acre','Residential - Rural - 2 acres','Residential - Rural - 5 acres','Residential - Agricultural','PD',r'RA/R1','CCH','CCR','RH','RR']
    gp_rvl  = ['Mineral Resource','Agricultural Lands','Biological Resource',r'RA/R1','RA','WL','RP','RM','RTA','RTB']
    
    gplu['ind'] = gp_ind
    gplu['ret'] = gp_ret
    gplu['ser'] = gp_ser
    gplu['rh']  = gp_rh
    gplu['rm']  = gp_rm
    gplu['rl']  = gp_rl
    gplu['rvl'] = gp_rvl
    UPConfig['ts1']['gplu'] = gplu #up_gplu by ts, lu
    if MultiTS:
        UPConfig['ts2']['gplu'] = gplu
    
    
    mixeduse = {}
    mixeduse['CC'] = [['ret','rh'],['ret','ser'],['ser','rh'],['ret','ser','rh']]
    mixeduse[r'CC/H'] = [['ret','rh'],['ret','ser'],['ser','rh'],['ret','ser','rh']]
    mixeduse['PD'] = [['ret','rh'],['ret','ser'],['ser','rh'],['ret','ser','rh']]
    mixeduse['CCR'] = [['ret','rh'],['ret','ser'],['ser','rh'],['ret','ser','rh']]
    UPConfig['ts1']['mixeduse'] = mixeduse # upc_mu by ts
    if MultiTS:
        UPConfig['ts2']['mixeduse'] = mixeduse
    
    # Constraints
    con_list = ['undevelopable','low_gw','vpools'] 
    UPConfig['ts1']['constraints'] = con_list # upc_constraints, by ts
    if MultiTS:
        UPConfig['ts2']['constraints'] = con_list
        
        
    con_ind = {"undevelopable":1,"low_gw":1,"vpools":0.5}
    con_ret = {"undevelopable":1,"low_gw":1,"vpools":0.5}
    con_ser = {"undevelopable":1,"low_gw":1,"vpools":0.5}
    con_rh  = {"undevelopable":1,"low_gw":0,"vpools":0.5}
    con_rm  = {"undevelopable":1,"low_gw":0.25,"vpools":0.5}
    con_rl  = {"undevelopable":1,"low_gw":0.25,"vpools":0.5}
    con_rvl = {"undevelopable":1,"low_gw":0.25,"vpools":0.1}
        
    # Build Constraints Dictionary
    constraints = {}
    constraints['ind'] = con_ind
    constraints['ret'] = con_ret
    constraints['ser'] = con_ser
    constraints['rh']  = con_rh
    constraints['rm']  = con_rm
    constraints['rl']  = con_rl
    constraints['rvl'] = con_rvl

    UPConfig['ts1']['cweights'] = constraints #upc_cweights, by ts, lu
    if MultiTS:
        UPConfig['ts2']['cweights'] = constraints

    
    # Attractions
    attractors = ['rds_shwy','rds_main','cp_tc','angels_bnd']
    UPConfig['ts1']['attractors'] = attractors #upc_attractors by ts
    if MultiTS:
        UPConfig['ts2']['attractors'] = attractors
    
    att_ind = {'rds_shwy':[[0,20],[500,10],[10000,0]],'rds_main':[[0,15],[500,5],[5000,0]],'cp_tc':[[0,25],[1000,0]],'angels_bnd':[[0,30],[1000,0]]}
    att_ret  = {'rds_shwy':[[0,25],[100,10],[10000,0]],'rds_main':[[0,15],[500,5],[5000,0]],'cp_tc':[[0,25],[1000,0]],'angels_bnd':[[0,30],[1000,0]]}
    att_ser  = {'rds_shwy':[[0,25],[200,10],[10000,0]],'rds_main':[[0,15],[500,5],[5000,0]],'cp_tc':[[0,25],[1000,0]],'angels_bnd':[[0,30],[1000,0]]}
    att_rh  = {'rds_shwy':[[0,20],[200,10],[10000,0]],'rds_main':[[0,15],[500,5],[5000,0]],'cp_tc':[[0,25],[1000,0]],'angels_bnd':[[0,30],[1000,0]]}
    att_rm  = {'rds_shwy':[[0,20],[1000,10],[10000,0]],'rds_main':[[0,15],[1000,10],[10000,0]],'cp_tc':[[0,25],[1000,0]],'angels_bnd':[[0,30],[1000,0]]}
    att_rl  = {'rds_shwy':[[0,10],[25000,0]],'rds_main':[[0,10],[25000,0]],'cp_tc':[[0,0]],'angels_bnd':[[0,0]]}
    att_rvl = {'rds_shwy':[[0,5],[50000,0]],'rds_main':[[0,10],[25000,0]],'cp_tc':[[0,0]],'angels_bnd':[[0,0]]}
    
    att_weights = {}
    att_weights['ind'] = att_ind
    att_weights['ret'] = att_ret
    att_weights['ser'] = att_ser
    att_weights['rh']  = att_rh
    att_weights['rm']  = att_rm
    att_weights['rl']  = att_rl
    att_weights['rvl'] = att_rvl
    UPConfig['ts1']['aweights'] = att_weights #upc_aweights by ts,lu
    if MultiTS:
        UPConfig['ts2']['aweights'] = att_weights
    
    return UPConfig

def MakeNewRunGDB(dbpath, dbname):
    '''
    Create new run file geodatabase and create the empty configuration tables.
    
    Arguments:
    dbpath: the path at which to create the geodatabase
    dbname: the name of the run database
    '''
    
    # create geodatabase
    Logger("Creating File Geodatabase")
    try:
        arcpy.CreateFileGDB_management(dbpath,dbname)
        arcpy.env.workspace = os.path.join(dbpath, dbname)
    except Exception, e:
        Logger(str(e))
        raise
        
    
    
    Logger("Creating Tables")
    # Key value table
    
    
    
    
    Logger("Done")
    
def dict_compare(d1, d2):
    '''
    Compares 2 dictionaries
    Source: http://stackoverflow.com/questions/4527942/comparing-two-dictionaries-in-python
    
    Called by:
    
    Arguments:
    d1: a dictionary
    d2: a dictionary you want to compare to d1
    
    Returns:
    added - keys and values that d2 has that d1 doesn't
    removed - keys and values that d1 has that d2 doesn't
    modified - keys that match in d1 and d2, but have different values
    same - keys that have the same values in d1 and d2
    '''

    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o : (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    return added, removed, modified, same

if __name__ == "__main__":
#     dbpath = r"..\testing\TestAllocation" 
#     dbname = 'AllocTest.gdb'
    
    #dbpath = r"G:\Public\UPLAN\HumboldtUPlan"
    #dbname = 'humboldt_run1.gdb'
    
    dbpath = r"G:\Public\UPLAN\Uplan4\testing"
    dbname = "calaveras_template.gdb"
    
#     print("Loading UPConfig from Python")
#     UPConfig = LoadUPConfig_python(True,True)
#     print("Writing UPConfig to tables")
#     WriteUPConfigToGDB(UPConfig)

#     WriteUPCLayers(UPConfig)
#     print("Reading upc_* tables to UPConfig")
    UPConfig2 = ReadUPConfigFromGDB(dbpath,dbname)
    print(UPConfig2)
#     WriteUPConfigToGDB(UPConfig2)
#     print("Pickle UPConfig")
#     picklefile = os.path.join(dbpath,dbname,"UPConfig.p")
#     UPConfig = uiut.LoadPickle(picklefile)
#     print(UPConfig)
    #pickle.dump(UPConfig2, open(picklefile, "wb"))

#     AllTSCodes = [ts[0] for ts in UPConfig2['TimeSteps']]
#     print(AllTSCodes)
    
    

#     InWorkspace = os.path.join(dbpath,dbname)
#     EmptyOrCreateUPCTables(InWorkspace)
#     print(UPConfig)

#     print(UPConfig2)  

    print arcpy.ProductInfo()
    
    print("script finished")
    