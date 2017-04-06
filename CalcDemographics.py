'''
Created on April 22, 2015

@author: boynton
'''
import arcpy
import os
from Utilities import Logger
#from GenerateServiceAreas import whereClause
import UPConfig as upc
import UIUtilities as uiut

def CreateOrEmptyTable(db,TableName,Fields,FieldTypes, TSCode):
    '''
    If the given table doesn't exist, this function will create the table.
    If the given table does exist, all rows will be removed for the given timestep
    
    Called by: CalculateDemand
    
    Arguments:
    db: full path to the uplan file geodatabase
    TableName: The name of the table
    Fields: A list containing the field names
    FieldTypes: A Dictionary that defines the field types by the field names
    TSCode = Timestep Code
    
    '''
    arcpy.env.workspace = db
        
    if not arcpy.Exists(TableName):
        #create the table
        Logger("Creating Table: " + TableName)
        arcpy.CreateTable_management(db, TableName)
        #add the field(s)
        for Field in Fields:
            arcpy.AddField_management(TableName,Field,FieldTypes[Field])
    else:
        #erase the rows for the given timestep
        Logger("Emptying Table: " + TableName + " for Timestep: " + TSCode)
        
        tempTableView = TableName + "TableView"
        if arcpy.Exists(tempTableView):
            arcpy.Delete_management(tempTableView)
        arcpy.MakeTableView_management(TableName, tempTableView)
        arcpy.SelectLayerByAttribute_management(tempTableView, 'NEW_SELECTION', r"TSCode = '" + TSCode + r"'")
        if int(arcpy.GetCount_management(tempTableView).getOutput(0)) > 0:
            arcpy.DeleteRows_management(tempTableView)

