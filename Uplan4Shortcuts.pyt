import arcpy
import os
import cPickle as pickle
import UPConfig as upc
import UIUtilities as uiut
import CalcDemographics as CalcDem

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "UPlan4 Shortcuts"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [MakePickle,CopyAttractors,CopyConstraints,CopyTimestep]
        
class MakePickle(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update UPlan GDB after Manual Edit"
        self.description = ""
        self.canRunInBackground = False
 
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
        splitpath = uiut.SplitPath(UPGDB)
        messages.addMessage("Reading Configuration from Database")
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        messages.addMessage("Writing Pickle")
        uiut.MakePickle(UPConfig, UPGDB)
        messages.addMessage("Pickle Written")
        
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        if len(UPDemand) == 0:
            #create an empty demand pickle
            UPDemand = uiut.MakeEmptyUPDemand(UPGDB)
        uiut.MakeDemandPickle(UPDemand, UPGDB)
 
        return

class CopyAttractors(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Copy the Attraction Weights to Another Land Use"
        self.description = ""
        self.canRunInBackground = False

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
        pLandUse = arcpy.Parameter(
            displayName="Select Land Use to Copy Attractor Weights From",
            name="LandUse",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pLandUse2 = arcpy.Parameter(
            displayName="Select Land Use to Copy Attractor Weights To",
            name="LandUse2",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        params = [pUPGDB,pTimeStep,pLandUse,pLandUse2]
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
            parameters[3].filter.list = uiut.LUNameLookup(UPConfig)
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
        splitpath = uiut.SplitPath(UPGDB)
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        lu = uiut.LUCodeLookup(parameters[2].valueAsText, UPConfig)
        lu2 = uiut.LUCodeLookup(parameters[3].valueAsText, UPConfig)
        
        WeightsToCopy = UPConfig[ts]['aweights'][lu]
        UPConfig[ts]['aweights'][lu2] = WeightsToCopy
        
        upc.WriteUPConfigToGDB(UPConfig)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        uiut.MakePickle(UPConfig,UPGDB)
        
        return
    
class CopyConstraints(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Copy the Constraint Weights to Another Land Use"
        self.description = ""
        self.canRunInBackground = False

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
        pLandUse = arcpy.Parameter(
            displayName="Select Land Use to Copy Constraint Weights From",
            name="LandUse",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pLandUse2 = arcpy.Parameter(
            displayName="Select Land Use to Copy Constraint Weights To",
            name="LandUse2",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        params = [pUPGDB,pTimeStep,pLandUse,pLandUse2]
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
            parameters[3].filter.list = uiut.LUNameLookup(UPConfig)
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
        splitpath = uiut.SplitPath(UPGDB)
        picklepath = "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        lu = uiut.LUCodeLookup(parameters[2].valueAsText, UPConfig)
        lu2 = uiut.LUCodeLookup(parameters[3].valueAsText, UPConfig)

        WeightsToCopy = UPConfig[ts]['cweights'][lu]
        UPConfig[ts]['cweights'][lu2] = WeightsToCopy
        
        upc.WriteUPConfigToGDB(UPConfig)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        uiut.MakePickle(UPConfig,UPGDB)
        
        return

class CopyTimestep(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Copy a Time Step"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        pUPGDB = arcpy.Parameter(
            displayName="UPlan geodatabase",
            name="UPGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        pTimeStep = arcpy.Parameter(
            displayName="Select Time Step To Copy",
            name="TimeStep",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        pTSLongName = arcpy.Parameter(
            displayName="New TimeStep's Descriptive Name",
            name="TSLongName",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pTSShortName = arcpy.Parameter(
            displayName="New TimeStep's Code",
            name="TSShortName",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        pTSPosition = arcpy.Parameter(
            displayName="New TimeStep's Position",
            name="TSPosition",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        params = [pUPGDB,pTimeStep,pTSLongName,pTSShortName,pTSPosition]
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
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        if parameters[0].value:
            if uiut.CheckIfFGDB(parameters[0].value)==False:
                parameters[0].setErrorMessage("You must select a file geodatabase")
        
            if parameters[3].value:
                if uiut.CheckIfTSInFGDB(str(parameters[0].value), str(parameters[3].value)):
                    parameters[3].setErrorMessage("The TimeStep Code must be unique. See the upc_timesteps table.")
                    
            if parameters[4].value:
                if int(parameters[4].value) < 1:
                    parameters[4].setErrorMessage("Position must be at least 1")
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        UPGDB = parameters[0].valueAsText
        splitpath = uiut.SplitPath(UPGDB)
        picklepath =  "\\".join([UPGDB,"UPConfig.p"])
        UPConfig = uiut.LoadPickle(picklepath)
        
        ts = uiut.TimestepCodeLookup(parameters[1].valueAsText, UPConfig)
        TSLongName = parameters[2].valueAsText
        TSShortName = parameters[3].valueAsText
        TSPosition = int(parameters[4].valueAsText)
        
        # add to TimeStep list in the correct order
        TimeSteps = UPConfig['TimeSteps']
        UPConfig['TimeSteps'] = uiut.InsertToList(TimeSteps, [TSShortName,TSLongName], TSPosition)

        #copy timestep dictionary
        TimestepToCopy = UPConfig[ts]
        UPConfig[TSShortName] = TimestepToCopy
        
        #save to UPGDB tables and update UPConfig pickle
        upc.WriteUPConfigToGDB(UPConfig)
        UPConfig = upc.ReadUPConfigFromGDB(splitpath[0],splitpath[1])
        uiut.MakePickle(UPConfig,UPGDB)
        
        #copy demand dictionary
        dpicklepath = "\\".join([UPGDB,"UPDemand.p"])
        UPDemand = uiut.LoadDemandPickle(dpicklepath)
        
        TSDemandToCopy = UPDemand[ts]
        UPDemand[TSShortName] = TSDemandToCopy
        
        #use demand dictionary to populate demand tables and update demand pickle
        CalcDem.WriteUPDemandToGDB(UPGDB, UPDemand, UPConfig)
        UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)
        uiut.MakeDemandPickle(UPDemand, UPGDB)
        
        return

class ManualEditTable(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update UPGDB"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = None
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
        return