'''
Created on Feb 5, 2015

@author: roth
'''
import os
import UPConfig
from Utilities import UPCleanup


    
if __name__ == "__main__":
    print("Starting Cleanup")
    UPConfig = UPConfig.LoadUPConfig_python(True,True)
    UPCleanup(UPConfig)
    print("Cleanup Finished")
    