def ReadUPDemandFromGDB(UPlanGDB):
    arcpy.env.workspace = UPlanGDB
    #a dictionary that will store the demand values
    UPDemand = {}
    
    if not arcpy.Exists('upd_demographics'):
        return UPDemand
    
    #create 2 lists for land uses, one for res and one for emp
    ResLUCodes=[]
    ResTypeRows = arcpy.SearchCursor('upc_lu', where_clause = r"LUType = 'res'")
    for ResTypeRow in ResTypeRows:
        LUCode = ResTypeRow.getValue('Code')
        ResLUCodes.append(LUCode)
    EmpLUCodes = []
    EmpTypeRows = arcpy.SearchCursor('upc_lu', where_clause = r"LUType = 'emp'")
    for EmpTypeRow in EmpTypeRows:
        LUCode = EmpTypeRow.getValue('Code')
        EmpLUCodes.append(LUCode)
    AllLUCodes = ResLUCodes + EmpLUCodes
    
    #create a list for subareas
    AllSAs = []
    SARows = arcpy.SearchCursor('upc_subareas')
    for SARow in SARows:
        SACode = SARow.getValue('Code')
        AllSAs.append(SACode)
    
    #loop over the timestep(s)
    TSrows = arcpy.SearchCursor('upc_timesteps', sort_fields = 'TSOrder A')
    for TSrow in TSrows:
        TSCode = TSrow.getValue('Code')
        
        #Add an empty placeholder for the dictionary that'll be filled for this TimeStep
        UPDemand[TSCode] = {}
        
        #retrieve values from upd_demographics table
        rows = arcpy.SearchCursor('upd_demographics', where_clause = r"TSCode = '" + TSCode + r"'")
        for row in rows:
            UPDemand[TSCode]['PopChange'] = row.getValue('PopChange')
            UPDemand[TSCode]['StartPop'] = row.getValue('StartPop')
            UPDemand[TSCode]['EndPop'] = row.getValue('EndPop')
            UPDemand[TSCode]['PPHH'] = row.getValue('PPHH')
            UPDemand[TSCode]['EPHH'] = row.getValue('EPHH')
    
        #retrieve values from upd_reslanduses table
        #if no record in upd_reslanduses, create one with all 0s
        ResLUs = {}
        if arcpy.Exists('upd_reslanduses'):
            for ResLUCode in ResLUCodes:
                ResLURows = arcpy.SearchCursor('upd_reslanduses', where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + ResLUCode + r"'")
                ResLURow = ResLURows.next()
                if not ResLURow == None:
                    AcPerUnit = ResLURow.getValue('AcPerUnit')
                    PctVacantUnits = ResLURow.getValue('PctVacantUnits')
                    PctOther = ResLURow.getValue('PctOther')
                    
                    ResValues = {}
                    ResValues['AcPerUnit'] = AcPerUnit
                    ResValues['PctVacantUnits'] = PctVacantUnits
                    ResValues['PctOther'] = PctOther
                    ResLUs[ResLUCode] = ResValues
                else:
                    ResValues = {}
                    ResValues['AcPerUnit'] = 0
                    ResValues['PctVacantUnits'] = 0
                    ResValues['PctOther'] = 0
                    ResLUs[ResLUCode] = ResValues
        else:
            for ResLUCode in ResLUCodes:
                ResValues = {}
                ResValues['AcPerUnit'] = 0
                ResValues['PctVacantUnits'] = 0
                ResValues['PctOther'] = 0
                ResLUs[ResLUCode] = ResValues
        UPDemand[TSCode]['ResLandUses'] = ResLUs
            
        #retrieve values from upd_emplanduses table
        EmpLUs = {}
        if arcpy.Exists('upd_emplanduses'):
            for EmpLUCode in EmpLUCodes:
                EmpLURows = arcpy.SearchCursor('upd_emplanduses', where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + EmpLUCode + r"'")
                EmpLURow = EmpLURows.next()
                if not EmpLURow == None:
                    SFPerEmp = EmpLURow.getValue('SFPerEmp')
                    FAR = EmpLURow.getValue('FAR')
                    PctOther = EmpLURow.getValue('PctOther')
                    
                    EmpValues = {}
                    EmpValues['SFPerEmp'] = SFPerEmp
                    EmpValues['FAR'] = FAR
                    EmpValues['PctOther'] = PctOther
                    EmpLUs[EmpLUCode] = EmpValues
                else:
                    EmpValues = {}
                    EmpValues['SFPerEmp'] = 0
                    EmpValues['FAR'] = 0
                    EmpValues['PctOther'] = 0
                    EmpLUs[EmpLUCode] = EmpValues
        else:
            for EmpLUCode in EmpLUCodes:
                EmpValues = {}
                EmpValues['SFPerEmp'] = 0
                EmpValues['FAR'] = 0
                EmpValues['PctOther'] = 0
                EmpLUs[EmpLUCode] = EmpValues
        UPDemand[TSCode]['EmpLandUses'] = EmpLUs
         
        #retrieve values from upd_rescalcs table
        ResCalcs = {}
        if arcpy.Exists('upd_rescalcs'):
            ResCalcRows = arcpy.SearchCursor('upd_rescalcs', where_clause = r"TSCode = '" + TSCode + r"'")
            for ResCalcRow in ResCalcRows:
                LUCode = ResCalcRow.getValue('LUCode')
                GrossAcrePerUnit = ResCalcRow.getValue('GrossAcPerUnit')
                GrossAcrePerOccUnit = ResCalcRow.getValue('GrossAcPerOccUnit')
      
                CalcValues = {}
                CalcValues['GrossAcrePerUnit'] = GrossAcrePerUnit
                CalcValues['GrossAcrePerOccUnit'] = GrossAcrePerOccUnit
                ResCalcs[LUCode] = CalcValues
        UPDemand[TSCode]['ResCalcs'] = ResCalcs
        
        #retrieve values from upd_empcalcs table
        EmpCalcs = {}
        if arcpy.Exists('upd_empcalcs'):
            EmpCalcRows = arcpy.SearchCursor('upd_empcalcs', where_clause = r"TSCode = '" + TSCode + r"'")
            for EmpCalcRow in EmpCalcRows:
                LUCode = EmpCalcRow.getValue('LUCode')
                GrossAcrePerEmp = EmpCalcRow.getValue('GrossAcPerEmp')
            
                CalcValues = {} 
                CalcValues['GrossAcrePerEmp'] = GrossAcrePerEmp
                EmpCalcs[LUCode] = CalcValues
        UPDemand[TSCode]['EmpCalcs'] = EmpCalcs
        
        #retrieve values from upd_SADemand table
        TotalsBySA = {}
        if arcpy.Exists('upd_subareademand'):
            for SACode in AllSAs:
                SADemoRows = arcpy.SearchCursor('upd_subareademand', where_clause = r"TSCode = '" + TSCode + r"' AND SACode = '" + SACode + r"'")
                SADemoRow = SADemoRows.next()
                if not SADemoRow == None:
                    SACode = SADemoRow.getValue('SACode')
                    PercentPop = SADemoRow.getValue('PctRes')
                    NumHH = SADemoRow.getValue('NumHH')
                    PercentEmp = SADemoRow.getValue('PctEmp')
                    NumEmp = SADemoRow.getValue('NumEmp')
                    
                    CalcValues = {}
                    CalcValues['PercentPop'] = PercentPop
                    CalcValues['NumHH'] = NumHH
                    CalcValues['PercentEmp'] = PercentEmp
                    CalcValues['NumEmp'] = NumEmp
                    TotalsBySA[SACode] = CalcValues
                else:
                    CalcValues = {}
                    CalcValues['PercentPop'] = 0
                    CalcValues['NumHH'] = 0
                    CalcValues['PercentEmp'] = 0
                    CalcValues['NumEmp'] = 0
                    TotalsBySA[SACode] = CalcValues
        else:
            for SACode in AllSAs:
                CalcValues = {}
                CalcValues['PercentPop'] = 0
                CalcValues['NumHH'] = 0
                CalcValues['PercentEmp'] = 0
                CalcValues['NumEmp'] = 0
                TotalsBySA[SACode] = CalcValues          
        UPDemand[TSCode]['TotalsBySA'] = TotalsBySA        

        #retrieve values from upd_subareares table
        PctResBySA = {}
        OccUnitsBySA = {}
        ResAcresBySA = {}
        if arcpy.Exists('upd_subareares'):
            #loop over SubAreas
            for SACode in AllSAs:
                PctResByLU = {}
                OccUnitsByLU = {}
                AcresByLU = {}
                
                #loop over Land Uses
                for ResLU in ResLUCodes:                    
                    #get the residential space values for the given LandUse
                    SAResRows = arcpy.SearchCursor('upd_subareares', where_clause = r"TSCode = '" + TSCode + r"' AND SACode = '" + SACode + r"' AND LUCode = '" + ResLU + r"'")
                    SAResRow = SAResRows.next()
                    if not SAResRow == None:
                        PctResByLU[ResLU] = SAResRow.getValue('PctRes')
                        OccUnitsByLU[ResLU] = SAResRow.getValue('OccUnits')
                        AcresByLU[ResLU] = SAResRow.getValue('AcresDemand')
                    else:
                        PctResByLU[ResLU] = 0
                        OccUnitsByLU[ResLU] = 0
                        AcresByLU[ResLU] = 0
                
                PctResBySA[SACode] = PctResByLU 
                OccUnitsBySA[SACode] = OccUnitsByLU
                ResAcresBySA[SACode] = AcresByLU
        else:
            #loop over SubAreas
            for SACode in AllSAs:
                PctResByLU = {}
                OccUnitsByLU = {}
                AcresByLU = {}
                #loop over res LUCodes
                for ResLU in ResLUCodes:
                    PctResByLU[ResLU] = 0
                    OccUnitsByLU[ResLU] = 0
                    AcresByLU[ResLU] = 0
                PctResBySA[SACode] = PctResByLU 
                OccUnitsBySA[SACode] = OccUnitsByLU
                ResAcresBySA[SACode] = AcresByLU  
                  
        UPDemand[TSCode]['PctResBySA'] = PctResBySA
        UPDemand[TSCode]['OccUnitsBySA'] = OccUnitsBySA
        UPDemand[TSCode]['ResAcresBySA'] = ResAcresBySA 

        #retrieve values from upd_subareaemp table
        PctEmpBySA = {}
        NumEmpbySA = {}
        EmpAcresBySA = {}
        if arcpy.Exists('upd_subareaemp'):
            #loop over SubAreas
            for SACode in AllSAs:               
                PctEmpByLU = {}
                NumSAEmpByLU = {}
                AcresByLU = {}
                
                #loop over emp LUCodes
                for EmpLU in EmpLUCodes:
                    #get the employment space values for the given LandUse
                    SAEmpRows = arcpy.SearchCursor('upd_subareaemp', where_clause = r"TSCode = '" + TSCode + r"' AND SACode = '" + SACode + r"' AND LUCode = '" + EmpLU + r"'")
                    SAEmpRow = SAEmpRows.next()
                    if not SAEmpRow == None:
                        PctEmpByLU[EmpLU] = SAEmpRow.getValue('PctEmp')           
                        NumSAEmpByLU[EmpLU] = SAEmpRow.getValue('NumEmp')
                        AcresByLU[EmpLU] = SAEmpRow.getValue('AcresDemand')
                    else:
                        PctEmpByLU[EmpLU] = 0          
                        NumSAEmpByLU[EmpLU] = 0
                        AcresByLU[EmpLU] = 0
                     
                PctEmpBySA[SACode] = PctEmpByLU
                NumEmpbySA[SACode] = NumSAEmpByLU
                EmpAcresBySA[SACode] = AcresByLU
        else:
            #loop over SubAreas
            for SACode in AllSAs:               
                PctEmpByLU = {}
                NumSAEmpByLU = {}
                AcresByLU = {}
                #loop over emp LUCodes
                for EmpLU in EmpLUCodes:
                    PctEmpByLU[EmpLU] = 0          
                    NumSAEmpByLU[EmpLU] = 0
                    AcresByLU[EmpLU] = 0
                PctEmpBySA[SACode] = PctEmpByLU
                NumEmpbySA[SACode] = NumSAEmpByLU
                EmpAcresBySA[SACode] = AcresByLU
                    
        UPDemand[TSCode]['PctEmpBySA'] = PctEmpBySA
        UPDemand[TSCode]['NumEmpBySA'] = NumEmpbySA
        UPDemand[TSCode]['EmpAcresBySA'] = EmpAcresBySA

    return UPDemand
        
