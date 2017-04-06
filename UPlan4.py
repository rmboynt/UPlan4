'''
Created on Feb 5, 2015

@author: roth
'''
import os
import arcpy
import UPConfig
import CalcGeneralPlans
import CalcConstraints
import CalcWeights
from Utilities import Logger

if __name__ == "__main__":
    Logger("Running UPlan")
    global UPConfig
    UPConfig = UPConfig.LoadUPConfig_python()
    CalcGeneralPlans.CalcGP(UPConfig)
    CalcConstraints.CalcConstraints(UPConfig)
    CalcWeights.CalcWeights(UPConfig)
    
    Logger("UPlan Finished")

