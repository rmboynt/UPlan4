import arcpy
import os
import cPickle as pickle
import UPConfig as upc
import UIUtilities as uiut
from operator import itemgetter
import Utilities
import CalcSubarea
import CalcGeneralPlans
import CalcConstraints
import CalcWeights
import Allocation
from UIUtilities import SplitPath
import LayerManagement
import CalcDemographics as CalcDem
import ZonalSum

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "UPlan 4"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [CreateUPlanGDB, ImportBaseGeometry, ImportConstraint, ImportAttractor, ImportGeneralPlan, ImportSALayer, ImportRedevTable,
                      AddTimeStep,RemoveTimeStep,AddLandUse,SetLandUsePriority,RemoveLandUse,
                      SetConstraints,SetConstraintWeights,SetAttractors,SetAttractorWeights,SetGeneralPlan,SetGeneralPlanSettings,SetMixedUse,
                      PreCalcAll,PreCalcSubareas,PreCalcGeneralPlans,PreCalcConstraints,PreCalcWeights,RunAllocation,ZonalSummary,ImportZonalLayer,
                      SetDemographics,SetSpaceReq4Res,SetSpaceReq4Emp,SetSubAreaPercentages,SetHousingDensity,SetEmploymentDist,RunDemographics]

class CreateUPlanGDB(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Create UPlan Geodatabase"
        self.description = "This tool creates a geodatabase for all UPlan layers and tables"
        self.canRunInBackground = False
        self.category = "A. Data Loading"

    def getParameterInfo(self):
        """Define parameter definitions"""
        # First parameter
        UPlan_gdb_folder = arcpy.Parameter(
            displayName="Location for UPlan GDB",
            name="uplan_gdb_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")
        
         # Second parameter
        UPlan_gdb_name = arcpy.Parameter(
            displayName="Name for UPlan GDB",
            name="uplan_gdb_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
          
        params = [UPlan_gdb_folder, UPlan_gdb_name]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        Uplan_gdb_folder = parameters[0].valueAsText
        Uplan_gdb_name = parameters[1].valueAsText
       
        #create UPlan geodatabase
        arcpy.CreateFileGDB_management(Uplan_gdb_folder, Uplan_gdb_name)
        
        #create UPC_*tables
        UPConfig = {}
    
        paths={'dbpath':Uplan_gdb_folder, 'dbname':Uplan_gdb_name + '.gdb'}
        UPConfig['paths'] = paths
    
        UPCTables = ['upc_key','upc_timesteps','upc_subareas','upc_lu','upc_demand','upc_gplu','upc_mu',
             'upc_constraints','upc_cweights','upc_attractors','upc_aweights','upc_layers']
    
        UPCTableFields = {'upc_key':['KeyName','KeyValue'],
                      'upc_timesteps':['TSOrder','Code','Name','GPLayer','GPField'],
                      'upc_subareas':['Code','Name'],
                      'upc_lu':['Code','Name','LUType','AllocMethod','Priority'],
                      'upc_demand':['TSCode','SACode','LUCode','Acres'],
                      'upc_gplu':['TSCode','LUCode','GPCat'],
                      'upc_mu':['TSCode','GPCat','LUCode'],
                      'upc_constraints':['TSCode','Name'],
                      'upc_cweights':['TSCode','LUCode','CLayer','Weight'],
                      'upc_attractors':['TSCode','Name'],
                      'upc_aweights':['TSCode','LUCode','AttLayer','Dist','Weight'],
                      'upc_layers':['FCName','LongName','DateAdded','Role']}
                      
        upc.CreateUPCTables(UPConfig,UPCTables,UPCTableFields)
        
        #add default values to upc_key table (prevents errors in later steps)
        UPGDB = uiut.JoinPath(Uplan_gdb_folder, Uplan_gdb_name) + '.gdb'
        uiut.CreateDefaultKeys(UPGDB)
        
        #create pickle file
        splitpath = uiut.SplitPath(UPGDB)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        uiut.MakePickle(UPConfig, UPGDB)
                                    
        return

class ImportBaseGeometry(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Import Base Geometry Layer"
        self.description = ""
        self.canRunInBackground = False
        self.category = "A. Data Loading"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB=arcpy.Parameter(
            displayName="UPlan File Geodatabase",
            name="up_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        in_base_geom_layer = arcpy.Parameter(
            displayName="Base Geometry Layer",
            name="geom_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
                               
        Descriptive_name=arcpy.Parameter(
            displayName="Base Geometry Descriptive Name",
            name="desc_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input")  
        
        pCentroidInside = arcpy.Parameter(
            displayName="Force Centroids Inside of Polygons",
            name="CentroidInside",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        pCentroidInside.value = False
        
        params = [pUPGDB, in_base_geom_layer, Descriptive_name, pCentroidInside]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        in_layer = parameters[1].valueAsText
        desc_name = parameters[2].valueAsText
        CentroidInside = parameters[3].value
               
        LayerManagement.ImportBaseGeom(UPGDB, in_layer, desc_name, CentroidInside)
                       
        return

class ImportConstraint(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3. Import Constraint Layer"
        self.description = "This tool imports a constraint layer to the UPlan geodatabase"
        self.canRunInBackground = False
        self.category = "A. Data Loading"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan File Geodatabase",
            name="up_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        InConstraint = arcpy.Parameter(
            displayName="Constraint Layer",
            name="constraint_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        LongName=arcpy.Parameter(
            displayName="Constraint Layer Long Name",
            name="desc_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input")                         

        params = [pUPGDB, InConstraint, LongName]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        in_layer = parameters[1].valueAsText
        desc_name = parameters[2].valueAsText
        
        LayerManagement.ImportConstraintLayer(in_layer, UPGDB, desc_name)
                       
        return
    
class ImportAttractor(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "4. Import Attractor Layer"
        self.description = "This tool imports an attractor layer to the UPlan geodatabase"
        self.canRunInBackground = False
        self.category = "A. Data Loading"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan File Geodatabase",
            name="up_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input") 
        
        InAttractor = arcpy.Parameter(
            displayName="Attractor Layer",
            name="attractor_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        LongName=arcpy.Parameter(
            displayName="Attractor Layer Long Name",
            name="desc_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input") 
                                
        params = [pUPGDB, InAttractor, LongName]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        in_layer = parameters[1].valueAsText
        desc_name = parameters[2].valueAsText
        
        LayerManagement.ImportAttractorLayer(in_layer, UPGDB, desc_name)
        
        return
    
class ImportGeneralPlan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "5. Import General Plan Layer"
        self.description = "This tool imports a general plan layer to the UPlan geodatabase"
        self.canRunInBackground = False
        self.category = "A. Data Loading"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan File Geodatabase",
            name="up_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")  
        
        InGP = arcpy.Parameter(
            displayName="General Plan Layer",
            name="gp_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        LongName=arcpy.Parameter(
            displayName="General Plan Layer Descriptive Name",
            name="desc_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input") 
        
#         GPCatField=arcpy.Parameter(
#             displayName="Field within the layer that contains the general plan codes",
#             name="gp_cat_field",
#             datatype="Field",
#             parameterType="Required",
#             direction="Input")  
#         GPCatField.parameterDependencies = [InGP.name]

        params = [pUPGDB, InGP, LongName]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        GPLayer = parameters[1].valueAsText
        desc_name = parameters[2].valueAsText
          
        LayerManagement.ImportGPLayer(GPLayer, UPGDB, desc_name)
                       
        return
    
class ImportSALayer(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "6. Import SubArea Layer"
        self.description = "Imports an SubArea layer to the geodatabase"
        self.canRunInBackground = False
        self.category = "A. Data Loading"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB=arcpy.Parameter(
            displayName="UPlan File Geodatabase",
            name="up_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pInSALayer = arcpy.Parameter(
            displayName="SubArea Layer",
            name="sa_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input") 
        
        pLongName=arcpy.Parameter(
            displayName="SubArea Layer Descriptive Name",
            name="desc_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input") 
        
        pSAIDField=arcpy.Parameter(
            displayName="Field within the layer that contains the SubArea codes (or IDs)",
            name="sa_id_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")  
                
        pSANameField=arcpy.Parameter(
            displayName="Field within the layer that contains the SubArea descriptions (or Names)",
            name="sa_name_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
     
        pSearchLength=arcpy.Parameter(
            displayName="Maximum distance between centroids and edge of SubArea",
            name="search_length",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")      
                                  
        params = [pUPGDB, pInSALayer, pLongName, pSAIDField, pSANameField, pSearchLength]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[1].value:
            upgdb = parameters[0].valueAsText
            SALayer = parameters[1].valueAsText
            parameters[3].filter.list = uiut.ReturnFieldListFromFC2(SALayer)
            parameters[4].filter.list = uiut.ReturnFieldListFromFC2(SALayer)
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPlanGDB = parameters[0].valueAsText
        InSALayer = parameters[1].valueAsText
        LongName = parameters[2].valueAsText
        SAIDField = parameters[3].valueAsText
        SANameField = parameters[4].valueAsText
        SearchLength = parameters[5].valueAsText
        
        LayerManagement.ImportSALayer(InSALayer, UPlanGDB, LongName, SAIDField, SANameField, SearchLength)

        return

class ImportRedevTable(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "7. Import Redevelopment Table"
        self.description = "Imports an redevelopment table to the geodatabase"
        self.canRunInBackground = False
        self.category = "A. Data Loading"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB=arcpy.Parameter(
            displayName="UPlan File Geodatabase",
            name="up_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        pRedevTable=arcpy.Parameter(
            displayName="Redevelopment Table",
            name="redev_table",
            datatype="DETable",
            parameterType="Required",
            direction="Input")
        pLongName=arcpy.Parameter(
            displayName="Descriptive Name for the Table",
            name="desc_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input") 
        pPopField=arcpy.Parameter(
            displayName="Field within the table that contains the population total",
            name="pop_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input") 
        pEmpField=arcpy.Parameter(
            displayName="Field within the table that contains the employment total",
            name="emp_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input") 
        
        params = [pUPGDB,pRedevTable,pLongName,pPopField,pEmpField]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[1].value:
            upgdb = parameters[0].valueAsText
            RedevTable = parameters[1].valueAsText
            parameters[3].filter.list = uiut.ReturnFieldListFromFC2(RedevTable)
            parameters[4].filter.list = uiut.ReturnFieldListFromFC2(RedevTable)
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPlanGDB = parameters[0].valueAsText
        InRedevTable = parameters[1].valueAsText
        LongName = parameters[2].valueAsText
        PopField = parameters[3].valueAsText
        EmpField = parameters[4].valueAsText
        
        LayerManagement.ImportReDevTable(InRedevTable, UPlanGDB, LongName, PopField, EmpField)
        
        return

# class MakePickle(object):
#     def __init__(self):
#         """Define the tool (tool name is the name of the class)."""
#         self.label = "1. Make UPlan Configuration Pickle File"
#         self.description = ""
#         self.canRunInBackground = False
#         self.category = "B. Model Configuration"
# 
#     def getParameterInfo(self):
#         """Define parameter definitions"""
#         pUPGDB = arcpy.Parameter(
#             displayName="UPlan geodatabase",
#             name="UPGDB",
#             datatype="DEWorkspace",
#             parameterType="Required",
#             direction="Input")
#         params = [pUPGDB]
#         return params
# 
#     def isLicensed(self):
#         """Set whether tool is licensed to execute."""
#         return True
# 
#     def updateParameters(self, parameters):
#         """Modify the values and properties of parameters before internal
#         validation is performed.  This method is called whenever a parameter
#         has been changed."""
#         return
# 
#     def updateMessages(self, parameters):
#         """Modify the messages created by internal validation for each tool
#         parameter.  This method is called after internal validation."""
#         if parameters[0].value:
#             if uiut.CheckIfFGDB(parameters[0].value)==False:
#                 parameters[0].setErrorMessage("You must select a file geodatabase")
#         return
# 
#     def execute(self, parameters, messages):
#         """The source code of the tool."""
#         UPGDB = parameters[0].valueAsText
#         splitpath = uiut.SplitPath(UPGDB)
#         messages.addMessage("Reading Configuration from Database")
#         UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
#         messages.addMessage("Writing Pickle")
#         uiut.MakePickle(UPConfig, UPGDB)
#         messages.addMessage("Pickle Written")
#         
#         return

class RemoveTimeStep(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Remove a Timestep"
        self.description = "Remove a Time Step from the configuration. Note, this cannot be undone and removes all traces of the time step."
        self.canRunInBackground = False
        self.category = "B. Model Configuration"

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSShortName = arcpy.Parameter(
            displayName="Time Step To Remove",
            name="TSShortName",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pTSShortName.filter.list = ["Select a UPlan Geodatabase to get a list of time steps"]
        
        params = [pUPGDB,pTSShortName]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            pUPGDB = parameters[0].valueAsText
            picklepath = "\\".join([pUPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        upgdb = parameters[0].valueAsText
        picklepath = "\\".join([upgdb,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        
        # Remove the timestep
        UPConfig.pop(ts,None)
        
        for TimeStep in UPConfig['TimeSteps']:
            if TimeStep[0] == ts:
                UPConfig['TimeSteps'].remove(TimeStep)
                messages.addMessage("Removed Timestep: {ts},{tsln}".format(ts=TimeStep[0],tsln=TimeStep[1]))
                break
         # Write out the pickle
        uiut.MakePickle(UPConfig, upgdb)
        
        # Write out to tables
        upc.WriteUPConfigToGDB(UPConfig)
        
        return

class AddTimeStep(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Add A Timestep"
        self.description = "Add a Timestep"
        self.canRunInBackground = False
        self.category = "B. Model Configuration"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSLongName = arcpy.Parameter(
            displayName="TimeStep Descriptive Name",
            name="TSLongName",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pTSShortName = arcpy.Parameter(
            displayName="TimeStep Code",
            name="TSShortName",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pTSPosition = arcpy.Parameter(
            displayName="TimeStep Position",
            name="TSPosition",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        
        pGPLayer = arcpy.Parameter(
            displayName="General Plan for this TimeStep",
            name="GPLayer",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pGPField = arcpy.Parameter(
            displayName="Field in General Plan Layer that contains the categories",
            name="GPField",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        params = [pUPGDB,pTSLongName,pTSShortName,pTSPosition,pGPLayer,pGPField]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            upgdb = parameters[0].valueAsText
            parameters[4].filter.list = uiut.ReturnValuesFromLayersTable(upgdb, 'GeneralPlan')
        
        if parameters[4].value:
            upgdb = parameters[0].valueAsText
            GPLayer = (parameters[4].valueAsText).split('(')[0][:-1]
            parameters[5].filter.list = uiut.ReturnFieldListFromFC(upgdb,GPLayer)
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        
            if parameters[2].value:
                if uiut.CheckIfTSInFGDB(str(parameters[0].value), str(parameters[2].value)):
                    parameters[2].setErrorMessage("The short name must be unique. See the upc_timesteps table.")
                    
            if parameters[3].value:
                if int(parameters[3].value) < 1:
                    parameters[3].setErrorMessage("Position must be at least 1")
                  
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # For running 
        UPGDB = parameters[0].valueAsText
        TSLongName = parameters[1].valueAsText
        TSShortName = parameters[2].valueAsText
        TSPosition = int(parameters[3].valueAsText)
        GPLayer = (parameters[4].valueAsText).split('(')[0][:-1]
        GPField = parameters[5].valueAsText
        
        messages.addMessage("Adding Time Step")
        # Check for Pickle
        picklepath =  "\\".join([UPGDB,"UPConfig.p"])
        if uiut.CheckForPickle(picklepath):
            UPConfig = uiut.LoadPickle(picklepath)
            # add to TimeStep list in the correct order
            TimeSteps = UPConfig['TimeSteps']
            if not len(TimeSteps) == 0:
                UPConfig['TimeSteps'] = uiut.InsertToList(TimeSteps, [TSShortName,TSLongName], TSPosition)
            else:
                UPConfig['TimeSteps'] = [[TSShortName,TSLongName]]
            
            # Add empty TS dictionary to hold everything else. 
            UPConfig[TSShortName] = uiut.MakeTemplateTimeStep(GPLayer,GPField)
            
            # Write out the pickle
            uiut.MakePickle(UPConfig, UPGDB)
            
            # Write out to tables
            upc.WriteUPConfigToGDB(UPConfig)
            
            messages.addMessage("Time step added, remember to configure the related attractors, discouragers, generalplans, etc..")
        else:
            messages.addMessage("Unable To Add Time Step")
            
        return

class AddLandUse(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3. Add Land Use"
        self.description = ""
        self.canRunInBackground = False
        self.category = "B. Model Configuration"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pLUShortName = arcpy.Parameter(
            displayName="Land Use Code",
            name="LUShortName",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pLULongName = arcpy.Parameter(
            displayName="Land Use Descriptive Name",
            name="LULongName",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pLUType = arcpy.Parameter(
            displayName="Land Use Type",
            name="LUType",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pLUType.filter.list = ["Residential","Employment"]
        
        pLUAlloc = arcpy.Parameter(
            displayName="Allocation Mode",
            name="LUAlloc",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pLUAlloc.filter.list = ["Normal","Random"]
        
        
        params = [pUPGDB,pLUShortName,pLULongName,pLUType,pLUAlloc]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        
        if parameters[0].value == True:
            gdb = parameters[0].valueAsText
            if uiut.CheckIfFGDB(gdb)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        if parameters[1].altered == True:
            gdb = parameters[0].valueAsText
            picklepath =  "\\".join([gdb,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            if parameters[1].valueAsText in UPConfig['LUPriority']:
                parameters[1].setErrorMessage("The land use short name already exists")
        
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # For running 
        pUPGDB = parameters[0].valueAsText
        pLUShortName = parameters[1].valueAsText
        pLULongName = parameters[2].valueAsText
        pLUType = parameters[3].valueAsText
        pLUAlloc = parameters[4].valueAsText
        
        messages.addMessage("Adding Land Use")
        # Check for Pickle
        picklepath =  "\\".join([pUPGDB,"UPConfig.p"])
        if uiut.CheckForPickle(picklepath):
            UPConfig = uiut.LoadPickle(picklepath)
            # add to TimeStep list in the correct order
            UPConfig['LUPriority'].append(pLUShortName)
            
            UPConfig['LUNames'][pLUShortName] = pLULongName
            
            if pLUAlloc == 'Normal':
                UPConfig['AllocMethods'][pLUShortName] = 1
            elif pLUAlloc == 'Random':
                UPConfig['AllocMethods'][pLUShortName] = 2
            else:
                messages.addError("Unrecognized Allocation Type (Normal or Random)")
                
            if pLUType == "Residential":
                UPConfig['LUTypes'][pLUShortName] = "res"
            elif pLUType == "Employment":
                UPConfig['LUTypes'][pLUShortName] = "emp"
            else:
                messages.addError("Unrecognized Land Use Type (Residential or Employment)")
                
            # Add empty TS dictionary to hold everything else.
            for TimeStep in UPConfig['TimeSteps']:
                ts = TimeStep[0]
                
                # Empty Demand
                for SubArea in UPConfig['Subareas']:
                    sa = SubArea['sa']
                    if sa not in UPConfig[ts]['Demand'].keys():
                        UPConfig[ts]['Demand'][sa] = {}
                    UPConfig[ts]['Demand'][sa][pLUShortName] = 0.0
                
                # General plan
                UPConfig[ts]['gplu'][pLUShortName] = []
                
                # Constraints
                UPConfig[ts]['cweights'][pLUShortName] = {}
                
                # Attractors
                UPConfig[ts]['aweights'][pLUShortName] = {}
                 
            # Write out the pickle
            uiut.MakePickle(UPConfig, pUPGDB)
            
            # Write out to tables
            upc.WriteUPConfigToGDB(UPConfig)
            
            messages.addMessage("Land use added, remember to configure the related attractors, discouragers, generalplans, etc..")
        else:
            messages.addMessage("Unable To Add Land Use")
            
        return

class RemoveLandUse(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "4. Remove Land Use"
        self.description = ""
        self.canRunInBackground = False
        self.category = "B. Model Configuration"

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pLUShortName = arcpy.Parameter(
            displayName="Land Use To Remove",
            name="LUShortName",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        params = [pUPGDB,pLUShortName]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.LUNameLookup(UPConfig)
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        pUPGDB = parameters[0].valueAsText
        picklepath =  "\\".join([pUPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        pLUShortName = uiut.LUCodeLookup(parameters[1].valueAsText, UPConfig)
            
        for TimeStep in UPConfig['TimeSteps']:
            ts = TimeStep[0]
            
            # Empty Demand
            for SubArea in UPConfig['Subareas']:
                sa = SubArea['sa']
                del UPConfig[ts]['Demand'][sa][pLUShortName] 
                
            # General Plan
            del UPConfig[ts]['gplu'][pLUShortName]
            
            # Constraints
            del UPConfig[ts]['cweights'][pLUShortName]
            
            # Attractors
            del UPConfig[ts]['aweights'][pLUShortName]
        
        # long name listing
        del UPConfig['LUNames'][pLUShortName]
        
        # LU Type
        del UPConfig['LUTypes'][pLUShortName]
        
        # Allocation Type
        del UPConfig['AllocMethods'][pLUShortName]
        
        # LU Priority
        UPConfig['LUPriority'].remove(pLUShortName)
        
        # Write out the pickle
        uiut.MakePickle(UPConfig, pUPGDB)
        
        # Write out to tables
        upc.WriteUPConfigToGDB(UPConfig)
        
        messages.addMessage("Land use removed")
            
        return

class SetLandUsePriority(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "5. Set Land Use Priority"
        self.description = "Reorder Landuses"
        self.canRunInBackground = False
        self.category = "B. Model Configuration"

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pLU = arcpy.Parameter(
            displayName="Set Land Use Priority",
            name="Constraints",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pLU.columns = [['String', 'Land Use']]
        
        params = [pUPGDB,pLU]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        hasPickle = False

        if parameters[0].value:
            pUPGDB = parameters[0].valueAsText
            picklepath = "\\".join([pUPGDB,"UPConfig.p"])
            if uiut.CheckForPickle(picklepath):
                UPConfig = uiut.LoadPickle(picklepath)
                hasPickle = True
            
        if parameters[1].values and hasPickle:
            values = parameters[1].values
            luorder = [uiut.LUCodeLookup(luo[0],UPConfig)for luo in values]
            UPConfig['PriorLUPrioirty'] = UPConfig['LUPriority']
            UPConfig['LUPriority'] = luorder
            uiut.MakePickle(UPConfig, pUPGDB)
                    
        if hasPickle:
            LandUseList = UPConfig['LUPriority']
            values = [[str(UPConfig['LUNames'][LUCode])] for LUCode in LandUseList]
            parameters[1].values = values
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
                 
            else:
                picklepath =  "\\".join([str(parameters[0].valueAsText),"UPConfig.p"])
                if uiut.CheckForPickle(picklepath):
                    UPConfig = uiut.LoadPickle(picklepath)
                else:
                    parameters[0].setErrorMessage("UPlan configuration pickle missing or damaged: Please Run 'Make Pickle'")
        
#         if parameters[1].values and UPConfig:
#             values = parameters[1].values
#             if 'PriorLUPriority' in UPConfig.keys():
#                 for value in values:
#                     if str(value[0]) not in UPConfig['PriorLUPriority']:
#                         parameters[1].setErrorMessage("The following land use is not recognize: {lu}".format(lu=value))
#                 
#                 for lu in UPConfig['PriorLUPriority']:
#                     vals = [str(luv[0]) for luv in values]
#                     if str(lu) not in vals:
#                         parameters[1].setErrorMessage("The following land use is missing: {lu}".format(lu=str(lu)))
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        UPGDB = parameters[0].valueAsText
        
        picklepath =  "\\".join([UPGDB,"UPConfig.p"])
        
        if uiut.CheckForPickle(picklepath):
            UPConfig = uiut.LoadPickle(picklepath)
            values = parameters[1].values
            luorder = [uiut.LUCodeLookup(luo[0],UPConfig) for luo in values]
            UPConfig['LUPriority'] = luorder
            if 'PriorLUPriority' in UPConfig.keys():
                del UPConfig['PriorLUPriority']
            
            # Write out the pickle
            uiut.MakePickle(UPConfig, UPGDB)
            
            # Write out to tables
            upc.WriteUPConfigToGDB(UPConfig)
        
        return
    
class SetConstraints(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3. Set Constraint Layers"
        self.description = "Set the list of constraints to be available for each time step"
        self.canRunInBackground = False
        self.category = "C. Scenario Settings"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTimeStep = arcpy.Parameter(
            displayName="Select Time Step",
            name="TimeStep",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pTimeStep.filter.list = ["Select your UPlan Geodatabase"]
        
        pConstraints = arcpy.Parameter(
            displayName="Set Constraint Availability",
            name="Constraint Availability",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pConstraints.columns = [['String', 'Layer'], ['String', 'Description'], ['String', 'Availability (Yes/No)']]
        
        params = [pUPGDB,pTimeStep,pConstraints]
        return params        
    
    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
                
        if parameters[1].altered and parameters[2].values == None:
            # Get list of constraint layers
            conlist = []
            ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            tclist = [str(tslyr) for tslyr in UPConfig[ts]['constraints']]
            inlist = []
            whereClause = "Role = 'Constraint'"
            cur = arcpy.SearchCursor(os.path.join(UPGDB,"upc_layers"), whereClause, fields = "FCName;LongName")
            for row in cur:
                lyr = row.getValue("FCName")
                LongName = row.getValue("LongName")
                if str(lyr) not in inlist:
                    inlist.append(str(lyr))
                    if str(lyr) in tclist:
                        conlist.append([str(lyr),LongName,"Yes"])
                    else:
                        conlist.append([str(lyr),LongName,"No"])
            parameters[2].values = conlist
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)

        messages.addMessage("Updating Active Constraint List")
        values = parameters[2].values
        conlist = []
        for val in values:
            if str(val[2][:1]).lower() == "y":
                conlist.append(val[0])
        UPConfig[ts]['constraints'] = conlist
        conlist = None
        
        # Write out the pickle
        uiut.MakePickle(UPConfig, UPGDB)
         
        # Write out to tables
        upc.WriteUPConfigToGDB(UPConfig)
        messages.addMessage("Constraint List Updated")
        
        return

class SetConstraintWeights(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "4. Set Constraint Weights"
        self.description = ""
        self.canRunInBackground = False
        self.category = "C. Scenario Settings"

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTimeStep = arcpy.Parameter(
            displayName="Select Time Step",
            name="TimeStep",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pTimeStep.filter.list = ["Select your UPlan Geodatabase"]
        
        pLandUse = arcpy.Parameter(
            displayName="Select Land Use",
            name="LandUse",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pLandUse.filter.list = ["Select your UPlan Geodatabase"]
        
        pConstraints = arcpy.Parameter(
            displayName="Set Constraint Weights",
            name="Constraints",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pConstraints.columns = [['String', 'Constraint'], ['Double', 'Weight']]

        params = [pUPGDB,pTimeStep,pLandUse,pConstraints]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        hasPickle = False
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
            parameters[2].filter.list = uiut.LUNameLookup(UPConfig)
            hasPickle = True
        
        hasTSandLU = False
        if parameters[1].value and parameters[2].value:
            ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            lu = uiut.LUCodeLookup(parameters[2].valueAsText, UPConfig)
            hasTSandLU = True
        
        if hasTSandLU and hasPickle and parameters[3].values == None:
            #constraints = UPConfig[ts]['constraints']
            ConDescNames = uiut.ConstraintNameLookup(UPConfig, ts, UPGDB)
            cweights = []
            for ConDescName in ConDescNames:
                constraint = uiut.GetLayerNameFromLayersTable(ConDescName, 'Constraint', UPGDB)
                if lu in UPConfig[ts]['cweights'].keys():
                    if constraint in UPConfig[ts]['cweights'][lu]:
                        cweight = [ConDescName,(UPConfig[ts]['cweights'][lu][constraint])*100]
                    else:
                        cweight = [ConDescName,0.0]
                else:
                    cweight = [ConDescName,0.0]
                cweights.append(cweight)
            
            parameters[3].values = cweights
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        
        if parameters[3].value:
            for val in parameters[3].value:
                if val[1] > 100 or val[1] < 0:
                    parameters[3].setErrorMessage("Weights must be between 0 and 100")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        #pLUShortName = parameters[1].valueAsText
         
        picklepath =  "\\".join([UPGDB,"UPConfig.p"])
        if uiut.CheckForPickle(picklepath):
            UPConfig = uiut.LoadPickle(picklepath)
            ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            lu = uiut.LUCodeLookup(parameters[2].valueAsText, UPConfig)
             
            values = parameters[3].values
            for val in values:
                cweight = (val[1])/100
                ConLayerName = uiut.GetLayerNameFromLayersTable(val[0], 'Constraint', UPGDB)
                
                if lu in UPConfig[ts]['cweights'].keys():
                    UPConfig[ts]['cweights'][lu][ConLayerName] = cweight
                else:
                    UPConfig[ts]['cweights'].update({lu:{ConLayerName:cweight}})
             
            # Write out the pickle
            uiut.MakePickle(UPConfig, UPGDB)
             
            # Write out to tables
            upc.WriteUPConfigToGDB(UPConfig)
             
            messages.addMessage("Constraints Updated")
        else:
            messages.addMessage("Unable To Change Constraints, run the make pickle tool")

        return

class SetAttractors(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Set Attractor Layers"
        self.description = "Set the list of attractors to be available for each time step"
        self.canRunInBackground = False
        self.category = "C. Scenario Settings"

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTimeStep = arcpy.Parameter(
            displayName="Select Time Step",
            name="TimeStep",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pTimeStep.filter.list = ["Select your UPlan Geodatabase"]
        
        pAttractors = arcpy.Parameter(
            displayName="Set Attractor Availability",
            name="Attractor Availability",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pAttractors.columns = [['String', 'Layer'], ['String', 'Description'], ['String', 'Availability (Yes/No)']]
        
        params = [pUPGDB,pTimeStep,pAttractors]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
                
        if parameters[1].altered and parameters[2].values == None:
            # Get list of attraction layers
            attlist = []
            ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            tclist = [str(tslyr) for tslyr in UPConfig[ts]['attractors']]
            inlist = []
            whereClause = "Role = 'Attractor'"
            cur = arcpy.SearchCursor(os.path.join(UPGDB,"upc_layers"), whereClause, fields = "FCName;LongName")
            for row in cur:
                lyr = row.getValue("FCName")
                LongName = row.getValue("LongName")
                if str(lyr) not in inlist:
                    inlist.append(str(lyr))
                    if str(lyr) in tclist:
                        attlist.append([str(lyr),LongName,"Yes"])
                    else:
                        attlist.append([str(lyr),LongName,"No"])
            parameters[2].values = attlist
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)

        messages.addMessage("Updating Active Attractor List")
        values = parameters[2].values
        attlist = []
        for val in values:
            if str(val[2][:1]).lower() == "y":
                attlist.append(val[0])
        UPConfig[ts]['attractors'] = attlist
        attlist = None
         
        # Write out the pickle
        uiut.MakePickle(UPConfig, UPGDB)
         
        # Write out to tables
        upc.WriteUPConfigToGDB(UPConfig)
        messages.addMessage("Attractor List Updated")
            
        return

class SetAttractorWeights(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Set Attractor Weights"
        self.description = ""
        self.canRunInBackground = False
        self.category = "C. Scenario Settings"

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTimeStep = arcpy.Parameter(
            displayName="Select Time Step",
            name="TimeStep",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pTimeStep.filter.list = ["Select your UPlan Geodatabase"]
        
        pLandUse = arcpy.Parameter(
            displayName="Select Land Use",
            name="LandUse",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pLandUse.filter.list = ["Select your UPlan Geodatabase"]
        
        pAttractor = arcpy.Parameter(
            displayName="Set Attraction Layer",
            name="Attractor",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pAttractor.filter.list = ["Select your UPlan Geodatabase and TimeStep"]
        
        pAWeights = arcpy.Parameter(
            displayName="Set Attraction Weights",
            name="Attraction Weights",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pAWeights.columns = [['Double', 'Distance'], ['Double', 'Weight']]
        
        params = [pUPGDB,pTimeStep,pLandUse,pAttractor,pAWeights]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        hasPickle = False
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            #parameters[1].filter.list = [ts[0] for ts in UPConfig['TimeSteps']]
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
            #parameters[2].filter.list = UPConfig['LUPriority']
            parameters[2].filter.list = uiut.LUNameLookup(UPConfig)
            hasPickle = True
        
        hasTSandLU = False
        if parameters[1].value and parameters[2].value:
            #ts = parameters[1].valueAsText
            ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            #lu = parameters[2].valueAsText
            lu = uiut.LUCodeLookup(parameters[2].valueAsText, UPConfig)
            hasTSandLU = True
            
        if hasTSandLU and hasPickle:
            # get attractors by land use
            #parameters[3].filter.list = UPConfig[ts]['attractors']
            parameters[3].filter.list = uiut.AttractorNameLookup(UPConfig, ts, UPGDB)
            
        # Load the attractors weights
        if parameters[3].value and hasTSandLU and hasPickle and parameters[4].values == None:
            UPConfig = uiut.LoadPickle(picklepath)
            AttDescName = parameters[3].valueAsText
            attractor = uiut.GetLayerNameFromLayersTable(AttDescName, 'Attractor', UPGDB)
            #attractor = parameters[3].valueAsText 
            
            awtvals = []
            if attractor in UPConfig[ts]['aweights'][lu].keys():
                aweights =  UPConfig[ts]['aweights'][lu][attractor]
            
                for wt in aweights:
                    awtvals.append([wt[0],wt[1]])
            else:
                awtvals.append([0,0])
            parameters[4].values=awtvals
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        
        picklepath =  "\\".join([UPGDB,"UPConfig.p"])
        if uiut.CheckForPickle(picklepath):
            UPConfig = uiut.LoadPickle(picklepath)
            #ts = parameters[1].valueAsText
            #lu = parameters[2].valueAsText
            #attractor = parameters[3].valueAsText
            ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            lu = uiut.LUCodeLookup(parameters[2].valueAsText, UPConfig)
            attractor = uiut.GetLayerNameFromLayersTable(parameters[3].valueAsText, 'Attractor', UPGDB)
            
            # get attraction weights and submit them to UPConfig.
            values = parameters[4].values
            atweights = [[val[0],val[1]] for val in values]
            
            # sort atweights to be safe
            atweights = sorted(atweights, key=itemgetter(0))
            UPConfig[ts]['aweights'][lu][attractor] = atweights
            
            # Write out the pickle
            uiut.MakePickle(UPConfig, UPGDB)
            
            # Write out to tables
            upc.WriteUPConfigToGDB(UPConfig)
            
            messages.addMessage("Attraction Weights Updated")
        else:
            messages.addMessage("Unable To Update Attraction Weights, run the make pickle tool")
        
        return

class SetGeneralPlan(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "5. Update General Plan"
        self.description = "Updates the general plan layer to be used in each Time Step"
        self.canRunInBackground = False
        self.category = "C. Scenario Settings"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTimeStep = arcpy.Parameter(
            displayName="Select Time Step",
            name="TimeStep",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pTimeStep.filter.list = ["Select your UPlan Geodatabase"]
        
        pGeneralPlan = arcpy.Parameter(
            displayName="Select General Plan",
            name="General Plan",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pGeneralPlan.filter.list = ["Select your Time Step"]
        
        pGeneralPlanField = arcpy.Parameter(
            displayName="Select General Plan Field",
            name="General Plan Field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pGeneralPlan.filter.list = ["Select your General Plan layer"]
#         pGeneralPlanField.parameterDependencies = [pGeneralPlan.name]
        
        params = [pUPGDB,pTimeStep,pGeneralPlan,pGeneralPlanField]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
        if parameters[1].value:
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            whereClause = "Role = 'GeneralPlan'"
            cur = arcpy.SearchCursor(os.path.join(UPGDB,'upc_layers'),whereClause,fields="FCName;LongName")
            vals = []
            for row in cur:
                if str(row.getValue("LongName")) not in vals:
                    vals.append(str(row.getValue("LongName")))
            parameters[2].filter.list = vals
        if parameters[2].value:
            GPLayer = uiut.GetLayerNameFromLayersTable(parameters[2].valueAsText, 'GeneralPlan', UPGDB)
            parameters[3].filter.list = uiut.ReturnFieldListFromFC(UPGDB,GPLayer)
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            if parameters[1].value and parameters[2].value and parameters[3].value:
                messages.addMessage("Setting General Plan")
                ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
                GPLayer = uiut.GetLayerNameFromLayersTable(parameters[2].valueAsText, 'GeneralPlan', UPGDB)
                UPConfig[ts]['gp']= [GPLayer, parameters[3].valueAsText]
                
                UPConfig[ts]['gplu'] = {}
                LUCodes = UPConfig['LUPriority']
                for LUCode in LUCodes:
                    UPConfig[ts]['gplu'][LUCode] = []
            
                # Write out the pickle
                uiut.MakePickle(UPConfig, UPGDB)
                
                # Write out to tables
                upc.WriteUPConfigToGDB(UPConfig)
                
                messages.addMessage("General Plan Set")
            else:
                messages.addMessage("Unable to set general plan, check for missing values")
        
        return

class SetGeneralPlanSettings(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "6. Set General Plan Settings"
        self.description = "Set the general plan classes that a land use can use for a time step"
        self.canRunInBackground = False
        self.category = "C. Scenario Settings"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTimeStep = arcpy.Parameter(
            displayName="Select Time Step",
            name="TimeStep",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pTimeStep.filter.list = ["Select your UPlan Geodatabase"]
        
        pLUCode = arcpy.Parameter(
            displayName="Select a Land Use Code",
            name="LUCode",
            datatype="GPString",  #GPValueTable?? multiValue with a ValueList filter?
            parameterType="Required",
            direction="Input")
        
        pGPCats = arcpy.Parameter(
            displayName="General Plan Category Availability",
            name="General Plan Availability",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pGPCats.columns = [['String', 'General Plan Category'], ['String', 'Availability (Yes/No)']]

        params = [pUPGDB,pTimeStep,pLUCode,pGPCats]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
            parameters[2].filter.list = uiut.LUNameLookup(UPConfig)
            
        if parameters[1].altered and parameters[2].altered and parameters[3].values == None:
            # Get list of GP codes
            #UPGDB = parameters[0].valueAsText
            TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            LUCode = uiut.LUCodeLookup(parameters[2].valueAsText, UPConfig)
            
            GPLUlist = []
            GPLayer = os.path.join(UPGDB, UPConfig[TSCode]['gp'][0])
            GPField = UPConfig[TSCode]['gp'][1]
            GPCats = uiut.ListUniqueFieldValues(GPLayer, GPField)
            ExistingLU = UPConfig[TSCode]['gplu'][LUCode]
            if len(ExistingLU) != 0:
                for GPCat in GPCats:
                    if GPCat in ExistingLU:
                        GPLUlist.append([GPCat,'Yes'])
                    else:
                        GPLUlist.append([GPCat,'No'])
            else:
                for GPCat in GPCats:
                    GPLUlist.append([GPCat,'No'])
            parameters[3].values = GPLUlist
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        
        TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        LUCode = uiut.LUCodeLookup(parameters[2].valueAsText, UPConfig)
            
        messages.addMessage("Updating General Plan Look Up List")
        values = parameters[3].values
        GPlist = []
        for val in values:
            if str(val[1][:1]).lower() == "y":
                GPlist.append(val[0])
        UPConfig[TSCode]['gplu'][LUCode] = GPlist
        GPlist = None
         
        # Write out the pickle
        uiut.MakePickle(UPConfig, UPGDB)
         
        # Write out to tables
        upc.WriteUPConfigToGDB(UPConfig)
        messages.addMessage("Look Up List Updated")        
        return

class SetMixedUse(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "7. Edit Mixed Use Combinations"
        self.description = "Set the mixed use settings for general plan classes by timestep"
        self.canRunInBackground = False
        self.category = "C. Scenario Settings"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSCode = arcpy.Parameter(
            displayName="Select Time Step",
            name="TimeStep",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pTSCode.filter.list = ["Select your UPlan Geodatabase"]
        
        pGPCat = arcpy.Parameter(
            displayName="Select a General Plan Category",
            name="GPCat",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pExistingMUCombos = arcpy.Parameter(
            displayName="Select a Mixed Use Combination to Edit",
            name="ExistingMUCombo",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pLUCodes = arcpy.Parameter(
            displayName="Land Use Codes Allowed for Mixed Use Category",
            name="MixedUseLUCodes",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pLUCodes.columns = [['String', 'Land Use Name'], ['String', 'Availability (Yes/No)']]

        params = [pUPGDB,pTSCode,pGPCat,pExistingMUCombos,pLUCodes]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
            
        if parameters[1].altered:
            TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)   
            GPLayer = os.path.join(UPGDB, UPConfig[TSCode]['gp'][0])
            GPField = UPConfig[TSCode]['gp'][1]
            GPCats = uiut.ListUniqueFieldValues(GPLayer, GPField)
            parameters[2].filter.list = GPCats
            
        if parameters[2].altered:
            GPCat = parameters[2].valueAsText
            
            MUComboList = []
            ExistingMU = UPConfig[TSCode]['mixeduse']
            if GPCat in ExistingMU.keys():
                MUCombos = UPConfig[TSCode]['mixeduse'][GPCat]
                if len(MUCombos) != 0:
                    #there is at least one mixed use group for the GPCat
                    for x in range(0,len(MUCombos)):
                        LUCodes = MUCombos[x]
                        MUComboList.append(uiut.LinkMUCodes(UPConfig, LUCodes))
            MUComboList.append('Create a New Combination')
            parameters[3].filter.list = MUComboList
            
        if parameters[3].altered and parameters[4].values == None:
            MUCombo = parameters[3].valueAsText
            MUCodeList = MUCombo.split('-')
            
            ExistingLUs = UPConfig['LUPriority']
            
            MULUlist = []
            for LUCode in ExistingLUs:
                LUName = UPConfig['LUNames'][LUCode]
                if MUCombo != 'Create a New Combination':
                    if LUCode in MUCodeList:
                        MULUlist.append([LUName,'Yes'])
                    else:
                        MULUlist.append([LUName,'No'])
                else:
                    MULUlist.append([LUName,'No'])
            parameters[4].values = MULUlist
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        
        TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        GPCat = parameters[2].valueAsText
        InputMUCombo = parameters[3].valueAsText
        InputMUComboList = InputMUCombo.split('-')
        
        messages.addMessage("Updating Mixed Use Combination")
        values = parameters[4].values
        MUlist = []
        for val in values:
            if str(val[1][:1]).lower() == "y":
                LUCode = uiut.LUCodeLookup(val[0], UPConfig)
                MUlist.append(LUCode)
        
        MUComboList = []
        ExistingMUs = UPConfig[TSCode]['mixeduse']
        if GPCat in ExistingMUs.keys():
            MUCombos = UPConfig[TSCode]['mixeduse'][GPCat]
            if len(MUCombos) != 0:
                #there is at least one mixed use group for the GPCat
                for x in range(0,len(MUCombos)):
                    LUCodes = MUCombos[x]
                    MUComboList.append(LUCodes)
        
        if InputMUCombo != 'Create a New Combination':
            MUComboList.remove(InputMUComboList)
        
        if not MUlist in MUComboList:
            if len(MUlist) != 0:
                MUComboList.append(MUlist)
        UPConfig[TSCode]['mixeduse'][GPCat] = MUComboList
        MUlist = None
         
        # Write out the pickle
        uiut.MakePickle(UPConfig, UPGDB)
         
        # Write out to tables
        upc.WriteUPConfigToGDB(UPConfig)
        messages.addMessage("Look Up List Updated")  
        
        return

class PreCalcSubareas(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Precalculate Subareas"
        self.description = "Build subarea-polygon lookup information"
        self.canRunInBackground = False
        self.category = "E. Precalculations"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        params = [pUPGDB]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
#         picklepath = "\\".join([UPGDB,"UPConfig.p"])
#         UPConfig = uiut.LoadPickle(picklepath)
        splitpath = uiut.SplitPath(UPGDB)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        messages.addMessage("Cleaning up Subareas")
        Utilities.UPCleanup_Subareas(UPConfig)
        messages.addMessage("Calculating Subareas")
        CalcSubarea.CalcSA(UPConfig)
        messages.addMessage("Subareas Complete")

        return

class PreCalcGeneralPlans(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Precalculate General Plans"
        self.description = "Build General Plan-polygon lookup information"
        self.canRunInBackground = False
        self.category = "E. Precalculations"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        params = [pUPGDB]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
                UPGDB = parameters[0].valueAsText
                picklepath = "\\".join([UPGDB,"UPConfig.p"])
                UPConfig = uiut.LoadPickle(picklepath)

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
#         UPGDB = r"..\\testing\calaveras.gdb"
#         picklepath = "\\".join([UPGDB,"UPConfig.p"])
#         UPConfig = uiut.LoadPickle(picklepath)
        splitpath = uiut.SplitPath(UPGDB)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        messages.addMessage("Cleaning up General Plans")
        Utilities.UPCleanup_GeneralPlans(UPConfig)
        messages.addMessage("Calculating General Plans")
        CalcGeneralPlans.CalcGP(UPConfig)
        messages.addMessage("General Plans Complete")

        return

class PreCalcConstraints(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3. Precalculate Constraints"
        self.description = "Calculate Developable Space based on Constraints"
        self.canRunInBackground = False
        self.category = "E. Precalculations"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        params = [pUPGDB]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
                UPGDB = parameters[0].valueAsText
                picklepath = "\\".join([UPGDB,"UPConfig.p"])
                UPConfig = uiut.LoadPickle(picklepath)

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
#         UPGDB = r"..\\testing\calaveras.gdb"
#         picklepath = "\\".join([UPGDB,"UPConfig.p"])
#         UPConfig = uiut.LoadPickle(picklepath)
        splitpath = uiut.SplitPath(UPGDB)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        messages.addMessage("Cleaning up Constraints")
        Utilities.UPCleanup_Constraints(UPConfig)
        messages.addMessage("Calculating Constraints")
        CalcConstraints.CalcConstraints(UPConfig)
        messages.addMessage("Constraints Complete")

        return

class PreCalcWeights(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "4. Precalculate Attractor Weights"
        self.description = "Calculate Distances and Weights"
        self.canRunInBackground = False
        self.category = "E. Precalculations"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        pSaveDisaggWts = arcpy.Parameter(
            displayName="Save Disaggregate Weights (True/False)",
            name="SaveDisaggWts",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        pSaveDisaggWts.value = False
        params = [pUPGDB,pSaveDisaggWts]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
                UPGDB = parameters[0].valueAsText
                picklepath = "\\".join([UPGDB,"UPConfig.p"])
                UPConfig = uiut.LoadPickle(picklepath)

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        
        saveDisaggWts = parameters[1].value

        splitpath = uiut.SplitPath(UPGDB)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])

        Utilities.UPCleanup_Weights(UPConfig)

        # Get unique set of attractors
        attractors = []
        for TimeStep in UPConfig['TimeSteps']:
            newattractors = UPConfig[TimeStep[0]]['attractors']
            attractors = attractors + newattractors
        attractors = set(attractors)
        
        #if not ArcInfo license, then make sure cauculating distance with SA (not GenerateNear tool)
        if arcpy.ProductInfo() != 'ArcInfo':
            if UPConfig['DistMode'] == 'GenerateNear':
                UPConfig = uiut.ChangeDistMode(UPConfig)
        
        CalcWeights.CalcDistanceLayerMultiple(UPConfig,attractors,False) # False disables multi processing.
        
        for TimeStep in UPConfig['TimeSteps']:
#             messages.addMessage("Working on time step: {ts}".format(ts = TimeStep[0]))
            CalcWeights.GetWeightsByTs([UPConfig,TimeStep,saveDisaggWts,False]) #[UPConfig,ts,writeResults,runMulti]
            
        messages.addMessage("Weights Complete")
#         print("Done")

        return
    
class PreCalcAll(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "0. Run All Precalculations"
        self.description = "Calculate Subareas, General Plans, Constraints, Attraction Weights"
        self.canRunInBackground = False
        self.category = "E. Precalculations"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        pSaveDisaggWts = arcpy.Parameter(
            displayName="Save Disaggregate Weights (True/False)",
            name="SaveDisaggWts",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        pSaveDisaggWts.value = False
        params = [pUPGDB,pSaveDisaggWts]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        saveDisaggWts = parameters[1].value
        splitpath = uiut.SplitPath(UPGDB)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        
        # Subareas
        messages.addMessage("Cleaning up Subareas")
        Utilities.UPCleanup_Subareas(UPConfig)
        messages.addMessage("Calculating Subareas")
        CalcSubarea.CalcSA(UPConfig)
        messages.addMessage("Subareas Complete")
                
        # General Plans
        messages.addMessage("Cleaning up General Plans")
        Utilities.UPCleanup_GeneralPlans(UPConfig)
        messages.addMessage("Calculating General Plans")
        CalcGeneralPlans.CalcGP(UPConfig)
        messages.addMessage("General Plans Complete")
        
        # Constraints
        messages.addMessage("Cleaning up Constraints")
        Utilities.UPCleanup_Constraints(UPConfig)
        messages.addMessage("Calculating Constraints")
        CalcConstraints.CalcConstraints(UPConfig)
        messages.addMessage("Constraints Complete")
        
        #if not ArcInfo license, then make sure cauculating distance with SA (not GenerateNear tool)
        if arcpy.ProductInfo() != 'ArcInfo':
            if UPConfig['DistMode'] == 'GenerateNear':
                UPConfig = uiut.ChangeDistMode(UPConfig)
        # Attraction Weights
        messages.addMessage("Cleaning up Weights")
        Utilities.UPCleanup_Weights(UPConfig)
        messages.addMessage("Calculating Distances")
        # Get unique set of attractors
        attractors = []
        for TimeStep in UPConfig['TimeSteps']:
            newattractors = UPConfig[TimeStep[0]]['attractors']
            attractors = attractors + newattractors
        attractors = set(attractors)
        CalcWeights.CalcDistanceLayerMultiple(UPConfig,attractors,False) # False disables multi processing.
        
        for TimeStep in UPConfig['TimeSteps']:
            messages.addMessage("Working on time step: {ts}".format(ts = TimeStep[0]))
            CalcWeights.GetWeightsByTs([UPConfig,TimeStep,saveDisaggWts,False]) #[UPConfig,ts,writeResults,runMulti]
            
        messages.addMessage("Weights Complete")

        return

class RunAllocation(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Run Allocation"
        self.description = "Run the full allocation of UPlan."
        self.canRunInBackground = False
        self.category = "F. UPlan Run"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        pRunRedev = arcpy.Parameter(
            displayName="Run Redevelopment",
            name="run_redev",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        pRunRedev.value = False
        
        params = [pUPGDB,pRunRedev]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
                UPGDB = parameters[0].valueAsText
                picklepath = "\\".join([UPGDB,"UPConfig.p"])
                UPConfig = uiut.LoadPickle(picklepath)

        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        RunRedev = parameters[1].value
        
        splitpath = uiut.SplitPath(UPGDB)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        
        #set redev = none if RunRedev = False
        if not RunRedev:
            UPConfig['Redev'] = None
            
        messages.addMessage("Cleaning up Allocation")
        Utilities.UPCleanup_Alloc(UPConfig)
        messages.addMessage("Running Allocation")
        Allocation.Allocate(UPConfig)

        return

class ImportZonalLayer(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Import Zonal Layer"
        self.description = "This tool imports a zonal layer to the UPlan geodatabase"
        self.canRunInBackground = False
        self.category = "G. Analysis"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan File Geodatabase",
            name="up_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pInZoneLayer = arcpy.Parameter(
            displayName="Zonal Layer",
            name="zonal_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        pLongName=arcpy.Parameter(
            displayName="Zonal Layer Long Name",
            name="desc_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input")                         

        params = [pUPGDB, pInZoneLayer, pLongName]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        in_layer = parameters[1].valueAsText
        desc_name = parameters[2].valueAsText
        
        LayerManagement.ImportZonalLayer(in_layer, UPGDB, desc_name)
                       
        return

class ZonalSummary(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Perform Zonal Summary"
        self.description = "Summarize UPlan outputs by zone"
        self.canRunInBackground = False
        self.category = "G. Analysis"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSCode = arcpy.Parameter(
            displayName="Timestep",
            name="TSCode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pSumType = arcpy.Parameter(
            displayName="Type of Summary",
            name="sum_type",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pZonalDataset = arcpy.Parameter(
            displayName="Layer with Zones to Summarize By",
            name="zonal_dataset",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
         
        pZoneField = arcpy.Parameter(
            displayName="Field that Containts a Unique ID for each Zone",
            name="zone_field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pSearchLength=arcpy.Parameter(
            displayName="Maximum distance between centroids and edge of Zonal Layer",
            name="search_length",
            datatype="GPLong",
            parameterType="Required",
            direction="Input") 
        
        params = [pUPGDB,pTSCode,pSumType,pZonalDataset,pZoneField,pSearchLength]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            TSlist = uiut.TimestepNameLookup(UPConfig)
            TSlist.append('All Timesteps')
            parameters[1].filter.list = TSlist
            parameters[2].filter.list = ['Timestep Allocation Only','Cumulative Allocation','Both Timestep and Cumulative Allocation']            

            whereClause = "Role = 'ZonalSummary'"
            cur = arcpy.SearchCursor(os.path.join(UPGDB,'upc_layers'),whereClause,fields="FCName;LongName")
            vals = []
            for row in cur:
                if str(row.getValue("LongName")) not in vals:
                    vals.append(str(row.getValue("LongName")))
            parameters[3].filter.list = vals
        if parameters[3].value:
            ZoneLayer = uiut.GetLayerNameFromLayersTable(parameters[3].valueAsText, 'ZonalSummary', UPGDB)
            parameters[4].filter.list = uiut.ReturnFieldListFromFC(UPGDB,ZoneLayer)        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")        
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        SelectedTSCode = parameters[1].valueAsText
        SumType = parameters[2].valueAsText
        ZoneLayer = uiut.GetLayerNameFromLayersTable(parameters[3].valueAsText, 'ZonalSummary', UPGDB)
        ZoneField = parameters[4].valueAsText
        SearchLength = parameters[5].valueAsText
        
        #create Xwalk table
        ZonalSum.CreateXwalkTable(UPConfig, ZoneLayer, ZoneField, SearchLength)
        
        #determine the summary type
        if SumType == 'Timestep Allocation Only':
            AllocTypes = ['ts']
        elif SumType == 'Cumulative Allocation':
            AllocTypes = ['cum']
        else:
            AllocTypes = ['ts','cum']
        
        #determine the timestep or timesteps to create summary tables for
        if SelectedTSCode == 'All Timesteps':
            TSCodes = [ts[0] for ts in UPConfig['TimeSteps']]
        else:
            TSCodes = [uiut.TimestepCodeLookup(SelectedTSCode, UPConfig)]
        
        #create summary table(s)
        for TSCode in TSCodes:
            for AllocType in AllocTypes:
                ZonalSum.CreateSummaryTable(UPConfig, AllocType, TSCode, ZoneField)
                
        return
    
class SetDemographics(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Set Demographics"
        self.description = "Set the input demographics"
        self.canRunInBackground = False
        self.category = "D. Land Use Demand"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSCode = arcpy.Parameter(
            displayName="Timestep",
            name="TSCode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pBasePop = arcpy.Parameter(
            displayName="Base Population",
            name="base_pop",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        
        pFuturePop = arcpy.Parameter(
            displayName="Future Population",
            name="future_pop",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        
        pPPHH = arcpy.Parameter(
            displayName="Persons Per Household",
            name="pphh",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        
        pEPHH = arcpy.Parameter(
            displayName="Employees Per Household",
            name="ephh",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input")
        
        params = [pUPGDB,pTSCode,pBasePop,pFuturePop,pPPHH,pEPHH]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
        if parameters[1].altered:
            #the user selected a timestep...see if that timestep already has demographics
            #if so, populate the other parameters with the values in the upd_demographics table
            
            #load demand pickle if exists, or create a new one
            dpicklepath = "\\".join([UPGDB,"UPDemand.p"])
            if uiut.CheckForPickle(dpicklepath):
                UPDemand = uiut.LoadDemandPickle(dpicklepath)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                    uiut.MakeDemandPickle(UPDemand, UPGDB)
            else:
                UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                uiut.MakeDemandPickle(UPDemand, UPGDB)
                
            TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            
            if parameters[2].value == None:
                parameters[2].value = UPDemand[TSCode]['StartPop']
            if parameters[3].value == None:
                parameters[3].value = UPDemand[TSCode]['EndPop']
            if parameters[4].value == None:
                parameters[4].value = UPDemand[TSCode]['PPHH']
            if parameters[5].value == None:
                parameters[5].value = UPDemand[TSCode]['EPHH']
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")        
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        BasePop = parameters[2].value
        FuturePop = parameters[3].value
        PPHH = parameters[4].value
        EPHH = parameters[5].value
        
        CalcDem.PopulateDemoTable(UPGDB, TSCode, BasePop, FuturePop, PPHH, EPHH)
        
        #save to the demand pickle
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        uiut.MakeDemandPickle(UPDemand, UPGDB)
        
        return
    
class SetSpaceReq4Res(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2. Set Space Requirements - Residential"
        self.description = "Set the space requirements for Residential Land Use Types"
        self.canRunInBackground = False
        self.category = "D. Land Use Demand"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSCode = arcpy.Parameter(
            displayName="Timestep",
            name="TSCode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pResSpaceReq = arcpy.Parameter(
            displayName="Set Space Requirements for each LandUse",
            name="ResSpaceReq",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pResSpaceReq.columns = [['String', 'LandUse Code'], ['Double', 'Acres per Unit'], ['Double', '% Vacant'], ['Double', '% Other Space']]

        params = [pUPGDB,pTSCode,pResSpaceReq]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)

        if parameters[1].altered:
            #the user selected a timestep and land use...see if that timestep/LU already has values
            #if so, populate the other parameters with the values in the upd_reslanduses table
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            
            #load demand pickle if exists, or create a new one
            dpicklepath = "\\".join([UPGDB,"UPDemand.p"])
            if uiut.CheckForPickle(dpicklepath):
                UPDemand = uiut.LoadDemandPickle(dpicklepath)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                    uiut.MakeDemandPickle(UPDemand, UPGDB)
            else:
                UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                uiut.MakeDemandPickle(UPDemand, UPGDB)
                
            TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            
            #get just the residential LU Types
            AllLUCodes = UPConfig['LUPriority']
            ResLUCodes = []
            for LUCode in AllLUCodes:
                if UPConfig['LUTypes'][LUCode] == 'res':
                    ResLUCodes.append(LUCode)
            
            ResSpaceValues = []
            for LUCode in ResLUCodes:
                AcPerUnit = UPDemand[TSCode]['ResLandUses'][LUCode]['AcPerUnit']
                PctVacantUnits = (UPDemand[TSCode]['ResLandUses'][LUCode]['PctVacantUnits'])*100
                PctOther = (UPDemand[TSCode]['ResLandUses'][LUCode]['PctOther'])*100
                
                ResSpaceValues.append([LUCode,AcPerUnit,PctVacantUnits,PctOther])
            
            if parameters[2].values == None:
                parameters[2].values = ResSpaceValues
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        
        #get the current ResLandUses values, and update with the user inputs
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
         
        ResLandUseValues = UPDemand[TSCode]['ResLandUses']
        ResSpaceValues = parameters[2].values
        for ResSpaceValue in ResSpaceValues:
            LUCode = ResSpaceValue[0]
            ResLandUseValues[LUCode]['AcPerUnit'] = ResSpaceValue[1]
            ResLandUseValues[LUCode]['PctVacantUnits'] = ResSpaceValue[2]/100
            ResLandUseValues[LUCode]['PctOther'] = ResSpaceValue[3]/100
         
        CalcDem.PopulateResLUTable(UPGDB, TSCode, ResLandUseValues)       
        CalcDem.PopulateResCalcsTable(UPGDB, TSCode)
         
        #save to the demand pickle
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        uiut.MakeDemandPickle(UPDemand, UPGDB)
        
        return
    
class SetSpaceReq4Emp(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3. Set Space Requirements - Employment"
        self.description = "Set the space requirements for Employment Land Use Types"
        self.canRunInBackground = False
        self.category = "D. Land Use Demand"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSCode = arcpy.Parameter(
            displayName="Timestep",
            name="TSCode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pEmpSpaceReq = arcpy.Parameter(
            displayName="Set Space Requirements for each LandUse",
            name="ResSpaceReq",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pEmpSpaceReq.columns = [['String', 'LandUse Code'], ['Double', 'Square Feet Per Employee'], ['Double', 'FAR'], ['Double', '% Other Space']]
        
        params = [pUPGDB,pTSCode,pEmpSpaceReq]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
        
        if parameters[1].altered:
            #the user selected a timestep and land use...see if that timestep/LU already has values
            #if so, populate the other parameters with the values in the upd_emplanduses table
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            
            #load demand pickle if exists, or create a new one
            dpicklepath = "\\".join([UPGDB,"UPDemand.p"])
            if uiut.CheckForPickle(dpicklepath):
                UPDemand = uiut.LoadDemandPickle(dpicklepath)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                    uiut.MakeDemandPickle(UPDemand, UPGDB)
            else:
                UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                uiut.MakeDemandPickle(UPDemand, UPGDB)
                
            TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            
            #get just the employment LU Types
            AllLUCodes = UPConfig['LUPriority']
            EmpLUCodes = []
            for LUCode in AllLUCodes:
                if UPConfig['LUTypes'][LUCode] == 'emp':
                    EmpLUCodes.append(LUCode)
            
            EmpSpaceValues = []
            for LUCode in EmpLUCodes:
                SFPerEmp = UPDemand[TSCode]['EmpLandUses'][LUCode]['SFPerEmp']
                FAR = UPDemand[TSCode]['EmpLandUses'][LUCode]['FAR']
                PctOther = (UPDemand[TSCode]['EmpLandUses'][LUCode]['PctOther'])*100
                
                EmpSpaceValues.append([LUCode,SFPerEmp,FAR,PctOther])
                
            if parameters[2].values == None:
                parameters[2].values = EmpSpaceValues
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        
        #get the current EmpLandUses values, and update with the user inputs
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        
        EmpLandUseValues = UPDemand[TSCode]['EmpLandUses']
        EmpSpaceValues = parameters[2].values
        for EmpSpaceValue in EmpSpaceValues:
            LUCode = EmpSpaceValue[0]
            EmpLandUseValues[LUCode]['SFPerEmp'] = EmpSpaceValue[1]
            EmpLandUseValues[LUCode]['FAR'] = EmpSpaceValue[2]
            EmpLandUseValues[LUCode]['PctOther'] = EmpSpaceValue[3]/100
        
        CalcDem.PopulateEmpLUTable(UPGDB, TSCode, EmpLandUseValues)
        CalcDem.PopulateEmpCalcTable(UPGDB, TSCode)
        
        #save to the demand pickle
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        uiut.MakeDemandPickle(UPDemand, UPGDB)
        
        return
    
class SetSubAreaPercentages(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "4. Set SubArea Percentages"
        self.description = "Set the percentage of employees and households going into each SubArea"
        self.canRunInBackground = False
        self.category = "D. Land Use Demand"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSCode = arcpy.Parameter(
            displayName="Timestep",
            name="TSCode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pSADist = arcpy.Parameter(
            displayName="Set SubArea Distributions",
            name="SADist",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pSADist.columns = [['String', 'SubArea'], ['Double', 'Percent of Total Population'], ['Double', 'Percent of Total Employees']]
        
        params = [pUPGDB,pTSCode,pSADist]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
        
        if parameters[1].altered:
            #populate the input table with the sub areas and their percentages (if already set)
            UPGDB = parameters[0].valueAsText
            
            #load demand pickle if exists, or create a new one
            dpicklepath = "\\".join([UPGDB,"UPDemand.p"])
            if uiut.CheckForPickle(dpicklepath):
                UPDemand = uiut.LoadDemandPickle(dpicklepath)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                    uiut.MakeDemandPickle(UPDemand, UPGDB)
            else:
                UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                uiut.MakeDemandPickle(UPDemand, UPGDB)
            
            TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
            
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            AllSAs = [sa['sa'] for sa in UPConfig['Subareas']]
            
            SADemandValues = []
            for SACode in AllSAs:
                PercentPop = UPDemand[TSCode]['TotalsBySA'][SACode]['PercentPop']*100
                PercentEmp = UPDemand[TSCode]['TotalsBySA'][SACode]['PercentEmp']*100
                
                SADemandValues.append([SACode,PercentPop,PercentEmp])
                
            if parameters[2].values == None:
                parameters[2].values=SADemandValues
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        
        #get a list of SubAreas
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        AllSAs = [sa['sa'] for sa in UPConfig['Subareas']]
        
        #get the current TotalsBySA values, and update with the user inputs
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        
        TotalsBySA = UPDemand[TSCode]['TotalsBySA']
        SAValues = parameters[2].values
        for SAValue in SAValues:
            SACode = SAValue[0]
            PercentPop = SAValue[1]/100
            PercentEmp = SAValue[2]/100
            
            InputValues = {}
            InputValues['PercentPop'] = PercentPop
            InputValues['PercentEmp'] = PercentEmp
            TotalsBySA[SACode] = InputValues
        
        CalcDem.PopulateSADemandTable(UPGDB, TSCode, AllSAs, TotalsBySA)
        
        #save to the demand pickle
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        uiut.MakeDemandPickle(UPDemand, UPGDB)
        
        return

class SetHousingDensity(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "5. Set Housing Density Distribution"
        self.description = "Set the Percentage of Households going into the Residentail Land Use Types"
        self.canRunInBackground = False
        self.category = "D. Land Use Demand"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSCode = arcpy.Parameter(
            displayName="Timestep",
            name="TSCode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pLUDist = arcpy.Parameter(
            displayName="Set Percentages for each LandUse",
            name="LUDist",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pLUDist.columns = [['String', 'SubArea Code'], ['String', 'LandUse Code'], ['Double', 'Percent of Households']]
               
        params = [pUPGDB,pTSCode,pLUDist]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
        
        if parameters[1].altered:
            UPGDB = parameters[0].valueAsText
            arcpy.env.workspace = UPGDB
              
             #load demand pickle if exists, or create a new one
            dpicklepath = "\\".join([UPGDB,"UPDemand.p"])
            if uiut.CheckForPickle(dpicklepath):
                UPDemand = uiut.LoadDemandPickle(dpicklepath)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                    uiut.MakeDemandPickle(UPDemand, UPGDB)
            else:
                UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                uiut.MakeDemandPickle(UPDemand, UPGDB)
              
            TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
              
            #get lists of SubAreas and res LUs
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            AllSAs = [sa['sa'] for sa in UPConfig['Subareas']]
  
            ResLUCodes=[]
            ResTypeRows = arcpy.SearchCursor('upc_lu', where_clause = r"LUType = 'res'")
            for ResTypeRow in ResTypeRows:
                LUCode = ResTypeRow.getValue('Code')
                ResLUCodes.append(LUCode)
  
            ResLUValues = []
            for SACode in AllSAs:
                PctResBySA = UPDemand[TSCode]['PctResBySA'][SACode]
                for ResLU in ResLUCodes:
                    ResLUValues.append([SACode,ResLU,PctResBySA[ResLU]*100])
              
            if parameters[2].values == None:
                parameters[2].values = ResLUValues
            
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")    
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
         
        #get a list of SubAreas
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        AllSAs = [sa['sa'] for sa in UPConfig['Subareas']]
     
        #get the current PctResBySA values, and update with user inputs
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
         
        PctResBySA = UPDemand[TSCode]['PctResBySA']
        ResLUValues = parameters[2].values
        for ResLUValue in ResLUValues:
            SACode = ResLUValue[0]
            LUCode = ResLUValue[1]
            PctValue = ResLUValue[2]/100
             
            PctResBySA[SACode][LUCode] = PctValue
             
        CalcDem.PopulateSAResTable(UPGDB, TSCode, AllSAs, PctResBySA)
         
        #save to the demand pickle
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        uiut.MakeDemandPickle(UPDemand, UPGDB)
        
        return
    
class SetEmploymentDist(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "6. Set Employment Type Distribution"
        self.description = "Set the Percentage of Employees going into the Employment Land Use Types"
        self.canRunInBackground = False
        self.category = "D. Land Use Demand"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        pTSCode = arcpy.Parameter(
            displayName="Timestep",
            name="TSCode",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pLUDist = arcpy.Parameter(
            displayName="Set Percentages for each LandUse",
            name="LUDist",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")
        pLUDist.columns = [['String', 'SubArea Code'], ['String', 'LandUse Code'], ['Double', 'Percent of Employees']]

        params = [pUPGDB,pTSCode,pLUDist]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[0].value:
            UPGDB = parameters[0].valueAsText
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            parameters[1].filter.list = uiut.TimestepNameLookup(UPConfig)
        
        if parameters[1].altered:
            UPGDB = parameters[0].valueAsText
            arcpy.env.workspace = UPGDB
             
            #load demand pickle if exists, or create a new one
            dpicklepath = "\\".join([UPGDB,"UPDemand.p"])
            if uiut.CheckForPickle(dpicklepath):
                UPDemand = uiut.LoadDemandPickle(dpicklepath)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                    uiut.MakeDemandPickle(UPDemand, UPGDB)
            else:
                UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
                if len(UPDemand) == 0:
                    #create an empty demand pickle
                    UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
                uiut.MakeDemandPickle(UPDemand, UPGDB)
             
            TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
             
            #get lists of SubAreas and emp LUs
            picklepath = "\\".join([UPGDB,"UPConfig.p"])
            UPConfig = uiut.LoadPickle(picklepath)
            AllSAs = [sa['sa'] for sa in UPConfig['Subareas']]
 
            EmpLUCodes=[]
            EmpTypeRows = arcpy.SearchCursor('upc_lu', where_clause = r"LUType = 'emp'")
            for EmpTypeRow in EmpTypeRows:
                LUCode = EmpTypeRow.getValue('Code')
                EmpLUCodes.append(LUCode)
 
            EmpLUValues = []
            for SACode in AllSAs:
                PctEmpBySA = UPDemand[TSCode]['PctEmpBySA'][SACode]
                for EmpLU in EmpLUCodes:
                    EmpLUValues.append([SACode,EmpLU,PctEmpBySA[EmpLU]*100])
             
            if parameters[2].values == None:
                parameters[2].values = EmpLUValues
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")    
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        TSCode = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        
        #get a list of SubAreas
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        AllSAs = [sa['sa'] for sa in UPConfig['Subareas']]
    
        #get the current PctEmpBySA values, and update with user inputs
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        
        PctEmpBySA = UPDemand[TSCode]['PctEmpBySA']
        EmpLUValues = parameters[2].values
        for EmpLUValue in EmpLUValues:
            SACode = EmpLUValue[0]
            LUCode = EmpLUValue[1]
            PctValue = EmpLUValue[2]/100
            
            PctEmpBySA[SACode][LUCode] = PctValue
            
        CalcDem.PopulateSAEmpTable(UPGDB, TSCode, AllSAs, PctEmpBySA)
        
        #save to the demand pickle
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        uiut.MakeDemandPickle(UPDemand, UPGDB)        
        
        return
    
class RunDemographics(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "7. Run Land Use Demand"
        self.description = "Runs Uplan demand - determines space required for each land use type in each SubArea "
        self.canRunInBackground = False
        self.category = "D. Land Use Demand"

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        params = [pUPGDB]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")    
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        
        #get lists of Timesteps and SubAreas
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        AllTSCodes = [ts[0] for ts in UPConfig['TimeSteps']]
        AllSAs = [sa['sa'] for sa in UPConfig['Subareas']]
        
        #Get UPDemand
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)

        #1. update upd_subareares and upd_usbareaemp tables in case the user has changed space requirements
        #   for land uses (tools 2 and/or 3), but not distribution to SubAreas (tools 5 and/or 6)
        #2. update upc_demand table
        for TSCode in AllTSCodes:
            PctResBySA = UPDemand[TSCode]['PctResBySA']
            CalcDem.PopulateSAResTable(UPGDB, TSCode, AllSAs, PctResBySA)
            
            PctEmpBySA = UPDemand[TSCode]['PctEmpBySA']
            CalcDem.PopulateSAEmpTable(UPGDB, TSCode, AllSAs, PctEmpBySA)
            
            CalcDem.UpdateUPCDemandTable(UPGDB, TSCode)
            
        #save to the demand pickle
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        uiut.MakeDemandPickle(UPDemand, UPGDB)
        
        #save to the UPConfig pickle
        splitpath = uiut.SplitPath(UPGDB)
        messages.addMessage("Reading Configuration from Database")
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        messages.addMessage("Writing Pickle")
        uiut.MakePickle(UPConfig, UPGDB)
        messages.addMessage("Pickle Written")
        
        return
    
# # For Debugging
# def main():
#      tbx = Toolbox()
#      tool = PreCalcWeights()
#      tool.execute(tool.getParameterInfo(), None)
#                    
# if __name__ == '__main__':
#      main()
      
    

    