def PopulateDemoTable(db, TSCode, StartPop, EndPop, PPHH, EPHH):
    #populate the upd_demographics table
    DemoFields = ['TSCode','StartPop','EndPop','PopChange','PPHH','EPHH']
    DemoFieldTypes = {'TSCode':'TEXT','StartPop':'LONG','EndPop':'LONG','PopChange':'LONG','PPHH':'DOUBLE','EPHH':'DOUBLE'}
    CreateOrEmptyTable(db,'upd_demographics',DemoFields,DemoFieldTypes,TSCode)
    
    Logger("Populating upd_demographics")
    PopChange = EndPop - StartPop
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_demographics'),DemoFields)
    cur.insertRow((TSCode,StartPop,EndPop,PopChange,PPHH,EPHH))
    del cur
    
def PopulateResLUTable(db, TSCode, ResInputs):
    '''
    ResInputs = A dictionary that contains acres per unit, percent vacant, and percent other space by Residential Land Use
        * The Key Name for acres per unit = 'AcPerUnit'
        * The Key Name for percent vacant = 'PctVacantUnits'
        * The Key Name for percent other space = 'PctOther'
        * Example Dictionary = {'rh': {'AcPerUnit': 0.05, 'PctOther': 0.2, 'PctVacantUnits': 0.1},'rm': {'AcPerUnit': 0.25, 'PctOther': 0.2, 'PctVacantUnits': 0.15}}
    '''
    #populate the upd_reslanduses table
    ResLUFields = ['TSCode','LUCode','LUName','AcPerUnit','PctVacantUnits','PctOther']
    ResLUFieldTypes = {'TSCode':'TEXT','LUCode':'TEXT','LUName':'TEXT',
                       'AcPerUnit':'DOUBLE','PctVacantUnits':'DOUBLE','PctOther':'DOUBLE'}
    CreateOrEmptyTable(db,'upd_reslanduses',ResLUFields,ResLUFieldTypes,TSCode)
    
    Logger("Populating upd_reslanduses") 
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_reslanduses'),ResLUFields)
    ResRows = arcpy.SearchCursor('upc_lu', where_clause = r"LUType = 'res'")
    for ResRow in ResRows:
        LUCode = ResRow.getValue('Code')
        LUName = ResRow.getValue('Name')
        AcrePerUnit = ResInputs[LUCode]['AcPerUnit']
        PerVacant = ResInputs[LUCode]['PctVacantUnits']
        PerOtherSpace = ResInputs[LUCode]['PctOther']
    
        cur.insertRow((TSCode,LUCode,LUName,AcrePerUnit,PerVacant,PerOtherSpace))
    del cur  

