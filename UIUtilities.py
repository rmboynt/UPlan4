'''
Created on Jun 9, 2015

@author: roth
'''

import arcpy
import os
import cPickle as pickle
import Utilities
import UPConfig as upc

def CheckForPickle(path):
    return os.path.isfile(path)

def TimestepNameLookup(UPConfig):
    #returns a list of timestep names
    TSNames = []
    Timesteps = UPConfig['TimeSteps']
    for Timestep in Timesteps:
        TSNames.append(Timestep[1])
    return(TSNames)

def TimestepCodeLookup(TSName,UPConfig):
    #returns the timestep code for the given timestep name
    Timesteps = UPConfig['TimeSteps']
    for Timestep in Timesteps:
        if Timestep[1] == TSName:
            TSCode = Timestep[0]
    return(TSCode)

def LUNameLookup(UPConfig):
    #returns a list of land use names
    LUNames = []
    #LUNameLU = UPConfig['LUNames']
    LUCodes = UPConfig['LUPriority']
    for LUCode in LUCodes:
        LUNames.append(UPConfig['LUNames'][LUCode])
    return(LUNames)
        
def LUCodeLookup(LUName,UPConfig):
    #returns the Land Use Code for the given Land Use Name
    LUNames = UPConfig['LUNames']
    for LUCode in LUNames.keys():
        if LUNames[LUCode] == LUName:
            return(LUCode)

def GetDescNameFromLayersTable(FCName,Role,UPGDB):
    #returns the descriptive name for the given layer name
    arcpy.env.workspace = UPGDB
    rows = arcpy.SearchCursor('upc_layers', where_clause = r"FCName = '" + FCName + r"' AND Role = '" + Role + r"'")
    row = rows.next()
    DescName = row.getValue('LongName')
    return(DescName)

def GetLayerNameFromLayersTable(DescName,Role,UPGDB):
    #returns the layer name for the given descriptive name
    arcpy.env.workspace = UPGDB
    rows = arcpy.SearchCursor('upc_layers', where_clause = r"LongName = '" + DescName + r"' AND Role = '" + Role + r"'")
    row = rows.next()
    FCName = row.getValue('FCName')
    return(FCName)
         
def AttractorNameLookup(UPConfig,TSCode,UPGDB):
    #returns a list of attractor layer descriptive names
    AttLayers = UPConfig[TSCode]['attractors']
    DescNames = []
    for AttLayer in AttLayers:
        DescNames.append(GetDescNameFromLayersTable(AttLayer,'Attractor',UPGDB))
    return(DescNames)

def ConstraintNameLookup(UPConfig,TSCode,UPGDB):
    #returns a list of constraint layer descriptive names
    ConLayers = UPConfig[TSCode]['constraints']     
    DescNames = []
    for ConLayer in ConLayers:
        DescNames.append(GetDescNameFromLayersTable(ConLayer,'Constraint',UPGDB))
    return(DescNames)

def SplitPath(path):
    dbpath = path[:path.rfind("\\")]
    dbname = path[(path.rfind("\\")+1):]
    return([dbpath,dbname])

def JoinPath(dbpath,dbname):
    dbfullpath = os.path.join(dbpath,dbname)
    return(dbfullpath)

def LoadPickle(path):
    #updates the path information in UPConfig in case it has moved. 
    fulldb = path[:path.rfind("\\")]
    dbpath = fulldb[:fulldb.rfind("\\")]
    dbname = fulldb[(fulldb.rfind("\\")+1):]
    UPConfig = pickle.load( open(path, "rb"))
    UPConfig['paths']['dbpath'] = dbpath
    UPConfig['paths']['dbname'] = dbname
    return(UPConfig)
    
def LoadDemandPickle(path):
    #updates the path information in UPConfig in case it has moved. 
#     fulldb = path[:path.rfind("\\")]
#     dbpath = fulldb[:fulldb.rfind("\\")]
#     dbname = fulldb[(fulldb.rfind("\\")+1):]
    UPDemand = pickle.load( open(path, "rb"))
#     UPConfig['paths']['dbpath'] = dbpath
#     UPConfig['paths']['dbname'] = dbname
    return(UPDemand)
    
def MakePickle(UPConfig, path):
    picklepath = os.path.join(path,"UPConfig.p")
    picklebackuppath = os.path.join(path,"UPConfig_backup.p")
    if CheckForPickle(picklepath):
        #make a backup
        if CheckForPickle(picklebackuppath):
            #delete the backup
            os.remove(picklebackuppath)
        #rename the current pickle to the backup name
        os.rename(picklepath,picklebackuppath)
    pickle.dump(UPConfig, open(picklepath, "wb"))
    return

def MakeDemandPickle(UPDemand, path):
    picklepath = os.path.join(path,"UPDemand.p")
    pickle.dump(UPDemand, open(picklepath, "wb"))
    return

