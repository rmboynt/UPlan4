import arcpy, os
from UPConfig import unique_values

def CheckUPCKeys(db):  
    #check to see if all 7 keys are in the table, for non-SubArea keys, make sure there is a value associated with the key
    arcpy.env.workspace = db  
    #a list to hold the errors (if there are any)
    MissingKeyMessage = []
    
    RequiredKeys = ['BaseGeom_bnd','BaseGeom_cent','BaseGeom_id','Subarea_bnd','Subarea_id','Subarea_search','DistMode']
    for RequiredKey in RequiredKeys:
        #see if the key in the the keys table
        UPKeyRows = arcpy.SearchCursor('upc_key', where_clause = r"KeyName = '" + RequiredKey + r"'")
        UPKeyRow = UPKeyRows.next()
        if UPKeyRow == None:
            #this key is missing
            MissingKeyMessage.append('upc_key error: Missing from upc_key: ' + RequiredKey)
        else:
            #the key is present, check to see if there is a value (except SubArea ones)
            if not RequiredKey in ['Subarea_bnd','Subarea_id','Subarea_search']:
                if not len(UPKeyRow.getValue('KeyValue'))>0:
                    #there is no value for this key
                    MissingKeyMessage.append('upc_key error: The upc_key table is missing a value for the key: ' + RequiredKey)
    
    if len(MissingKeyMessage) == 0:
        MissingKeys = False
    else:
        MissingKeys = True
    
    return (MissingKeys, MissingKeyMessage)
        
def CheckUPCSubareas(db):
    #there must be at least one record, and each record needs a SubArea ID
    arcpy.env.workspace = db
    RowCount = 0
    MissingSAID = False
    
    SARows = arcpy.SearchCursor('upc_subareas')
    for SARow in SARows:
        RowCount += 1
        
        if not len(SARow.getValue('Code')) > 0:
            #missing SubArea ID
            MissingSAID = True
    
    if RowCount == 0:
        #there are no rows in the table
        MissingSA = True  
    else:
        MissingSA = False      
    
    return(MissingSA, MissingSAID)
    
def CheckUPCLandUse(db):
    #make sure at least 1 LUType, they have LUCode, LUType, AllocMethod and Priority
    #return any errors and a list of LUCodes
    arcpy.env.workspace = db
    RowCount = 0
    LUErrorMessages = []
    LUCodes = []
    
    LURows = arcpy.SearchCursor('upc_lu')
    for LURow in LURows:
        RowCount += 1
        
        LUCode = LURow.getValue('Code')
        #check LUCode
        if not len(LUCode) > 0:
            #this record doesn't have a LUCode
            LUErrorMessages.append('upc_lu error: LUCode is missing in ucp_lu table for row with ObjectID: ' + str(LURow.getValue('OBJECTID')))
        else:
            LUCodes.append(LUCode)
        
        #check LUType
        if not LURow.getValue('LUType') in ['emp','res']:
            #this record doesn't have a LUType
            LUErrorMessages.append('upc_lu error: Error with LUType in ucp_lu table for row with ObjectID: ' + str(LURow.getValue('OBJECTID')))
        
        #check AllocMethod
        if not LURow.getValue('AllocMethod') in ['1','2']:
            #this record doesn't have an AllocMethod 
            LUErrorMessages.append('upc_lu error: Error with AllocMethod in ucp_lu table for row with ObjectID: ' + str(LURow.getValue('OBJECTID')))
    
    if len(LUErrorMessages) == 0:
        LUError = False
    else:
        LUError = True
        
    if RowCount == 0:
        #there are no rows in the table
        MissingLU = True  
    else:
        MissingLU = False 
        
    return(LUCodes, LUError, LUErrorMessages, MissingLU)