def PopulateResCalcsTable(db, TSCode):
    #calculate residential space values and populate the upd_rescalcs table
    ResCalcFields = ['TSCode','LUCode','GrossAcPerUnit','GrossAcPerOccUnit']
    ResCalcFieldTypes = {'TSCode':'TEXT','LUCode':'TEXT','GrossAcPerUnit':'DOUBLE','GrossAcPerOccUnit':'DOUBLE'}
    CreateOrEmptyTable(db,'upd_rescalcs',ResCalcFields,ResCalcFieldTypes,TSCode)
    
    Logger("Populating upd_rescalcs") 
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_rescalcs'),ResCalcFields)
    ResRows = arcpy.SearchCursor('upd_reslanduses', where_clause = r"TSCode = '" + TSCode + r"'")
    for ResRow in ResRows:
        LUCode = ResRow.getValue('LUCode')
        AcrePerUnit = ResRow.getValue('AcPerUnit')
        PerVacant = ResRow.getValue('PctVacantUnits')
        PerOtherSpace = ResRow.getValue('PctOther')
        AcrePerUnit = AcrePerUnit/(1-PerOtherSpace)
        AcrePerOccUnit = AcrePerUnit/(1-PerVacant)
         
        cur.insertRow((TSCode,LUCode,AcrePerUnit,AcrePerOccUnit))
    del cur
    
def PopulateEmpLUTable(db, TSCode, EmpInputs):
    '''
    EmpInputs = A dictionary that contains square feet per employee, FAR, and percent other space by Employment Land Use
        * The Key Name for square feet per employee = 'SFPerEmp'
        * The Key Name for FAR = 'FAR'
        * The Key Name for percent other space = 'PctOther'
        * Example Dictionary = {'ind': {'FAR': 0.2, 'PctOther': 0.5, 'SFPerEmp': 650}, 'ser': {'FAR': 0.5, 'PctOther': 0.2, 'SFPerEmp': 250}}
    '''
    #populate the upd_emplanduses table
    EmpLUFields = ['TSCode','LUCode','LUName','SFPerEmp','FAR','PctOther']
    EmpLUFieldTypes = {'TSCode':'TEXT','LUCode':'TEXT','LUName':'TEXT',
                       'SFPerEmp':'DOUBLE','FAR':'DOUBLE','PctOther':'DOUBLE'}
    CreateOrEmptyTable(db,'upd_emplanduses',EmpLUFields,EmpLUFieldTypes,TSCode)
    
    Logger("Populating upd_emplanduses")  
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_emplanduses'),EmpLUFields)
    EmpRows = arcpy.SearchCursor('upc_lu', where_clause = r"LUType = 'emp'")
    for EmpRow in EmpRows:
        LUCode = EmpRow.getValue('Code')
        LUName = EmpRow.getValue('Name')
        SFPerEmp = EmpInputs[LUCode]['SFPerEmp']
        FAR = EmpInputs[LUCode]['FAR']
        PctOther = EmpInputs[LUCode]['PctOther']
    
        cur.insertRow((TSCode, LUCode, LUName, SFPerEmp, FAR, PctOther))
    del cur
    
def PopulateEmpCalcTable(db, TSCode):
    #calculate employment space values and populate the upd_empcalcs table
    EmpCalcFields = ['TSCode','LUCode','GrossAcPerEmp']
    EmpCalcFieldTypes = {'TSCode':'TEXT','LUCode':'TEXT','GrossAcPerEmp':'DOUBLE'}
    CreateOrEmptyTable(db,'upd_empcalcs',EmpCalcFields,EmpCalcFieldTypes,TSCode)
    
    Logger("Populating upd_empcalcs")  
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_empcalcs'),EmpCalcFields)
    EmpRows = arcpy.SearchCursor('upd_emplanduses', where_clause = r"TSCode = '" + TSCode + r"'")
    for EmpRow in EmpRows:
        LUCode = EmpRow.getValue('LUCode')
        SFPerEmp = EmpRow.getValue('SFPerEmp')
        FAR = EmpRow.getValue('FAR')
        PerOtherSpace = EmpRow.getValue('PctOther')
        AcrePerEmp = ((SFPerEmp/FAR)/(1-PerOtherSpace))/43560
       
        cur.insertRow((TSCode,LUCode,AcrePerEmp))         
    del cur

