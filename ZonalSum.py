'''
Created Jan-Feb, 2016
@author: rmboynton

This is a tool that will allow the user to get summaries of UPlan allocation
by input zonal dataset (or TAZ)
'''
import arcpy
from arcpy import env
import os
from UPConfig import ReadUPConfigFromGDB
import UIUtilities as uiut

def CreateXwalkTable(UPConfig,ZonalDataset,ZoneField,MaxDist):
    ##Makes a Xwalk table between zone ID and BaseGeom ID
    #set the workspace
    UPGDB = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    env.workspace = UPGDB
    env.overwriteOutput = True
    
    ##create a crosswalk table between zones and BaseGeomIDs
    #join base geom centroids to zonal layer
    arcpy.SpatialJoin_analysis(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],UPConfig['BaseGeom_cent']),os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],ZonalDataset),"in_memory/intersect","JOIN_ONE_TO_ONE","KEEP_ALL","","CLOSEST",MaxDist)
    
    #create XWalk table
    if arcpy.Exists('upa_ZoneXWalk'):
        arcpy.Delete_management('upa_ZoneXWalk')
    arcpy.TableToTable_conversion('in_memory/intersect',UPGDB,'upa_ZoneXWalk')
    
    #delete unneeded fields
    BaseGeomID = UPConfig['BaseGeom_id']
    Fields = arcpy.ListFields("upa_ZoneXWalk")
    FieldList = []
    for Field in Fields:
        if not Field.required:
            if not (Field.name == BaseGeomID or Field.name == ZoneField):
                FieldList.append(Field.name)
    arcpy.DeleteField_management("upa_ZoneXWalk",FieldList)
    
def CreateSummaryTable(UPConfig,AllocType,TSCode,ZoneField):    
    #AllocType = 'cum' if cumulative, 'ts' if just that timestep
    
    #set the workspace
    UPGDB = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    env.workspace = UPGDB
    env.overwriteOutput = True
    env.qualifiedFieldNames = False
    
    #load demand pickle
    dpicklepath = "\\".join([UPGDB,"UPDemand.p"])
    UPDemand = uiut.LoadDemandPickle(dpicklepath)
    print(UPDemand)
    
    AllocTable = 'upo_' + AllocType + '_alloc_' + TSCode
    
    #join alloc table to xwalk table
    TableViewName = 'AllocTable_TView'
    arcpy.MakeTableView_management(AllocTable,TableViewName)
    BaseGeomID = UPConfig['BaseGeom_id']
    arcpy.AddJoin_management(TableViewName ,BaseGeomID, 'upa_ZoneXWalk',BaseGeomID)
    
#     #for debug
#     arcpy.CopyRows_management(TableViewName,r'G:\Public\UPLAN\Uplan4\testing\ryan_test.gdb\JoinTable')
    
    ##get the sum of acres by land use type and ZoneID
    #get list of fields to summarize
    AllocFields = arcpy.ListFields(TableViewName, '*alloc_ac*')
    SumFields = []
    for AllocField in AllocFields:
        SumFields.append([AllocField.name,'SUM'])
    print(SumFields)
    
    ZoneFieldName2 = 'upa_ZoneXWalk.' + ZoneField
    OutSumTableName = 'upa_sum_' + AllocType + '_alloc_' + TSCode
    arcpy.Statistics_analysis(TableViewName,OutSumTableName,SumFields,ZoneFieldName2)
    
    ##add fields for #emp, #people, #households by LU type and populate them
    #GetLUCodes by type
    AllLUCodes = UPConfig['LUPriority']
    ResLUCodes = []
    EmpLUCodes = []
    for LUCode in AllLUCodes:
        if UPConfig['LUTypes'][LUCode] == 'res':
            ResLUCodes.append(LUCode)
        else:
            EmpLUCodes.append(LUCode)
    
    #start with res types
    for ResLUCode in ResLUCodes:
        #add fields
        NumPeopleField = 'alloc_pp_' + ResLUCode
        NumHHField = 'alloc_hh_' + ResLUCode 
        arcpy.AddField_management(OutSumTableName,NumPeopleField,'DOUBLE')
        arcpy.AddField_management(OutSumTableName,NumHHField,'DOUBLE')
        
        #calculate fields
        AcrePerOccUnit = UPDemand[TSCode]['ResCalcs'][ResLUCode]['GrossAcrePerOccUnit']
        PPHH = UPDemand[TSCode]['PPHH']
        FieldWithAcres = 'alloc_ac_' + ResLUCode
        
        arcpy.CalculateField_management(OutSumTableName,NumHHField,'!' + FieldWithAcres + '!/'+str(AcrePerOccUnit),"PYTHON_9.3")
        arcpy.CalculateField_management(OutSumTableName,NumPeopleField,'!'+NumHHField+'!*'+str(PPHH),"PYTHON_9.3")
    
    #now emp types
    for EmpLUCode in EmpLUCodes:
        #add field
        NumEmpField = 'alloc_emp_' + EmpLUCode
        arcpy.AddField_management(OutSumTableName,NumEmpField,'DOUBLE')
        
        #calculate field
        AcrePerEmp = UPDemand[TSCode]['EmpCalcs'][EmpLUCode]['GrossAcrePerEmp']
        FieldWithAcres = 'alloc_ac_' + EmpLUCode
        arcpy.CalculateField_management(OutSumTableName,NumEmpField,'!' + FieldWithAcres + '!/'+str(AcrePerEmp),"PYTHON_9.3")

if __name__ == "__main__":
    dbpath = r'G:\Public\UPLAN\HumboldtUPlan'
    dbname = 'humboldt_run1.gdb'
    ZonalDataset = r'G:\Public\UPLAN\HumboldtUPlan\humboldt_run1.gdb\SumZones'
    ZoneField = 'ZoneID'
    
    UPConfig = ReadUPConfigFromGDB(dbpath,dbname)
    print(UPConfig)
     
#     #create xwalk table
#     CreateXwalkTable(UPConfig,ZonalDataset,ZoneField)

    #create summary table
    AllocType = 'cum'
    TSCode = 'ts1'
    CreateSummaryTable(UPConfig,AllocType,TSCode,ZoneField)
    
print('script finished!!')