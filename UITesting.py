'''
Created on Jun 9, 2015

@author: roth
'''

import arcpy
import os
import cPickle
import UIUtilities as uiut
import UPConfig as upc


dbpath = r"..\testing" 
dbname = 'calaveras.gdb'

# combined path
picklepath = os.path.join(dbpath,dbname)

# get UPConfig
print("getting path")
UPConfig  = uiut.LoadPickle(picklepath)

startlist = ['A','B','C','D','E']

outlist = uiut.InsertToList(startlist, "N", 2)

TSShortName = "TS3"
TSLongName = "Time Step 3"
TSPosition = 2

TimeSteps = UPConfig['TimeSteps']
print(TimeSteps)
UPConfig['TimeSteps'] = uiut.InsertToList(TimeSteps, [TSShortName,TSLongName], TSPosition)
print(UPConfig['TimeSteps'])

# Empty Timestep
UPConfig[TSShortName] = uiut.MakeEmptyTimeStep()


# Write out the pickle
uiut.MakePickle(UPConfig, picklepath)

# Write out to tables
upc.WriteUPConfigToGDB(UPConfig) # excluding upc_layers

print("Done")