def PopulateSADemandTable(db, TSCode, SubAreas, SADemandInputs):
    '''
    SubAreas = List of SubAreaCodes
        * Example List = ['sa1','sa2']
    SADemandInputs = A dictionary that contains percent of population and percent of employment by SubArea
        * The Key Name for percent population = 'PercentPop'
        * The Key Name for percent employment = 'PercentEmp'
        * Example Dictionary = {'sa1':{'PercentPop':0.6, 'PercentEmp':0.9},'sa2':{'PercentPop':0.4, 'PercentEmp':0.1}}
    '''
    
    #create the upd_subareademand table
    SADemandFields = ['TSCode','SACode','PctRes','PctEmp','NumHH','NumEmp']
    SADemandFieldTypes = {'TSCode':'TEXT','SACode':'TEXT','PctRes':'DOUBLE','PctEmp':'DOUBLE','NumHH':'DOUBLE','NumEmp':'DOUBLE'}
    CreateOrEmptyTable(db,'upd_subareademand',SADemandFields,SADemandFieldTypes,TSCode)
    
    Logger("Populating upd_subareademand")   
    #calculate the number of households and employees by subarea and save to upd_subareademand table
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_subareademand'),SADemandFields)
    
    #get population change, PPHH, and EPHH from Demographics table
    DemoRows = arcpy.SearchCursor('upd_demographics', where_clause = r"TSCode = '" + TSCode + r"'")
    DemoRow = DemoRows.next()
    PopChange = DemoRow.getValue('PopChange')
    PPHH = DemoRow.getValue('PPHH')
    EPHH = DemoRow.getValue('EPHH')
    
    for SubArea in SubAreas:
        PercentPop = SADemandInputs[SubArea]['PercentPop']
        PercentEmp = SADemandInputs[SubArea]['PercentEmp']
        NumHH = PercentPop*(PopChange/PPHH)
        NumEmp = PercentEmp*(PopChange/PPHH)*EPHH
        
        cur.insertRow((TSCode,SubArea,PercentPop,PercentEmp,NumHH,NumEmp))
    del cur

def PopulateSAResTable(db, TSCode, SubAreas, SAResInputs):
    '''
    SubAreas = List of SubAreaCodes
        * Example List = ['sa1','sa2']
    SAResInputs = A dictionary that contains the percent of households going into each residential land use type by SubArea
        * Example Dictionary = {'sa1': {'rl': 0.05, 'rm': 0.85, 'rh': 0.1},'sa2': {'rl': 0.2, 'rm': 0.8, 'rh': 0}}
    '''
    
    #create the upd_subareares table
    SAResFields = ['TSCode','SACode','LUCode','PctRes','OccUnits','AcresDemand']
    SAResFieldTypes = {'TSCode':'TEXT','SACode':'TEXT','LUCode':'TEXT','PctRes':'DOUBLE','OccUnits':'DOUBLE','AcresDemand':'DOUBLE'}
    CreateOrEmptyTable(db,'upd_subareares',SAResFields,SAResFieldTypes,TSCode)
    
    Logger("Populating upd_subareares")  
    #calculate occupied units and gross acres demanded by subarea
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_subareares'),SAResFields)

    for SubArea in SubAreas:
        #get the number of Households in this SubArea
        SADemandRows = arcpy.SearchCursor('upd_subareademand', where_clause = r"SACode = '" + SubArea + r"'")
        SADemandRow = SADemandRows.next()
        NumSAHH = SADemandRow.getValue('NumHH')

        ResLURows = arcpy.SearchCursor('upc_lu', where_clause = r"LUType = 'res'")
        for ResLURow in ResLURows:
            ResLU = ResLURow.getValue('Code')
            
            #get GrossAcrePerOccUnit Value for this land use
            ConversionRows = arcpy.SearchCursor('upd_rescalcs', where_clause = r"LUCode = '" + ResLU + r"' AND TSCode = '" + TSCode + r"'")
            ConversionRow = ConversionRows.next()
            GrossAcrePerOccUnit = ConversionRow.getValue('GrossAcPerOccUnit')
            
            #get number of households by LU type
            OccHH = NumSAHH*SAResInputs[SubArea][ResLU]
            ResAcresByLU = OccHH*GrossAcrePerOccUnit
            
            cur.insertRow((TSCode,SubArea,ResLU,SAResInputs[SubArea][ResLU],OccHH,ResAcresByLU))  
    del cur

def PopulateSAEmpTable(db, TSCode, SubAreas, SAEmpInputs):
    '''
    SubAreas = List of SubAreaCodes
        * Example List = ['sa1','sa2']
    SAEmpInputs = A dictionary that contains the percent of employees going into each employment land use type by SubArea
        * Example Dictionary = {'sa1': {'ind': 0.1, 'ch': 0.3, 'cl': 0.6},'sa2': {'ind': 0.5, 'ch': 0.2, 'cl': 0.3}}
    '''
    #create the upd_subareaemp table
    SAEmpFields = ['TSCode','SACode','LUCode','PctEmp','NumEmp','AcresDemand']
    SAEmpFieldTypes = {'TSCode':'TEXT','SACode':'TEXT','LUCode':'TEXT','PctEmp':'DOUBLE','NumEmp':'DOUBLE','AcresDemand':'DOUBLE'}
    CreateOrEmptyTable(db,'upd_subareaemp',SAEmpFields,SAEmpFieldTypes,TSCode)
    
    Logger("Populating upd_subareaemp") 
    #calculate number of employees and acres demanded by subarea and save to upd_subareaemp
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_subareaemp'),SAEmpFields)
    
    for SubArea in SubAreas:
        #get the number of employees in this SubArea
        SADemandRows = arcpy.SearchCursor('upd_subareademand', where_clause = r"SACode = '" + SubArea + r"'")
        SADemandRow = SADemandRows.next()
        NumSAEmp = SADemandRow.getValue('NumEmp')

        EmpLURows = arcpy.SearchCursor('upc_lu', where_clause = r"LUType = 'emp'")
        for EmpLURow in EmpLURows:
            EmpLU = EmpLURow.getValue('Code')
            
            #get number of employees in this LU type
            NumEmpByLU = NumSAEmp * SAEmpInputs[SubArea][EmpLU]
            
            #convert number of employees to space needed
            EmpAcresRows = arcpy.SearchCursor('upd_empcalcs', where_clause = r"LUCode = '" + EmpLU + r"' AND TSCode = '" + TSCode + r"'")
            EmpAcresRow = EmpAcresRows.next()
            GrossAcrePerEmp = EmpAcresRow.getValue('GrossAcPerEmp')
            
            EmpAcresByLU = NumEmpByLU * GrossAcrePerEmp
            
            cur.insertRow((TSCode,SubArea,EmpLU,SAEmpInputs[SubArea][EmpLU],NumEmpByLU,EmpAcresByLU))
    del cur
    