def CheckUPTimesteps(db):
    #make sure at least 1 TS, gp layer exists, and has the correct GP field
    arcpy.env.workspace = db
    RowCount = 0
    TSErrorMessages = []
    TSCodes = []
    
    GPCodes = {}
    
    TSRows = arcpy.SearchCursor('upc_timesteps')
    for TSRow in TSRows:
        RowCount += 1
        
        TSCode = TSRow.getValue('Code')
        #check TSCode
        if not len(TSCode) > 0:
            #this record doesn't have a TSCode
            TSErrorMessages.append('upc_timesteps error: TSCode is missing in upc_timesteps table for row with ObjectID: ' + TSRow.getVlaue('OBJECTID'))
        else:
            TSCodes.append(TSCode)
        
        #check for GP layer and verify it's in the GDB
        GPLayer = TSRow.getValue('GPLayer')
        if not len(GPLayer) > 0:
            #this record doesn't have a general Plan layer
            TSErrorMessages.append('upc_timesteps error: General Plan attribute is missing in upc_timesteps for row with ObjectID: ' + TSRow.getVlaue('OBJECTID'))
        else:
            #this record has a general plan layer, verify it exists in the GDB
            if not arcpy.Exists(GPLayer):
                #GP layer doesn't exist
                TSErrorMessages.append('upc_timesteps error: General Plan layer (' + GPLayer + ') assigned in upc_timesteps for row with ObjectID: ' + TSRow.getVlaue('OBJECTID') + ' does not exist in the GDB')
            else:
                #check that the GPField exists within the GPLayer
                GPField = TSRow.getValue('GPField')
                FieldCheck = arcpy.ListFields(GPLayer, GPField)
                if not len(FieldCheck) == 1:
                    #the field doesn't exist within the GPLayer
                    TSErrorMessages.append('upc_timesteps error: The field within the General Plan layer assigned in upc_timesteps for row with ObjectID: ' + TSRow.getVlaue('OBJECTID') + ' does not exist')
                else:
                    #get a list of the GPCats (to be used in later checks)
                    UniqueGPCats = []
                    for GPCat in unique_values(GPLayer, GPField):
                        UniqueGPCats.append(GPCat)
                    GPCodes[TSCode] = UniqueGPCats
                    
    if len(TSErrorMessages) == 0:
        TSError = False
    else:
        TSError = True
        
    if RowCount == 0:
        #there are no rows in the table
        MissingTS = True  
    else:
        MissingTS = False 
        
    return(TSCodes, TSError, TSErrorMessages, MissingTS, GPCodes)

def CheckGPLU(db, TSCodes, LUCodes, GPCodes):
    #make sure each LU has 1+ GPCats (and those categories exist)
    arcpy.env.workspace = db
    GPLUErrorMessages = []
    
    for TSCode in TSCodes:
        for LUCode in LUCodes:
            RowCount = 0
            GPLUrows = arcpy.SearchCursor('upc_gplu', where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + LUCode + r"'")
            for GPLUrow in GPLUrows:
                RowCount += 1
                GPCat = GPLUrow.getValue('GPCat')
                if not GPCat in GPCodes[TSCode]:
                    #this GPCat isn't in the general plan layer for this TS
                    GPLUErrorMessages.append('upc_gplu error: LUCode ' + LUCode + ' in timestep ' + TSCode + ' is assigned to ' + GPCat + ', but this category is not in the general plan layer')
            if RowCount == 0:
                GPLUErrorMessages.append('upc_gplu error: LUCode ' + LUCode + ' in timestep ' + TSCode + ' is not assigned to any general plan categories')
    
    if len(GPLUErrorMessages) == 0:
        GPLUError = False
    else:
        GPLUError = True

    return(GPLUError, GPLUErrorMessages)

def CheckMU(db, TSCodes):
    #the table needs to exist (even if there are no records)
    #if there are records, go through LU codes and check that the given LU can go into the GPCats (according to upc_gplu)
    arcpy.env.workspace = db
    MUErrorMessages = []
    
    if not arcpy.Exists('upc_mu'):
        MUErrorMessages.append('upc_mu error: The upc_mu table is missing')
    else:
        for TSCode in TSCodes:
            MURows = arcpy.SearchCursor('upc_mu', where_clause = r"TSCode = '" + TSCode + r"'")
            for MURow in MURows:
                #get GPCat
                GPCat = MURow.getValue('GPCat')
                
                #split the LUCodes
                LUCodes = MURow.getValue('LUCode')
                MULUs= LUCodes.split('-')           
                
                #check that the LUCode is assigned to the GPCode
                for LUCode in MULUs:
                    LUGPmatch = False
                    GPLURows = arcpy.SearchCursor('upc_gplu', where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + LUCode + r"'")
                    for GPLURow in GPLURows:
                        if GPCat == GPLURow.getValue('GPCat'):
                            LUGPmatch = True
                    if LUGPmatch == False:
                        MUErrorMessages.append('upc_mu error: Row with ObjectID ' + MURow.getValue('OBJECTID') + 'has LUCode ' + LUCode + ' assigned to GPCat ' + GPCat + ', but this pair is not part of the upc_gplu table for timestep: ' + TSCode)
    
    if len(MUErrorMessages) == 0:
        MUError = False
    else:
        MUError = True
        
    return(MUError, MUErrorMessages)
     
