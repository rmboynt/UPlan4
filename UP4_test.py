'''
used to test uplan functions
'''

import arcpy
import UIUtilities as uiut
import CalcDemographics as CalcDem

TSCode = 'ts1'
UPGDB = r"G:\Public\UPLAN\Uplan4\testing\ryan_test2.gdb"

arcpy.env.workspace = UPGDB

picklepath = "\\".join([UPGDB,"UPConfig.p"])
UPConfig = uiut.LoadPickle(picklepath)
AllSAs = [sa['sa'] for sa in UPConfig['Subareas']]

EmpLUCodes=[]
EmpTypeRows = arcpy.SearchCursor('upc_lu', where_clause = r"LUType = 'emp'")
for EmpTypeRow in EmpTypeRows:
    LUCode = EmpTypeRow.getValue('Code')
    EmpLUCodes.append(LUCode)

UPDemand = CalcDem.ReadUPDemandFromGDB(UPGDB)

EmpLUValues = []
for SACode in AllSAs:
    PctEmpBySA = UPDemand[TSCode]['PctEmpBySA'][SACode]
    for EmpLU in EmpLUCodes:
        EmpLUValues.append([SACode,EmpLU,PctEmpBySA[EmpLU]*100])
             
print(EmpLUValues)