def UpdateUPCDemandTable(db, TSCode):
    #update upc_demand table
    arcpy.env.workspace = db
    
    Logger("Populating upc_demand")
    #delete rows for this timestep if they exist
    arcpy.MakeTableView_management('upc_demand', 'DemandTableView'+TSCode)
    TSCodeSelection = arcpy.AddFieldDelimiters('DemandTableView'+TSCode, 'TSCode') + r" = '" + TSCode + r"'"
    arcpy.SelectLayerByAttribute_management('DemandTableView'+TSCode, 'NEW_SELECTION', TSCodeSelection)
    if int(arcpy.GetCount_management('DemandTableView'+TSCode).getOutput(0)) > 0:
        arcpy.DeleteRows_management('DemandTableView'+TSCode)
       
    #insert new rows for this timestep
    cur = arcpy.da.InsertCursor(os.path.join(db,'upc_demand'),['TSCode','SACode','LUCode','Acres'])

    #copy the residential acres demanded
    SAResDemandRows = arcpy.SearchCursor('upd_subareares', where_clause = r"TSCode = '" + TSCode + r"'")
    for SAResDemandRow in SAResDemandRows:
        SACode = SAResDemandRow.getValue('SACode')
        LUCode = SAResDemandRow.getValue('LUCode')
        Acres = SAResDemandRow.getValue('AcresDemand')
        cur.insertRow((TSCode, SACode, LUCode, Acres))
        
    #copy the employment acres demanded
    SAEmpDemandRows = arcpy.SearchCursor('upd_subareaemp', where_clause = r"TSCode = '" + TSCode + r"'")
    for SAEmpDemandRow in SAEmpDemandRows:
        SACode = SAEmpDemandRow.getValue('SACode')
        LUCode = SAEmpDemandRow.getValue('LUCode')
        Acres = SAEmpDemandRow.getValue('AcresDemand')
        cur.insertRow((TSCode, SACode, LUCode, Acres))
    del cur