def CheckConstraints(db, TSCodes):
    #each TS needs at least one
    #return a dictionary of constraints by TS to be used to check the cweights table
    arcpy.env.workspace = db
    ConsErrorMessages = []
    Constraints = {}
    
    for TSCode in TSCodes:
        ConsRows = arcpy.SearchCursor('upc_constraints', where_clause = r"TSCode = '" + TSCode + r"'")
        TSCons = []
        RowCount = 0
        for ConsRow in ConsRows:
            RowCount += 1
            ConsName = ConsRow.getValue('Name')
            TSCons.append(ConsName)
        if RowCount == 0:
            ConsErrorMessages.append('upc_constraints error: timestep ' + TSCode + ' does not have a constraint')
        Constraints[TSCode] = TSCons
    
    if len(ConsErrorMessages) == 0:
        ConsError = False
    else:
        ConsError = True
        
    return(ConsError, ConsErrorMessages, Constraints)

def CheckCWeights(db, TSCodes, LUCodes, Constraints):
    #each constraint needs at least 1 record
    #the CLayers must exist in the upc_constraints table
    #each LU has at least 1 record
    #weight can't be null
    arcpy.env.workspace = db
    CWeightErrorMessages = []
    
    for TSCode in TSCodes:
        for LUCode in LUCodes:
            CWeightRows = arcpy.SearchCursor('upc_cweights', where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + LUCode + r"'")
            RowCount = 0
            for CWeightRow in CWeightRows:
                RowCount += 1
                
                #the CLayers must exist in the upc_constraints table
                CLayer = CWeightRow.getValue('CLayer')
                if not CLayer in Constraints[TSCode]:
                    if not CLayer == None:
                        CWeightErrorMessages.append('upc_cweights error: LUCode ' + LUCode + ' has a constraint layer (' + CLayer + ') that is not in the upc_constraints table')
                    else:
                        CWeightErrorMessages.append('upc_cweights error: row with ObjectID ' + str(CWeightRow.getValue('OBJECTID')) + 'is missing the layer name')
                
                #weight can't be null
                CWeight = CWeightRow.getValue('Weight')
                print(CWeight)
                if not CWeight >= 0:
                    CWeightErrorMessages.append('upc_cweights error: LUCode ' + LUCode + ' is missing a weight for constraint layer: ' + CLayer)
                CWeight = None
                CLayer = None
                
            #each LU has at least 1 record    
            if RowCount == 0:
                CWeightErrorMessages.append('upc_cweights error: LUCode ' + LUCode + ' does not have a constraint for timestep ' + TSCode)
        
    #each constraint needs at least 1 record
    for Constraint in Constraints[TSCode]:
        ConsCheckRows = arcpy.SearchCursor('upc_cweights', where_clause = r"TSCode = '" + TSCode + r"' AND CLayer = '" + Constraint + r"'")
        RowCount = 0
        for ConsCheckRow in ConsCheckRows:
            RowCount += 1
        if RowCount == 0:
            CWeightErrorMessages.append('upc_cweights error: the constraint ' + Constraint + ' is not being used in timestep ' + TSCode)
        del ConsCheckRows
        
    if len(CWeightErrorMessages) == 0:
        CWeightError = False
    else:
        CWeightError = True
        
    return(CWeightError, CWeightErrorMessages)

