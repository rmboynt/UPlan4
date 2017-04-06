'''
Created on April 22, 2015

@author: boynton
'''
import arcpy
import os
from Utilities import Logger
#from GenerateServiceAreas import whereClause
import UPConfig as upc

def CreateOrEmptyTable(db,TableName,Fields,FieldTypes):
    '''
    If the given table doesn't exist, this function will create the table.
    If the given table does exist, all rows will be removed
    
    Called by: CalculateDemand
    
    Arguments:
    db: full path to the uplan file geodatabase
    TableName: The name of the table
    Fields: A list containing the field names
    FieldTypes: A Dictionary that defines the field types by the field names
    
    '''
    arcpy.env.workspace = db
    if arcpy.Exists(TableName):
        Logger("Emptying Table: " + TableName)
        #arcpy.DeleteRows_management(TableName)
    else:
        #create the table
        Logger("Creating Table: " + TableName)
        arcpy.CreateTable_management(InWorkspace, TableName)
        #add the field(s)
        for Field in Fields:
            arcpy.AddField_management(TableName,Field,FieldTypes[Field])

def CalculateDemand(db,TSCode):
    '''
    From Demographic inputs, this function computes the demand for each land use within each SubArea for a single timestep
    
    Demand calculated for employment types:
    1. Total number of employees
    2. Total Acres needed for allocation
        
    Demand calculated for residentail types:
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
    #a dictionary that will store the demand values
    UPDemand = {}
    
    ###User inputs for upd_demographics (Note: tested getting values from toolbox within a function and it works)
    if TSCode == 'ts1':
        StartPop = 10000
        EndPop = 35000
        PPHH = 2.05
        EPHH = 1.1
    elif TSCode == 'ts2':
        StartPop = 35000
        EndPop = 50000
        PPHH = 2.05
        EPHH = 1.1
    
    #populate the upd_demographics table
    DemoFields = ['TSCode','StartPop','EndPop','PopChange','PPHH','EPHH']
    DemoFieldTypes = {'TSCode':'TEXT','StartPop':'LONG','EndPop':'LONG','PopChange':'LONG','PPHH':'DOUBLE','EPHH':'DOUBLE'}
    CreateOrEmptyTable(InWorkspace,'upd_demographics',DemoFields,DemoFieldTypes)
    
    Logger("Populating upd_demographics")
    PopChange = EndPop - StartPop
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_demographics'),DemoFields)
    cur.insertRow((TSCode,StartPop,EndPop,PopChange,PPHH,EPHH))
    del cur
    
    #put upd_demographics values in UPDemand
    UPDemand['PopChange'] = PopChange
    UPDemand['PPHH'] = PPHH
    UPDemand['EPHH'] = EPHH
    
    ###User inputs for upd_reslanduses
    #There is going to be a variable number of ResLandUses so will have to loop through them and get values I think
    #for now we'll just assume 3
     
    #get names of the ResLandUses - search the upc_lu table to get residential land uses
        #if this is the method, need to add a field to upc_lu to distinguish between res and emp types
    ResLUs = ['rh','rm','rl','rvl']
     
    #get values for the Residential land uses
    Res1Code = 'rh'
    Res1Name = 'Residential High' #can get this from a search cursor in upc_lu table
    Res1AcrePerUnit = 0.05
    Res1PerVacant = 0.1
    Res1PerOtherSpace = 0.2
     
    Res2Code = 'rm'
    Res2Name = 'Residential Medium' #can get this from a search cursor in upc_lu table
    Res2AcrePerUnit = 0.25
    Res2PerVacant = 0.15
    Res2PerOtherSpace = 0.2
     
    Res3Code = 'rvl'
    Res3Name = 'Residential Very Low' #can get this from a search cursor in upc_lu table
    Res3AcrePerUnit = 10
    Res3PerVacant = 0.2
    Res3PerOtherSpace = 0.5
    
    Res4Code = 'rl'
    Res4Name = 'Residential Low' #can get this from a search cursor in upc_lu table
    Res4AcrePerUnit = 2
    Res4PerVacant = 0.2
    Res4PerOtherSpace = 0.5
     
    #populate the upd_reslanduses table
    ResLUFields = ['TSCode','LUCode','LUName','AcPerUnit','PctVacantUnits','PctOther']
    ResLUFieldTypes = {'TSCode':'TEXT','LUCode':'TEXT','LUName':'TEXT',
                       'AcPerUnit':'DOUBLE','PctVacantUnits':'DOUBLE','PctOther':'DOUBLE'}
    CreateOrEmptyTable(InWorkspace,'upd_reslanduses',ResLUFields,ResLUFieldTypes)
    
    Logger("Populating upd_reslanduses") 
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_reslanduses'),ResLUFields)
    #for x in range(0,len(ResLU)):
    cur.insertRow((TSCode,Res1Code,Res1Name,Res1AcrePerUnit,Res1PerVacant,Res1PerOtherSpace))
    cur.insertRow((TSCode,Res2Code,Res2Name,Res2AcrePerUnit,Res2PerVacant,Res2PerOtherSpace))
    cur.insertRow((TSCode,Res3Code,Res3Name,Res3AcrePerUnit,Res3PerVacant,Res3PerOtherSpace))
    cur.insertRow((TSCode,Res4Code,Res4Name,Res4AcrePerUnit,Res4PerVacant,Res4PerOtherSpace))
    del cur   
     
    ###calculate residential space values and populate the upd_rescalcs table
    ResCalcFields = ['TSCode','LUCode','GrossAcPerUnit','GrossAcPerOccUnit']
    ResCalcFieldTypes = {'TSCode':'TEXT','LUCode':'TEXT','GrossAcPerUnit':'DOUBLE','GrossAcPerOccUnit':'DOUBLE'}
    CreateOrEmptyTable(InWorkspace,'upd_rescalcs',ResCalcFields,ResCalcFieldTypes)
    
    Logger("Populating upd_rescalcs") 
    ResCalcs = {}
    whereClause = """TSCode = '{ts}'""".format(ts = TSCode)
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_rescalcs'),ResCalcFields)
    ResRows = arcpy.SearchCursor('upd_reslanduses',whereClause)
    for ResRow in ResRows:
        LUCode = ResRow.getValue('LUCode')
        AcrePerUnit = ResRow.getValue('AcPerUnit')
        PerVacant = ResRow.getValue('PctVacantUnits')
        PerOtherSpace = ResRow.getValue('PctOther')
        AcrePerUnit = AcrePerUnit/(1-PerOtherSpace)
        AcrePerOccUnit = AcrePerUnit/(1-PerVacant)
         
        cur.insertRow((TSCode,LUCode,AcrePerUnit,AcrePerOccUnit))
        
        CalcValues = {}
        CalcValues['AcrePerUnit'] = AcrePerUnit
        CalcValues['AcrePerOccUnit'] = AcrePerOccUnit
        ResCalcs[LUCode] = CalcValues
        
    del cur
    
    #put upd_rescalcs values in UPDemand
    UPDemand['ResCalcs'] = ResCalcs
          
    ###User inputs for upd_emplanduses
    #There is going to be a variable number of EmpLandUses so will have to loop through them and get values I think
    #for now we'll just assume 3
     
    #get names of EMPLandUses - search the upc_lu table to get employment land uses
        #if this is the method, need to add a field to upc_lu to distinguish between res and emp types
    EmpLUs = ['ret','ser','ind']
      
    #get values for the employment land uses
    Emp1Code = 'ret'
    Emp1Name = 'Retail' #can get this from a search cursor in upc_lu table
    Emp1SFperEmp = 250
    Emp1FAR = 0.5
    Emp1PerOtherSpace = 0.2
      
    Emp2Code = 'ser'
    Emp2Name = 'Service' #can get this from a search cursor in upc_lu table
    Emp2SFperEmp = 300
    Emp2FAR = 0.5
    Emp2PerOtherSpace = 0.2
      
    Emp3Code = 'ind'
    Emp3Name = 'Industrial' #can get this from a search cursor in upc_lu table
    Emp3SFperEmp = 650
    Emp3FAR = 0.2
    Emp3PerOtherSpace = 0.5
      
    #populate the upd_emplanduses table
    EmpLUFields = ['TSCode','LUCode','LUName','SFPerEmp','FAR','PctOther']
    EmpLUFieldTypes = {'TSCode':'TEXT','LUCode':'TEXT','LUName':'TEXT',
                       'SFPerEmp':'DOUBLE','FAR':'DOUBLE','PctOther':'DOUBLE'}
    CreateOrEmptyTable(InWorkspace,'upd_emplanduses',EmpLUFields,EmpLUFieldTypes)
    
    Logger("Populating upd_emplanduses")  
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_emplanduses'),EmpLUFields)
    #for x in range(0,len(EmpLU)):
    cur.insertRow((TSCode,Emp1Code,Emp1Name,Emp1SFperEmp,Emp1FAR,Emp1PerOtherSpace))
    cur.insertRow((TSCode,Emp2Code,Emp2Name,Emp2SFperEmp,Emp2FAR,Emp2PerOtherSpace))
    cur.insertRow((TSCode,Emp3Code,Emp3Name,Emp3SFperEmp,Emp3FAR,Emp3PerOtherSpace))
    del cur
      
    ###calculate employment space values and populate the upd_empcalcs table
    EmpCalcFields = ['TSCode','LUCode','GrossAcPerEmp']
    EmpCalcFieldTypes = {'TSCode':'TEXT','LUCode':'TEXT','GrossAcPerEmp':'DOUBLE'}
    CreateOrEmptyTable(InWorkspace,'upd_empcalcs',EmpCalcFields,EmpCalcFieldTypes)
    
    Logger("Populating upd_empcalcs")  
    EmpCalcs = {} 
    whereClause = """TSCode = '{ts}'""".format(ts = TSCode)
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_empcalcs'),EmpCalcFields)
    EmpRows = arcpy.SearchCursor('upd_emplanduses',whereClause)
    for EmpRow in EmpRows:
        LUCode = EmpRow.getValue('LUCode')
        SFperEmp = EmpRow.getValue('SFPerEmp')
        FAR = EmpRow.getValue('FAR')
        PerOtherSpace = EmpRow.getValue('PctOther')
        AcrePerEmp = ((SFperEmp/FAR)/(1-PerOtherSpace))/43560
       
        cur.insertRow((TSCode,LUCode,AcrePerEmp))
        
        CalcValues = {} 
        CalcValues['AcrePerEmp'] = AcrePerEmp
        EmpCalcs[LUCode] = CalcValues
         
    del cur
     
    #put upd_empcalcs values in UPDemand
    UPDemand['EmpCalcs'] = EmpCalcs
     
    ###User inputs for upd_subareademand
    SubAreas = ['sa1','sa2']
     
#     SA1Code = 'sa1'
#     SA1PerPop = 0.6
#     SA1PerEmp = 0.9
#      
#     SA2Code = 'sa2'
#     SA2PerPop = 0.4
#     SA2PerEmp = 0.1
    SAProps = {'pop':0.8,'emp':0.5}
    SA1PropInputs = {'Proportion':SAProps}
    
    SAProps = {'pop':0.2,'emp':0.5}
    SA2PropInputs = {'Proportion':SAProps}
    
    SADemandInputs = {}
    SADemandInputs['sa1'] = SA1PropInputs
    SADemandInputs['sa2'] = SA2PropInputs
     
    #create the upd_subareademand table
    SADemandFields = ['TSCode','SACode','PctRes','PctEmp','NumHH','NumEmp']
    SADemandFieldTypes = {'TSCode':'TEXT','SACode':'TEXT','PctRes':'DOUBLE','PctEmp':'DOUBLE','NumHH':'DOUBLE','NumEmp':'DOUBLE'}
    CreateOrEmptyTable(InWorkspace,'upd_subareademand',SADemandFields,SADemandFieldTypes)
    
    Logger("Populating upd_subareademand")   
    #calculate the number of households and employees by subarea and save to upd_subareademand table
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_subareademand'),SADemandFields)
    TotalsBySA = {}
    for SubArea in SubAreas:
        PercentPop = SADemandInputs[SubArea]['Proportion']['pop']
        PercentEmp = SADemandInputs[SubArea]['Proportion']['emp']
        NumHH = PercentPop*(PopChange/PPHH)
        NumEmp = PercentEmp*(PopChange/PPHH)*EPHH
        
        cur.insertRow((TSCode,SubArea,PercentPop,PercentEmp,NumHH,NumEmp))
        
        CalcValues = {}
        CalcValues['PercentPop'] = PercentPop
        CalcValues['NumHH'] = NumHH
        CalcValues['PercentEmp'] = PercentEmp
        CalcValues['NumEmp'] = NumEmp
        TotalsBySA[SubArea] = CalcValues
    del cur

    #put upd_empcalcs values in UPDemand
    UPDemand['TotalsBySA'] = TotalsBySA
     
    ###User inputs for upd_subareares
#     SA1PerRH = 0.1
#     SA1PerRM = 0.85
#     SA1PerRL = 0.05
#       
#     SA2PerRH = 0
#     SA2PerRM = 0.8
#     SA2PerRL = 0.2
    LUProps = {'rh':0.05,'rm':0.80,'rl':0.10,'rvl':0.05}
    SA1PropInputs = {'Proportion':LUProps}
    
    LUProps = {'rh':0.45,'rm':0.50,'rl':0.04,'rvl':0.01}
    SA2PropInputs = {'Proportion':LUProps}
    
    SAResInputs = {}
    SAResInputs['sa1'] = SA1PropInputs
    SAResInputs['sa2'] = SA2PropInputs
      
    #create the upd_subareares table
    SAResFields = ['TSCode','SACode','LUCode','PctRes','OccUnits','AcresDemand']
    SAResFieldTypes = {'TSCode':'TEXT','SACode':'TEXT','LUCode':'TEXT','PctRes':'DOUBLE','OccUnits':'DOUBLE','AcresDemand':'DOUBLE'}
    CreateOrEmptyTable(InWorkspace,'upd_subareares',SAResFields,SAResFieldTypes)
    
    Logger("Populating upd_subareares")  
    #calculate occupied units and gross acres demanded by subarea
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_subareares'),SAResFields)
    
    PctResBySA = {}
    OccUnitsBySA = {}
    ResAcresBySA = {}
    
    for SubArea in SubAreas:
        PctResByLU = {}
        OccUnitsByLU = {}
        AcresByLU = {}
        
        for ResLU in ResLUs:
            NumSAHH = TotalsBySA[SubArea]['NumHH']
            OccHH = NumSAHH*SAResInputs[SubArea]['Proportion'][ResLU]
            ResAcresByLU = OccHH*UPDemand['ResCalcs'][ResLU]['AcrePerOccUnit']
            
            cur.insertRow((TSCode,SubArea,ResLU,SAResInputs[SubArea]['Proportion'][ResLU],OccHH,ResAcresByLU))
            
            #get values to send to UPDemand dict
            PctResByLU[ResLU] = SAResInputs[SubArea]['Proportion'][ResLU]
            OccUnitsByLU[ResLU] = OccHH
            AcresByLU[ResLU] = ResAcresByLU
    
        PctResBySA[SubArea] = PctResByLU 
        OccUnitsBySA[SubArea] = OccUnitsByLU
        ResAcresBySA[SubArea] = AcresByLU  
    del cur
    
    UPDemand['PctResBySA'] = PctResBySA
    UPDemand['OccUnitsBySA'] = OccUnitsBySA
    UPDemand['ResAcresBySA'] = ResAcresBySA  
     
    ###User inputs for upd_subareaemp
#     SA1PerCH = 0.3
#     SA1PerCL = 0.6
#     SA1PerInd = 0.1
#     
#     SA2PerCH = 0.2
#     SA2PerCL = 0.3
#     SA2PerInd = 0.5
    Proportions = {'ret':0.4,'ser':0.4,'ind':0.2}
    SA1EmpInputs = {'Proportion':Proportions}
     
    Proportions = {'ret':0.5,'ser':0.4,'ind':0.1}
    SA2EmpInputs = {'Proportion':Proportions}
     
    SubAreaEmpInputs = {}
    SubAreaEmpInputs['sa1'] = SA1EmpInputs
    SubAreaEmpInputs['sa2'] = SA2EmpInputs
     
    #create the upd_subareaemp table
    SAEmpFields = ['TSCode','SACode','LUCode','PctEmp','NumEmp','AcresDemand']
    SAEmpFieldTypes = {'TSCode':'TEXT','SACode':'TEXT','LUCode':'TEXT','PctEmp':'DOUBLE','NumEmp':'DOUBLE','AcresDemand':'DOUBLE'}
    CreateOrEmptyTable(InWorkspace,'upd_subareaemp',SAEmpFields,SAEmpFieldTypes)
    
    Logger("Populating upd_subareaemp") 
    #calculate number of employees and acres demanded by subarea and save to upd_subareaemp
    cur = arcpy.da.InsertCursor(os.path.join(db,'upd_subareaemp'),SAEmpFields)
    
    PctEmpBySA = {}
    NumEmpbySA = {}
    EmpAcresBySA = {}
    
    for SubArea in SubAreas:
        PctEmpByLU = {}
        NumSAEmpByLU = {}
        AcresByLU = {}
        
        for EmpLU in EmpLUs:
            NumSAEmp = TotalsBySA[SubArea]['NumEmp']
            NumEmpByLU = NumSAEmp * SubAreaEmpInputs[SubArea]['Proportion'][EmpLU]
            EmpAcresByLU = NumEmpByLU * UPDemand['EmpCalcs'][EmpLU]['AcrePerEmp']
            
            cur.insertRow((TSCode,SubArea,EmpLU,SubAreaEmpInputs[SubArea]['Proportion'][EmpLU],NumEmpByLU,EmpAcresByLU))
            
            #get values to send to UPDemand dict
            PctEmpByLU[EmpLU] = SubAreaEmpInputs[SubArea]['Proportion'][EmpLU]           
            NumSAEmpByLU[EmpLU] = NumEmpByLU
            AcresByLU[EmpLU] = EmpAcresByLU
            
        PctEmpBySA[SubArea] = PctEmpByLU
        NumEmpbySA[SubArea] = NumSAEmpByLU
        EmpAcresBySA[SubArea] = AcresByLU
    del cur
     
    UPDemand['PctEmpBySA'] = PctEmpBySA
    UPDemand['NumEmpBySA'] = NumEmpbySA
    UPDemand['EmpAcresBySA'] = EmpAcresBySA
    
    ###update upc_demand table
    Logger("Populating upc_demand")
    #delete rows for this timestep if they exist
    try:
        arcpy.MakeTableView_management('upc_demand', 'DemandTableView')
    except:
        pass # deal with it during the second time step
    TSCodeSelection = arcpy.AddFieldDelimiters('DemandTableView', 'TSCode') + r" = '" + TSCode + r"'"
    arcpy.SelectLayerByAttribute_management('DemandTableView', 'NEW_SELECTION', TSCodeSelection)
    if int(arcpy.GetCount_management('DemandTableView').getOutput(0)) > 0:
        arcpy.DeleteRows_management('DemandTableView')
       
    #insert new rows for this timestep
    cur = arcpy.da.InsertCursor(os.path.join(db,'upc_demand'),['TSCode','SACode','LUCode','Acres'])
    
    for SubArea in SubAreas:
        for ResLU in ResLUs:
            Acres = UPDemand['ResAcresBySA'][SubArea][ResLU]
            cur.insertRow((TSCode,SubArea,ResLU,Acres))
        for EmpLU in EmpLUs:
            Acres = UPDemand['EmpAcresBySA'][SubArea][EmpLU]
            cur.insertRow((TSCode,SubArea,EmpLU,Acres))
    del cur
    
    #return a dictionary that has all the demand values by the timestep
    ReturnDict = {}
    ReturnDict[TSCode]=UPDemand
    return ReturnDict

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
    
def CalcRedevEmp(UPConfig,TimeStep,pop):
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


def ReDevCalcs(UPConfig,TimeStep,pop,emp):
    """
    Manage the calculation of redevelopment
    """

    resReDev = CalcRedevRes(UPConfig, UPConfig['TimeSteps'][0], pop)
    empReDev = CalcRedevEmp(UPConfig, UPConfig['TimeSteps'][0], emp)
    
    ReDevAc = {}
    for sa in UPConfig['Subareas']:
        ReDevAc[sa['sa']] = {}
        for lu in resReDev[0][sa['sa']].keys():
            ReDevAc[sa['sa']][lu] = resReDev[0][sa['sa']][lu]
        for lu in empReDev[0][sa['sa']].keys():
            ReDevAc[sa['sa']][lu] = empReDev[0][sa['sa']][lu]
            
    

    return(ReDevAc,[resReDev[1],empReDev[1]])

    
if __name__ == "__main__":
    dbpath = r"..\testing" 
    dbname = 'calaveras.gdb'
    TSCode = 'ts1'
    
    
    TestDemand = True
    TestRedev = False
    
    # Testing primary Demand Calculations
    if TestDemand == True:
        InWorkspace = os.path.join(dbpath,dbname)
        UPDemand = CalculateDemand(InWorkspace,TSCode)
        UPDemand = CalculateDemand(InWorkspace,'ts2')
        print(UPDemand)
    
    # Testing Redevelopment
    if TestRedev == True:
        Logger("Reading UPConfig")
        UPConfig = upc.ReadUPConfigFromGDB(dbpath, dbname)
        pop = 250
        emp = 200
        resac = CalcRedevRes(UPConfig, UPConfig['TimeSteps'][0], pop)
        print(resac[0])
        
        empac = CalcRedevEmp(UPConfig, UPConfig['TimeSteps'][0], emp)
        print(empac[0])
        
        redevResults = ReDevCalcs(UPConfig, UPConfig['TimeSteps'][0], pop, emp)
        
        
        Logger("pause")
    
    
    print("script finished")
    