def CalculateDemand(db,TSCode):
    '''
    From Demographic inputs, this function computes the demand for each land use within each SubArea for a single timestep
    
    Demand calculated for employment types:
    1. Total number of employees
    2. Total Acres needed for allocation
        
    Demand calculated for residential types:
    1. Total number of households
    2. Total acres needed for allocation
        
    Steps:
    1. Get input demographic data from UI 
        a. Not implemented yet...the inputs are hard coded in
    2. Create or update ucd_* tables in the file geodatabase with the demand values
        a. upd_demographics
            i. Contains input values
                * Start, end and change in population 
                * People Per Household 
                * Employees Per Household
        b. upd_reslanduses
            1. Contains input values by residential land use type:
                * Land use code and descriptive name
                * Net gross acres per unit
                * Percent vacant units
                * Percent other space
        c. upd_rescalcs
            i. Contains values calculated from upd_reslanduses by residential land use type:
                * Land use code
                * Gross acres per unit (all)
                * Gross acres per occupied unit
        d. upd_emplanduses
            i. Contains input values by employment land use type:
                * Land use code and descriptive name
                * Square feet per employee
                * Floor Area Ratio (FAR)
                * Percent other space
        e. upd_empcalcs
            i. Contains values calculated from upd_emplanduses by employment land use type:
                * Land use code
                * Gross acres per employee
        f. upd_subareademand
            i. Contains input values by SubArea:
                * SubArea Code
                * Percent of total population to be allocated
                * Percent of total employment to be allocated
            ii. Contains calculated values by SubArea:
                * Number of households
                * Number of employees
        g. upd_subareares
            i. Contains input values by SubArea and residential land use type:
                * Percent of SubArea population to be allocated to each land use type
            ii. Contains calculated values by SubArea and residential land use type:
                * Occupied units
                * Gross acres demanded
        h. upd_subareaemp
            i. Contains input values by SunArea and employment land use type:
                * Percent of SubArea employees to be allocated to each land use type
            ii. Contains calculated values by SubArea and employment land use type:
                * Number of employees
                * Gross acres demanded
    3. Create and populate a dictionary with all of these values
    4. Update upc_demand table with the calculated demand in Acres
                
    Calls:
    CreateOrEmptyTable 
    
    Called by:
    
    Arguments:
    db: full path to the uplan file geodatabase
    TSCode: the timestep code
    
    Returns: a dictionary that contains all of the demand values (final and intermediate) for the given timestep
    '''
    
    Logger("Calculating Demographics")
    arcpy.env.workspace = db
    
    ###User inputs for upd_demographics
    StartPop = 10000
    EndPop = 35000
    PPHH = 2.05
    EPHH = 1.1
     
    PopulateDemoTable(db, TSCode, StartPop, EndPop, PPHH, EPHH)
    
    ###User inputs for upd_reslanduses
    Res1Inputs = {'AcrePerUnit':0.05,'PctVacant':0.1,'PctOther':0.2}
    Res2Inputs = {'AcrePerUnit':0.25,'PctVacant':0.15,'PctOther':0.2}
    Res3Inputs = {'AcrePerUnit':2,'PctVacant':0.2,'PctOther':0.5}
    Res4Inputs = {'AcrePerUnit':20,'PctVacant':0.1,'PctOther':0.55}
    
    ResInputs = {}
    ResInputs['rh'] = Res1Inputs
    ResInputs['rm'] = Res2Inputs
    ResInputs['rl'] = Res3Inputs
    ResInputs['rvl'] = Res4Inputs
    
    #populate the upd_reslanduses table
    PopulateResLUTable(db, TSCode, ResInputs)
    
    #calculate residential space values and populate the upd_rescalcs table
    PopulateResCalcsTable(db, TSCode)
    
    ###User inputs for upd_emplanduses   
    Emp1Inputs = {'SFPerEmp':250,'FAR':0.5,'PctOther':0.2}
    Emp2Inputs = {'SFPerEmp':500,'FAR':0.2,'PctOther':0.2}
    Emp3Inputs = {'SFPerEmp':650,'FAR':0.2,'PctOther':0.5}
    
    EmpInputs = {}
    EmpInputs['ser'] = Emp1Inputs
    EmpInputs['ret'] = Emp2Inputs
    EmpInputs['ind'] = Emp3Inputs
    
    #populate the upd_emplanduses table
    PopulateEmpLUTable(db, TSCode, EmpInputs)
    
    #calculate employment space values and populate upd_empcalcs table
    PopulateEmpCalcTable(db, TSCode)
     
    ###User inputs for upd_subareademand
    SubAreas = ['sa1','sa2']
    SA1Props = {'PercentPop':0.6,'PercentEmp':0.9}
    SA2Props = {'PercentPop':0.4,'PercentEmp':0.1}
    
    SADemandInputs = {}
    SADemandInputs['sa1'] = SA1Props
    SADemandInputs['sa2'] = SA2Props
     
    #calculate num Households and num emp by SA, then populate the upd_subareademand table
    PopulateSADemandTable(db, TSCode, SubAreas, SADemandInputs)
     
    ###User inputs for upd_subareares
    SA1ResProps = {'rh':0.1,'rm':0.85,'rl':0.05,'rvl':0}
    SA2ResProps = {'rh':0,'rm':0.6,'rl':0.2,'rvl':0.2}
    
    SAResInputs = {}
    SAResInputs['sa1'] = SA1ResProps
    SAResInputs['sa2'] = SA2ResProps
      
    #populate the upd_subareares table
    PopulateSAResTable(db, TSCode, SubAreas, SAResInputs)
     
    ###User inputs for upd_subareaemp
    SA1EmpInputs = {'ser':0.3,'ret':0.6,'ind':0.1}
    SA2EmpInputs = {'ser':0.2,'ret':0.3,'ind':0.5}
     
    SubAreaEmpInputs = {}
    SubAreaEmpInputs['sa1'] = SA1EmpInputs
    SubAreaEmpInputs['sa2'] = SA2EmpInputs
     
    #populate the upd_subareaemp table
    PopulateSAEmpTable(db, TSCode, SubAreas, SubAreaEmpInputs)
    
    ###update upc_demand table
    UpdateUPCDemandTable(db, TSCode)

def CalcRedevRes(UPConfig,TimeStep,pop):
    """
    Return the number of acres of each res type for redevelopment
    
    
    """
    
    Logger("Calculating Redev Acres: Residential")
    gdb = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    
    
    # get pphh
    whereClause = """TSCode = '{ts}'""".format(ts = TimeStep[0])
    fields = ['PPHH']
    cur = arcpy.da.SearchCursor(os.path.join(gdb,'upd_demographics'), fields, whereClause)
    pphh = cur.next()[0]
    
    # get subarea proportions
    sap = {}
    for sa in UPConfig['Subareas']:
        sap[sa['sa']] = {}
        whereClause = """TSCode = '{ts}' AND SACode = '{sacd}' """.format(ts = TimeStep[0], sacd = sa['sa'])
        cur = arcpy.SearchCursor(os.path.join(gdb,'upd_subareares'), whereClause, ['LUCode','PctRes'])
        lus = []
        for row in cur:
            lus.append(row.getValue('LUCode'))
            sap[sa['sa']][row.getValue('LUCode')] = row.getValue('PctRes')

        
        
        # Get the subarea's proportion of total pop
        cur = arcpy.SearchCursor(os.path.join(gdb,'upd_subareademand'), whereClause, ['PctRes'])
        sap[sa['sa']]['PctRes'] = cur.next().getValue('PctRes')
    
    # Get densities
    
    whereClause = """TSCode = '{ts}'""".format(ts = TimeStep[0])
    cur = arcpy.SearchCursor(os.path.join(gdb,'upd_rescalcs'), whereClause, ['LUCode','GrossAcPerOccUnit'])
    acPerUnit = {}
    for row in cur:
        acPerUnit[row.getValue('LUCode')] = row.getValue('GrossAcPerOccUnit')
    
    resAc = {}
    reDevHH = {}
    for sa in UPConfig['Subareas']:
        resAc[sa['sa']] = {}
        reDevHH[sa['sa']] = {}
        sapop = pop*sap[sa['sa']]['PctRes']
        sahh = sapop/pphh
        for lu in lus:
            reDevHH[sa['sa']][lu] = sahh*sap[sa['sa']][lu]
            resAc[sa['sa']][lu] = reDevHH[sa['sa']][lu]*acPerUnit[lu]
            
    
    Logger("Calculated Redev Acres")        

    return([resAc,reDevHH])
    