def CheckAttractors(db, TSCodes):
    #each TS needs at least one
    #return a dictionary of constraints by TS to be used to check the cweights table
    arcpy.env.workspace = db
    AttErrorMessages = []
    Attractors = {}
    
    for TSCode in TSCodes:
        AttRows = arcpy.SearchCursor('upc_attractors', where_clause = r"TSCode = '" + TSCode + r"'")
        TSAtt = []
        RowCount = 0
        for AttRow in AttRows:
            RowCount += 1
            AttName = AttRow.getValue('Name')
            TSAtt.append(AttName)
        if RowCount == 0:
            AttErrorMessages.append('upc_attractors error: timestep ' + TSCode + ' does not have an attractor')
        Attractors[TSCode] = TSAtt
    
    if len(AttErrorMessages) == 0:
        AttError = False
    else:
        AttError = True
        
    return(AttError, AttErrorMessages, Attractors)

def CheckAWeights(db, TSCodes, LUCodes, Attractors):
    #each attractor needs at least 1 record
    #the AttLayers must exist in the upc_attractors table
    #each LU has at least 1 record
    #weight can't be null
    arcpy.env.workspace = db
    AWeightErrorMessages = []
    
    for TSCode in TSCodes:
        for LUCode in LUCodes:
            AWeightRows = arcpy.SearchCursor('upc_aweights', where_clause = r"TSCode = '" + TSCode + r"' AND LUCode = '" + LUCode + r"'")
            RowCount = 0
            for AWeightRow in AWeightRows:
                RowCount += 1
                
                #the AttLayers must exist in the upc_attractors table
                AttLayer = AWeightRow.getValue('AttLayer')
                if not AttLayer in Attractors[TSCode]:
                    AWeightErrorMessages.append('upc_aweights error: LUCode ' + LUCode + ' has an attractor layer (' + AttLayer + ') that is not in the upc_attractors table')
                
                #weight can't be null
                AWeight = AWeightRow.getValue('Weight')
                if not AWeight >= 0:
                    AWeightErrorMessages.append('upc_aweights error: LUCode ' + LUCode + ' is missing a weight for attractor layer: ' + AttLayer)
                AttLayer = None
                AWeight = None
                
            #each LU has at least 1 record    
            if RowCount == 0:
                AWeightErrorMessages.append('upc_aweights error: LUCode ' + LUCode + ' does not have an attractor for timestep ' + TSCode)
        
    #each attractor needs at least 1 record
    for Attractor in Attractors[TSCode]:
        AttCheckRows = arcpy.SearchCursor('upc_aweights', where_clause = r"TSCode = '" + TSCode + r"' AND AttLayer = '" + Attractor + r"'")
        RowCount = 0
        for AttCheckRow in AttCheckRows:
            RowCount += 1
        if RowCount == 0:
            AWeightErrorMessages.append('upc_aweights error: the attractor ' + Attractor + ' is not being used in timestep ' + TSCode)
        del AttCheckRows
        
    if len(AWeightErrorMessages) == 0:
        AWeightError = False
    else:
        AWeightError = True
        
    return(AWeightError, AWeightErrorMessages)

def CheckDemand(db,TSCodes, LUCodes):
    #each land use has demand in each timestep and subarea
    #demand can = 0
    arcpy.env.workspace = db
    DemandErrorMessages = []
    
    #get a list of SubAreas
    SARows = arcpy.SearchCursor('upc_subareas')
    SACodes=[]
    for SARow in SARows:
        SACodes.append(SARow.getValue('Code'))
    
    for TSCode in TSCodes:
        for SACode in SACodes:
            for LUCode in LUCodes:
                DemandRows = arcpy.SearchCursor('upc_demand', where_clause = r"TSCode = '" + TSCode + r"' AND SACode = '" + SACode + r"' AND LUCode = '" + LUCode + r"'")
                RowCount = 0
                for DemandRow in DemandRows:
                    AcresDemand = DemandRow.getValue('Acres')
                    RowCount += 1
                    
                if RowCount == 0:
                    DemandErrorMessages.append('upc_demand error: Missing a row for LUCode ' + LUCode + ' in SubArea ' + SACode + ' and timestep ' + TSCode)
                else:
                    if not AcresDemand >= 0:
                        DemandErrorMessages.append('upc_demand error: Missing acres demanded for LUCode ' + LUCode + ' in SubArea ' + SACode + ' and timestep ' + TSCode)
                AcresDemand = None
    
    if len(DemandErrorMessages) == 0:
        DemandError = False
    else:
        DemandError = True
        
    return(DemandError, DemandErrorMessages)
                