def InsertToList(lst,item,position):
    return(lst[:(position-1)] + [item] + lst[(position-1):])
    
def MakeEmptyTimeStep():
    ts = {}
    ts['gp'] = []
    ts['Demand'] = {}
    ts['gplu'] = {}
    ts['mixeduse'] = {}
    ts['constraints'] = []
    ts['cweights'] = {}
    ts['attractors'] = []
    ts['aweights'] = {}
    return(ts)

def MakeTemplateTimeStep(GPLayer,GPField):
    ts = {}
    ts['gp'] = [GPLayer,GPField]
    ts['Demand'] = {}
    ts['gplu'] = {}
    ts['mixeduse'] = {}
    ts['constraints'] = []
    ts['cweights'] = {}
    ts['attractors'] = []
    ts['aweights'] = {}
    return(ts)

def MakeEmptyUPDemand(UPGDB):
    arcpy.env.workspace = UPGDB
    UPDemand = {}
    #get a list of timesteps
    picklepath = "\\".join([UPGDB,"UPConfig.p"])
    UPConfig = LoadPickle(picklepath)
    for Timestep in UPConfig['TimeSteps']:
        TSCode = Timestep[0]
        UPDemand[TSCode] = CreateUPDemandForTS(UPGDB,TSCode,UPDemand)
#         UPDemand[TSCode] = {}
#         UPDemand[TSCode]['ResCalcs'] = {}
#         UPDemand[TSCode]['TotalsBySA'] = {}
#         UPDemand[TSCode]['PctResBySA'] = {}
#         UPDemand[TSCode]['OccUnitsBySA'] = {}
#         UPDemand[TSCode]['EmpCalcs'] = {}
#         UPDemand[TSCode]['ResAcresBySA'] = {}
#         UPDemand[TSCode]['PctEmpBySA'] = {}
#         UPDemand[TSCode]['EPHH'] = 0
#         UPDemand[TSCode]['PPHH'] = 0 
#         UPDemand[TSCode]['EndPop'] = 0
#         UPDemand[TSCode]['EmpAcresBySA'] = {}
#         UPDemand[TSCode]['PopChange'] = 0
#         UPDemand[TSCode]['StartPop'] = 0
#         UPDemand[TSCode]['NumEmpBySA'] = {}
#         UPDemand[TSCode]['ResLandUses'] = {}
#         #loop over residential land uses
#         ResLURows = arcpy.SearchCursor('upc_lu',where_clause = r"LUType = 'res'")
#         for ResLURow in ResLURows:
#             LUCode = ResLURow.getValue('Code')
#             UPDemand[TSCode]['ResLandUses'][LUCode] = {}
#             UPDemand[TSCode]['ResLandUses'][LUCode]['AcPerUnit'] = 0
#             UPDemand[TSCode]['ResLandUses'][LUCode]['PctVacantUnits'] = 0
#             UPDemand[TSCode]['ResLandUses'][LUCode]['PctOther'] = 0
         
    return(UPDemand)

def CreateUPDemandForTS(UPGDB,TSCode,UPDemand):
    TSDemand = {}
    TSDemand['ResCalcs'] = {}
    TSDemand['TotalsBySA'] = {}
    TSDemand['PctResBySA'] = {}
    TSDemand['OccUnitsBySA'] = {}
    TSDemand['EmpCalcs'] = {}
    TSDemand['ResAcresBySA'] = {}
    TSDemand['PctEmpBySA'] = {}
    TSDemand['EPHH'] = 0
    TSDemand['PPHH'] = 0 
    TSDemand['EndPop'] = 0
    TSDemand['EmpAcresBySA'] = {}
    TSDemand['PopChange'] = 0
    TSDemand['StartPop'] = 0
    TSDemand['NumEmpBySA'] = {}
    
    TSDemand['ResLandUses'] = {}
    #loop over residential land uses
    ResLURows = arcpy.SearchCursor('upc_lu',where_clause = r"LUType = 'res'")
    for ResLURow in ResLURows:
        LUCode = ResLURow.getValue('Code')
        TSDemand['ResLandUses'][LUCode] = {}
        TSDemand['ResLandUses'][LUCode]['AcPerUnit'] = 0
        TSDemand['ResLandUses'][LUCode]['PctVacantUnits'] = 0
        TSDemand['ResLandUses'][LUCode]['PctOther'] = 0
    
    TSDemand['EmpLandUses'] = {}
    #loop over employment land uses
    EmpLURows = arcpy.SearchCursor('upc_lu',where_clause = r"LUType = 'emp'")
    for ResLURow in EmpLURows:
        LUCode = ResLURow.getValue('Code')
        TSDemand['EmpLandUses'][LUCode] = {}
        TSDemand['EmpLandUses'][LUCode]['SFPerEmp'] = 0
        TSDemand['EmpLandUses'][LUCode]['FAR'] = 0
        TSDemand['EmpLandUses'][LUCode]['PctOther'] = 0
    
    return(TSDemand)