def CalcRedevEmp(UPConfig,TimeStep,emp):
    """
    Return the number of acres of each emp type for redevelopment
    
    
    """
    
    Logger("Calculating Redev Acres: Employment")
    gdb = os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'])
    
    
    
    # get subarea proportions
    sap = {}
    for sa in UPConfig['Subareas']:
        sap[sa['sa']] = {}
        whereClause = """TSCode = '{ts}' AND SACode = '{sacd}' """.format(ts = TimeStep[0], sacd = sa['sa'])
        cur = arcpy.SearchCursor(os.path.join(gdb,'upd_subareaemp'), whereClause, ['LUCode','PctEmp'])
        lus = []
        for row in cur:
            lus.append(row.getValue('LUCode'))
            sap[sa['sa']][row.getValue('LUCode')] = row.getValue('PctEmp')

        
        
        # Get the subarea's proportion of total pop
        cur = arcpy.SearchCursor(os.path.join(gdb,'upd_subareademand'), whereClause, ['PctEmp'])
        sap[sa['sa']]['PctEmp'] = cur.next().getValue('PctEmp')
    
    # Get densities
    
    whereClause = """TSCode = '{ts}'""".format(ts = TimeStep[0])
    cur = arcpy.SearchCursor(os.path.join(gdb,'upd_empcalcs'), whereClause, ['LUCode','GrossAcPerEmp'])
    acPerEmp = {}
    for row in cur:
        acPerEmp[row.getValue('LUCode')] = row.getValue('GrossAcPerEmp')
    
    empAc = {}
    reDevEmp = {}
    for sa in UPConfig['Subareas']:
        empAc[sa['sa']] = {}
        reDevEmp[sa['sa']] = {}
        saemp = emp*sap[sa['sa']]['PctEmp']
        for lu in lus:
            reDevEmp[sa['sa']][lu] = saemp*sap[sa['sa']][lu]
            empAc[sa['sa']][lu] = reDevEmp[sa['sa']][lu]*acPerEmp[lu]
            
    
    Logger("Calculated Redev Acres")        

    return([empAc,reDevEmp])
    

def WriteUPDemandToGDB(db,UPDemand,UPConfig):
    '''populates the upd_tables from UPDemand dictionary'''
    
    for TSCode in UPDemand.keys():
        DValues = UPDemand[TSCode]
        
        #demographics table
        PopulateDemoTable(db,TSCode,DValues['StartPop'],DValues['EndPop'],DValues['PPHH'],DValues['EPHH'])
    
        #res lu and calcs tables
        PopulateResLUTable(db,TSCode,DValues['ResLandUses'])
        PopulateResCalcsTable(db,TSCode)
        
        #emp lu and calcs tables
        PopulateEmpLUTable(db,TSCode,DValues['EmpLandUses'])
        PopulateEmpCalcTable(db,TSCode)
            
        #SA demand table
        AllSAs = [sa['sa'] for sa in UPConfig['Subareas']]
        PopulateSADemandTable(db,TSCode,AllSAs,DValues['TotalsBySA'])
        
        #SubArea Res and Emp Tables
        PopulateSAResTable(db, TSCode, AllSAs, DValues['PctResBySA'])
        PopulateSAEmpTable(db, TSCode, AllSAs, DValues['PctEmpBySA'])

    
if __name__ == "__main__":
    dbpath = r"..\testing\TestAllocation" 
    dbname = 'AllocTest.gdb'
    TSCode = 'ts1'
    
    InWorkspace = os.path.join(dbpath,dbname)
    #UpdateUPCDemandTable(InWorkspace,'ts1')
#     CalculateDemand(InWorkspace,TSCode)

    UPDemand = ReadUPDemandFromGDB(InWorkspace)
#     uiut.MakeDemandPickle(UPDemand, InWorkspace)
    print(UPDemand)
#     print(UPDemand[TSCode]['PctEmpBySA'])
    

    
#     TestDemand = True
#     TestRedev = False
#     
#     # Testing primary Demand Calculations
#     if TestDemand == True:
#         InWorkspace = os.path.join(dbpath,dbname)
#         UPDemand = CalculateDemand(InWorkspace,TSCode)
#         print(UPDemand)
#     
#     # Testing Redevelopment
#     if TestRedev == True:
#         Logger("Reading UPConfig")
#         UPConfig = upc.ReadUPConfigFromGDB(dbpath, dbname)
#         pop = 250
#         emp = 200
#         empac = CalcRedevRes(UPConfig, UPConfig['TimeSteps'][0], pop)
        
        
        
    
    
    print("script finished")
    