def CheckAllSettings(db):
    #The switch to see if all settings are in the gdb
    ReadyToRun = True
    #the error message
    UPErrorMessages = []

    #check the upc_keys table to make sure all of the keys are there
    MissingKeys, MissingKeyMessage = CheckUPCKeys(db)
    if MissingKeys == True:
        ReadyToRun = False
        UPErrorMessages.append(MissingKeyMessage)
        
    #check upc_subareas table
    MissingSA, MissingSAID = CheckUPCSubareas(db)
    if MissingSA == True:
        ReadyToRun = False
        UPErrorMessages.append('The upc_subareas table has no records')
    if MissingSAID == True:
        ReadyToRun = False
        UPErrorMessages.append('There is a missing SubArea Code in the upc_subareas table')

    #check upc_lu table
    LUCodes, LUError, LUErrorMessages, MissingLU = CheckUPCLandUse(db)
    if LUError == True:
        ReadyToRun = False
        UPErrorMessages.append(LUErrorMessages)
    if MissingLU == True:
        ReadyToRun = False
        UPErrorMessages.append('The upc_lu table is empty')
    
    #check upc_timesteps - need at least 1 with a GP that exists in the GDB
    #return a dictionary of GPCats by TS, to be used in later checks
    TSCodes, TSError, TSErrorMessages, MissingTS, GPCodes = CheckUPTimesteps(db)
    if TSError == True:
        ReadyToRun = False
        TSErrorMessages.append(LUErrorMessages)
    if MissingTS == True:
        ReadyToRun = False
        UPErrorMessages.append('The upc_timesteps table is empty')
    
    #the rest of the tables need at least one TSCode and/or one LUCode
    if not len(TSCodes) == 0 or len(LUCodes) == 0:
        #check upc_gplu
        GPLUError, GPLUErrorMessages = CheckGPLU(db, TSCodes, LUCodes, GPCodes)
        if GPLUError == True:
            ReadyToRun = False
            UPErrorMessages.append(GPLUErrorMessages)
        
        #check upc_mu
        MUError, MUErrorMessages = CheckMU(db, TSCodes)
        if MUError == True:
            ReadyToRun = False
            UPErrorMessages.append(MUErrorMessages)
        
        #check upc_constraints
        ConsError, ConsErrorMessages, Constraints = CheckConstraints(db, TSCodes)
        if ConsError == True:
            ReadyToRun = False
            UPErrorMessages.append(ConsErrorMessages)
        
        #check upc_cweights
        CWeightError, CWeightErrorMessages = CheckCWeights(db, TSCodes, LUCodes, Constraints)
        if CWeightError == True:
            ReadyToRun = False
            UPErrorMessages.append(CWeightErrorMessages)
        
        #check upc_attractors
        AttError, AttErrorMessages, Attractors = CheckAttractors(db, TSCodes)
        if AttError == True:
            ReadyToRun = False
            UPErrorMessages.append(AttErrorMessages)
        
        #check upc_aweights
        AWeightError, AWeightErrorMessages = CheckAWeights(db, TSCodes, LUCodes, Attractors)
        if AWeightError == True:
            ReadyToRun = False
            UPErrorMessages.append(AWeightErrorMessages)
            
        #check upc_demand
        DemandError, DemandErrorMessages = CheckDemand(db,TSCodes, LUCodes)
        if DemandError == True:
            ReadyToRun = False
            UPErrorMessages.append(DemandErrorMessages)
    
    
    return (ReadyToRun, UPErrorMessages)

if __name__ == "__main__":
    dbpath = r"..\testing" 
    dbname = 'calaveras.gdb'
    
    db = os.path.join(dbpath,dbname)

    #check all of the settings
    ReadyToRun, UPErrorMessages = CheckAllSettings(db)
    print('UPlan is ready to run: ' + str(ReadyToRun))
    print('Error Messages: ' + str(UPErrorMessages))

    
    print("script finished")