def CheckIfFGDB(path):
    desc = arcpy.Describe(path)
    if desc.workspaceFactoryProgID == "esriDataSourcesGDB.FileGDBWorkspaceFactory.1":
        return(True)
    else:
        return(False)

def CheckIfTSInFGDB(path,ts):
    #returns true if the TSCode already exists
    #based off TomAdair's response on stackoverflow, http://stackoverflow.com/questions/31559275/how-do-i-check-if-my-search-cursor-is-empty-in-arcpy
    whereClause = "Code = '{ts}'".format(ts = ts)
    i = 0
    with arcpy.da.SearchCursor(os.path.join(path,"upc_timesteps"),'Code',whereClause) as cursor:
        for row in cursor:
            i += 1

    if i == 0:
        return(False)
    else:
        return(True)

def CreateDefaultKeys(InDB):
    #add default keys to the upc_key table
    fields = ['KeyName','KeyValue']
    cur = arcpy.da.InsertCursor(os.path.join(InDB,'upc_key'),fields)
    
    cur.insertRow(('BaseGeom_bnd','add a base geometry'))
    cur.insertRow(('BaseGeom_cent','add a base geometry'))
    cur.insertRow(('BaseGeom_id','add a base geometry'))
#     cur.insertRow(('Subarea_bnd',UPConfig['Subarea_bnd']))
#     cur.insertRow(('Subarea_id',UPConfig['Subarea_id']))
#     cur.insertRow(('Subarea_search',UPConfig['Subarea_search']))
    if arcpy.ProductInfo() == 'ArcInfo':
        cur.insertRow(('DistMode','GenerateNear'))
    else:
        cur.insertRow(('DistMode','RasterEuc'))
#     if 'Redev' in UPConfig.keys():
#         cur.insertRow(('Redev',UPConfig['Redev']))
#         cur.insertRow(('Redev_pop',UPConfig['Redev_pop']))
#         cur.insertRow(('Redev_emp',UPConfig['Redev_emp']))
    del cur
    
def ReturnValuesFromLayersTable(InDB,Role):
    fields = ['FCName','LongName','DateAdded','Role']
    OutValues = []
    rows = arcpy.SearchCursor(os.path.join(InDB,'upc_layers'),where_clause = r"Role = '" + Role + r"'", sort_fields = 'DateAdded D')
    for row in rows:
        FCName = str(row.getValue('FCName'))
        FCLongName = str(row.getValue('LongName'))
        DateAdded = str(row.getValue('DateAdded'))
        OutValues.append(FCName + ' (' + FCLongName + ') Added: ' + DateAdded)
    return(OutValues)

def ReturnFieldListFromFC(InDB,FCName):
    OutValues = []
    InFC = os.path.join(InDB,FCName)
    Fields = arcpy.ListFields(InFC)
    for Field in Fields:
        OutValues.append(Field.name)
    return(OutValues)

def ReturnFieldListFromFC2(InFC):
    #same as ReturnFieldListFromFC, but the layer doesn't need to be in the UPGDB
    OutValues = []
    Fields = arcpy.ListFields(InFC)
    for Field in Fields:
        OutValues.append(Field.name)
    return(OutValues)

def ListUniqueFieldValues(table, field):
    #This function can be used to return a unique list of field values
    #source: https://arcpy.wordpress.com/2012/02/01/create-a-list-of-unique-field-values/
    with arcpy.da.SearchCursor(table, [field]) as cursor:
        return sorted({row[0] for row in cursor})
    
def LinkMUCodes(UPConfig, LUCodes):
    LUCodes2 = Utilities.OrderLU(UPConfig,LUCodes)
    LUCodes3=''
    for y in range(0,len(LUCodes2)):
        if not y == len(LUCodes2)-1:
            LUCodes3 = LUCodes3 + LUCodes2[y] + '-'
        else:
            LUCodes3 = LUCodes3 + LUCodes2[y]
    return LUCodes3

def ChangeDistMode(UPConfig):
    UPConfig['DistMode'] = 'RasterEuc'
    upc.WriteUPConfigToGDB(UPConfig)
    return UPConfig
    
#testing
if __name__ == "__main__":
    dbpath = r"..\testing\TestAllocation" 
    dbname = 'AllocTest.gdb' 
    fullpath = os.path.join(dbpath,dbname)
#     fullpath = r"G:\Public\UPLAN\HumboldtUPlan\humboldt_run1.gdb"
    
    if CheckIfTSInFGDB(fullpath,'ts1'):
        print('timestep code already exists')
    else:
        print('new ts code')
    
    #dpicklepath = "\\".join([fullpath,"UPDemand.p"])
    #UPDemand = LoadDemandPickle(dpicklepath)
    #UPDemand = MakeEmptyUPDemand(fullpath)
    #print (UPDemand)
    