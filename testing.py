'''
Created on Mar 5, 2015

@author: roth
'''
import AllocUtilities as au
import Utilities
import os
import arcpy
# import pandas as pd
import numpy as np
import UPConfig
import pandas as pd
# from Utilities import MergeDataFrames
# 
# arcpy.env.workspace=r"M:\UPlan4\repository\testing\calaveras.gdb"
# arcpy.env.overwriteOutput = Trues
# 
# demand = 100
#    
# # Get gp table
# gpTableName = "up_bg_gp_avail_ts1"
# gparray = arcpy.da.TableToNumPyArray("up_bg_gp_avail_ts1", ['pclid','gp_ind'])
# gpdf = pd.DataFrame(gparray)
# 
# # Get dev space table
# dsTableName = "up_cons_ts1"
# dsarray = arcpy.da.TableToNumPyArray("up_cons_ts1", ['pclid','SUM_dev_ac_ind'])
# dsdf = pd.DataFrame(dsarray)
# 
# # get weight table
# wtTableName = "up_weights"
# wtFieldName = 'wt_ts1_ind'
# wtarray = arcpy.da.TableToNumPyArray("up_weights",['pclid','wt_ts1_ind']) 
# wtdf = pd.DataFrame(wtarray)
# 
# # get prior alloc table
# 
# 
# allocdf = MergeDataFrames([gpdf,dsdf,wtdf],'pclid')
# 
# # Do allocation
# allocdf['cumarea'] = allocdf[(allocdf['gp_ind'] == 1) & (allocdf['SUM_dev_ac_ind'] > 0)].sort(columns = 'wt_ts1_ind',ascending=False)['SUM_dev_ac_ind'].cumsum()
# allocdf['alloc_pct'] = 0.
# allocdf['alloc_pct'][(allocdf['cumarea'] < demand)] = 1.
# 
# # Exporting to numpy array and table
# exdf = allocdf.loc[:,['pclid','alloc_pct']]
# arr = np.array(exdf.to_records(False))
# arr.dtype = [('pclid','int'),('alloc_pct','float')]
# arcpy.da.NumPyArrayToTable(arr,os.path.join(r"M:\UPlan4\repository\testing\calaveras.gdb","up_test"))
# pass

# UPDemand = {u'ts2': {'ResCalcs': {u'rl': {'GrossAcrePerOccUnit': 5.0, 'GrossAcrePerUnit': 4.0}, u'rm': {'GrossAcrePerOccUnit': 0.36764705882352944, 'GrossAcrePerUnit': 0.3125}, u'rh': {'GrossAcrePerOccUnit': 0.06944444444444445, 'GrossAcrePerUnit': 0.0625}, u'rvl': {'GrossAcrePerOccUnit': 25.0, 'GrossAcrePerUnit': 20.0}}, 'TotalsBySA': {u'sa2': {'NumEmp': 4024.39024390244, 'PercentEmp': 0.5, 'NumHH': 1463.4146341463418, 'PercentPop': 0.2}, u'sa1': {'NumEmp': 4024.39024390244, 'PercentEmp': 0.5, 'NumHH': 5853.658536585367, 'PercentPop': 0.8}}, 'PctResBySA': {u'sa2': {u'rl': 0.04, u'rm': 0.5, u'rh': 0.45, u'rvl': 0.01}, u'sa1': {u'rl': 0.1, u'rm': 0.8, u'rh': 0.05, u'rvl': 0.05}}, 'EmpCalcs': {u'ind': {'GrossAcrePerEmp': 0.14921946740128558}, u'ser': {'GrossAcrePerEmp': 0.01721763085399449}, u'ret': {'GrossAcrePerEmp': 0.014348025711662075}}, 'EmpAcresBySA': {u'sa2': {u'ind': 60.05173688100519, u'ser': 27.716186252771628, u'ret': 28.87102734663711}, u'sa1': {u'ind': 120.10347376201038, u'ser': 27.716186252771628, u'ret': 23.09682187730969}}, 'PctEmpBySA': {u'sa2': {u'ind': 0.1, u'ser': 0.4, u'ret': 0.5}, u'sa1': {u'ind': 0.2, u'ser': 0.4, u'ret': 0.4}}, 'EPHH': 1.1, 'ResLandUses': {u'rl': {'PctOther': 0.5, 'PctVacantUnits': 0.2, 'AcPerUnit': 2.0}, u'rm': {'PctOther': 0.2, 'PctVacantUnits': 0.15, 'AcPerUnit': 0.25}, u'rh': {'PctOther': 0.2, 'PctVacantUnits': 0.1, 'AcPerUnit': 0.05}, u'rvl': {'PctOther': 0.5, 'PctVacantUnits': 0.2, 'AcPerUnit': 10.0}}, 'EmpLandUses': {u'ind': {'FAR': 0.2, 'PctOther': 0.5, 'SFPerEmp': 650.0}, u'ser': {'FAR': 0.5, 'PctOther': 0.2, 'SFPerEmp': 300.0}, u'ret': {'FAR': 0.5, 'PctOther': 0.2, 'SFPerEmp': 250.0}}, 'ResAcresBySA': {u'sa2': {u'rl': 292.68292682926835, u'rm': 269.01004304160693, u'rh': 45.73170731707319, u'rvl': 365.85365853658544}, u'sa1': {u'rl': 2926.8292682926835, u'rm': 1721.6642754662846, u'rh': 20.325203252032527, u'rvl': 7317.073170731709}}, 'PPHH': 2.05, 'EndPop': 50000, 'OccUnitsBySA': {u'sa2': {u'rl': 58.536585365853675, u'rm': 731.7073170731709, u'rh': 658.5365853658539, u'rvl': 14.634146341463419}, u'sa1': {u'rl': 585.3658536585367, u'rm': 4682.926829268294, u'rh': 292.68292682926835, u'rvl': 292.68292682926835}}, 'PopChange': 15000, 'StartPop': 35000, 'NumEmpBySA': {u'sa2': {u'ind': 402.439024390244, u'ser': 1609.756097560976, u'ret': 2012.19512195122}, u'sa1': {u'ind': 804.878048780488, u'ser': 1609.756097560976, u'ret': 1609.756097560976}}}, u'ts1': {'ResCalcs': {u'rl': {'GrossAcrePerOccUnit': 5.0, 'GrossAcrePerUnit': 4.0}, u'rm': {'GrossAcrePerOccUnit': 0.36764705882352944, 'GrossAcrePerUnit': 0.3125}, u'rh': {'GrossAcrePerOccUnit': 0.06944444444444445, 'GrossAcrePerUnit': 0.0625}, u'rvl': {'GrossAcrePerOccUnit': 25.0, 'GrossAcrePerUnit': 20.0}}, 'TotalsBySA': {u'sa2': {'NumEmp': 6707.317073170732, 'PercentEmp': 0.5, 'NumHH': 2439.024390243903, 'PercentPop': 0.2}, u'sa1': {'NumEmp': 6707.317073170732, 'PercentEmp': 0.5, 'NumHH': 9756.097560975611, 'PercentPop': 0.8}}, 'PctResBySA': {u'sa2': {u'rl': 0.04, u'rm': 0.5, u'rh': 0.45, u'rvl': 0.01}, u'sa1': {u'rl': 0.1, u'rm': 0.8, u'rh': 0.05, u'rvl': 0.05}}, 'EmpCalcs': {u'ind': {'GrossAcrePerEmp': 0.14921946740128558}, u'ser': {'GrossAcrePerEmp': 0.01721763085399449}, u'ret': {'GrossAcrePerEmp': 0.014348025711662075}}, 'EmpAcresBySA': {u'sa2': {u'ind': 100.08622813500864, u'ser': 46.19364375461937, u'ret': 48.11837891106184}, u'sa1': {u'ind': 200.17245627001728, u'ser': 46.19364375461937, u'ret': 38.49470312884948}}, 'PctEmpBySA': {u'sa2': {u'ind': 0.1, u'ser': 0.4, u'ret': 0.5}, u'sa1': {u'ind': 0.2, u'ser': 0.4, u'ret': 0.4}}, 'EPHH': 1.1, 'ResLandUses': {u'rl': {'PctOther': 0.5, 'PctVacantUnits': 0.2, 'AcPerUnit': 2.0}, u'rm': {'PctOther': 0.2, 'PctVacantUnits': 0.15, 'AcPerUnit': 0.25}, u'rh': {'PctOther': 0.2, 'PctVacantUnits': 0.1, 'AcPerUnit': 0.05}, u'rvl': {'PctOther': 0.5, 'PctVacantUnits': 0.2, 'AcPerUnit': 10.0}}, 'EmpLandUses': {u'ind': {'FAR': 0.2, 'PctOther': 0.5, 'SFPerEmp': 650.0}, u'ser': {'FAR': 0.5, 'PctOther': 0.2, 'SFPerEmp': 300.0}, u'ret': {'FAR': 0.5, 'PctOther': 0.2, 'SFPerEmp': 250.0}}, 'ResAcresBySA': {u'sa2': {u'rl': 487.80487804878055, u'rm': 448.3500717360116, u'rh': 76.21951219512196, u'rvl': 609.7560975609757}, u'sa1': {u'rl': 4878.048780487806, u'rm': 2869.4404591104744, u'rh': 33.875338753387545, u'rvl': 12195.121951219515}}, 'PPHH': 2.05, 'EndPop': 35000, 'OccUnitsBySA': {u'sa2': {u'rl': 97.56097560975611, u'rm': 1219.5121951219514, u'rh': 1097.5609756097563, u'rvl': 24.39024390243903}, u'sa1': {u'rl': 975.6097560975612, u'rm': 7804.87804878049, u'rh': 487.8048780487806, u'rvl': 487.8048780487806}}, 'PopChange': 25000, 'StartPop': 10000, 'NumEmpBySA': {u'sa2': {u'ind': 670.7317073170733, u'ser': 2682.926829268293, u'ret': 3353.658536585366}, u'sa1': {u'ind': 1341.4634146341466, u'ser': 2682.926829268293, u'ret': 2682.926829268293}}}}
# print(UPDemand['ts1']['EmpCalcs']['ind']['GrossAcrePerEmp'])

# FieldWithAcres = 'acres_rh'
# AcrePerOccUnit = 0.0694
# print('!' + FieldWithAcres + '!/'+str(AcrePerOccUnit))

#UPConfig = {'paths': {'dbpath': 'G:\\Public\\UPLAN\\Uplan4\\testing', 'dbname': 'calaveras_complete.gdb'}, u'BaseGeom_id': 'pclid', u'Redev': 'redev_src', u'Redev_pop': 'pop', u'BaseGeom_cent': 'pcl_cent', 'LUNames': {'ser': 'Service', 'ret': 'Retail', 'rvl': 'Residential Very Low', 'rl': 'Residential Low', 'ind': 'Industrial', 'rm': 'Residential Medium', 'rh': 'Residential High'}, u'Subarea_id': 'sa', u'BaseGeom_bnd': 'pcl_bnd', 'AllocMethods': {'ser': 1, 'ret': 1, 'rvl': 2, 'rl': 1, 'ind': 1, 'rm': 1, 'rh': 1}, 'ts2': {'attractors': ['rds_shwy', 'rds_main', 'cp_tc', 'angels_bnd'], 'aweights': {'ser': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 25.0], [200.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [500.0, 5.0], [5000.0, 0.0]]}, 'ret': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 25.0], [100.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [500.0, 5.0], [5000.0, 0.0]]}, 'rvl': {'angels_bnd': [[0.0, 0.0]], 'rds_shwy': [[0.0, 5.0], [50000.0, 0.0]], 'cp_tc': [[0.0, 0.0]], 'rds_main': [[0.0, 10.0], [25000.0, 0.0]]}, 'rl': {'angels_bnd': [[0.0, 0.0]], 'rds_shwy': [[0.0, 10.0], [25000.0, 0.0]], 'cp_tc': [[0.0, 0.0]], 'rds_main': [[0.0, 10.0], [25000.0, 0.0]]}, 'ind': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 20.0], [500.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [500.0, 5.0], [5000.0, 0.0]]}, 'rm': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 20.0], [1000.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [1000.0, 10.0], [10000.0, 0.0]]}, 'rh': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 20.0], [200.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [500.0, 5.0], [5000.0, 0.0]]}}, 'cweights': {'ser': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 1.0}, 'ret': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 1.0}, 'rvl': {'undevelopable': 1.0, 'vpools': 0.1, 'low_gw': 0.25}, 'rl': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 0.25}, 'ind': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 1.0}, 'rm': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 0.25}, 'rh': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 0.0}}, 'gp': ['gp', 'gp_class'], 'mixeduse': {'CC': [['ret', 'rh'], ['ret', 'ser'], ['ser', 'rh'], ['ret', 'ser', 'rh']], 'CCR': [['ret', 'rh'], ['ret', 'ser'], ['ser', 'rh'], ['ret', 'ser', 'rh']], 'PD': [['ret', 'rh'], ['ret', 'ser'], ['ser', 'rh'], ['ret', 'ser', 'rh']], 'CC/H': [['ret', 'rh'], ['ret', 'ser'], ['ser', 'rh'], ['ret', 'ser', 'rh']]}, 'Demand': {'sa2': {'ser': 27.716186252771628, 'ret': 28.87102734663711, 'rvl': 365.85365853658544, 'rl': 292.68292682926835, 'ind': 60.05173688100519, 'rm': 269.01004304160693, 'rh': 45.73170731707319}, 'sa1': {'ser': 27.716186252771628, 'ret': 23.09682187730969, 'rvl': 7317.073170731709, 'rl': 2926.8292682926835, 'ind': 120.10347376201038, 'rm': 1721.6642754662846, 'rh': 20.325203252032527}}, 'gplu': {'ser': ['Commercial', 'Commercial - Recreation', 'PS/SC', 'SC', 'CC', 'CC/H', 'PD', 'R1/SC', 'C-PD', 'CCH', 'CCL', 'CCR', 'CO', 'CR', 'PI'], 'ret': ['Commercial', 'Commercial - Recreation', 'PS/SC', 'SC', 'CC', 'CC/H', 'PD', 'R1/SC', 'C-PD', 'CCH', 'CCL', 'CCR', 'CO', 'CR'], 'rvl': ['Mineral Resource', 'Agricultural Lands', 'Biological Resource', 'RA/R1', 'RA', 'WL', 'RP', 'RM', 'RTA', 'RTB'], 'rl': ['Residential - Low - 1 acre', 'Residential - Rural - 2 acres', 'Residential - Rural - 5 acres', 'Residential - Agricultural', 'PD', 'RA/R1', 'CCH', 'CCR', 'RH', 'RR'], 'ind': ['I', 'PD-I'], 'rm': ['Residential - Low - 14,500 sq ft', 'Residential - Low - 21,800', 'Residential - Low - 21,800 sq ft', 'Residential - Low - 1 acre', 'Residential - Rural - 2 acres', 'Residential - Rural - 5 acres', 'Residential - Agricultural', 'R3', 'R3-PD', 'R1', 'R1-PD', 'R2', 'RA/R1', 'R1/SC', 'C-PD', 'CCH', 'CCL', 'CCR', 'RHD', 'RMD', 'RLD', 'RH'], 'rh': ['Residential - Medium - 6,000 sq ft', 'Residential - Low - 14,500 sq ft', 'R3', 'R3-PD', 'CC', 'CC/H', 'PD', 'CCR', 'RHD']}, 'constraints': ['undevelopable', 'low_gw', 'vpools']}, 'LUPriority': ['ind', 'ret', 'ser', 'rh', 'rm', 'rl', 'rvl'], u'Subarea_search': '100', u'Redev_emp': 'emp', 'TimeSteps': [['ts1', 'TimeStep 1'], ['ts2', 'TimeStep 2']], u'DistMode': 'GenerateNear', 'LUTypes': {'ser': 'emp', 'ret': 'emp', 'rvl': 'res', 'rl': 'res', 'ind': 'emp', 'rm': 'res', 'rh': 'res'}, 'Subareas': [{'sa': 'sa1', 'SAName': 'Subarea 1'}, {'sa': 'sa2', 'SAName': 'Subarea 2'}], 'ts1': {'attractors': ['rds_shwy', 'rds_main', 'cp_tc', 'angels_bnd'], 'aweights': {'ser': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 25.0], [200.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [500.0, 5.0], [5000.0, 0.0]]}, 'ret': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 25.0], [100.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [500.0, 5.0], [5000.0, 0.0]]}, 'rvl': {'angels_bnd': [[0.0, 0.0]], 'rds_shwy': [[0.0, 5.0], [50000.0, 0.0]], 'cp_tc': [[0.0, 0.0]], 'rds_main': [[0.0, 10.0], [25000.0, 0.0]]}, 'rl': {'angels_bnd': [[0.0, 0.0]], 'rds_shwy': [[0.0, 10.0], [25000.0, 0.0]], 'cp_tc': [[0.0, 0.0]], 'rds_main': [[0.0, 10.0], [25000.0, 0.0]]}, 'ind': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 20.0], [500.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [500.0, 5.0], [5000.0, 0.0]]}, 'rm': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 20.0], [1000.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [1000.0, 10.0], [10000.0, 0.0]]}, 'rh': {'angels_bnd': [[0.0, 30.0], [1000.0, 0.0]], 'rds_shwy': [[0.0, 20.0], [200.0, 10.0], [10000.0, 0.0]], 'cp_tc': [[0.0, 25.0], [1000.0, 0.0]], 'rds_main': [[0.0, 15.0], [500.0, 5.0], [5000.0, 0.0]]}}, 'cweights': {'ser': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 1.0}, 'ret': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 1.0}, 'rvl': {'undevelopable': 1.0, 'vpools': 0.1, 'low_gw': 0.25}, 'rl': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 0.25}, 'ind': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 1.0}, 'rm': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 0.25}, 'rh': {'undevelopable': 1.0, 'vpools': 0.5, 'low_gw': 0.0}}, 'gp': ['gp', 'gp_class'], 'mixeduse': {'CC': [['ret', 'rh'], ['ret', 'ser'], ['ser', 'rh'], ['ret', 'ser', 'rh']], 'CCR': [['ret', 'rh'], ['ret', 'ser'], ['ser', 'rh'], ['ret', 'ser', 'rh']], 'PD': [['ret', 'rh'], ['ret', 'ser'], ['ser', 'rh'], ['ret', 'ser', 'rh']], 'CC/H': [['ret', 'rh'], ['ret', 'ser'], ['ser', 'rh'], ['ret', 'ser', 'rh']]}, 'Demand': {'sa2': {'ser': 46.19364375461937, 'ret': 48.11837891106184, 'rvl': 609.7560975609757, 'rl': 487.80487804878055, 'ind': 100.08622813500864, 'rm': 448.3500717360116, 'rh': 76.21951219512196}, 'sa1': {'ser': 46.19364375461937, 'ret': 38.49470312884948, 'rvl': 12195.121951219515, 'rl': 4878.048780487806, 'ind': 200.17245627001728, 'rm': 2869.4404591104744, 'rh': 33.875338753387545}}, 'gplu': {'ser': ['Commercial', 'Commercial - Recreation', 'PS/SC', 'SC', 'CC', 'CC/H', 'PD', 'R1/SC', 'C-PD', 'CCH', 'CCL', 'CCR', 'CO', 'CR', 'PI'], 'ret': ['Commercial', 'Commercial - Recreation', 'PS/SC', 'SC', 'CC', 'CC/H', 'PD', 'R1/SC', 'C-PD', 'CCH', 'CCL', 'CCR', 'CO', 'CR'], 'rvl': ['Mineral Resource', 'Agricultural Lands', 'Biological Resource', 'RA/R1', 'RA', 'WL', 'RP', 'RM', 'RTA', 'RTB'], 'rl': ['Residential - Low - 1 acre', 'Residential - Rural - 2 acres', 'Residential - Rural - 5 acres', 'Residential - Agricultural', 'PD', 'RA/R1', 'CCH', 'CCR', 'RH', 'RR'], 'ind': ['I', 'PD-I'], 'rm': ['Residential - Low - 14,500 sq ft', 'Residential - Low - 21,800', 'Residential - Low - 21,800 sq ft', 'Residential - Low - 1 acre', 'Residential - Rural - 2 acres', 'Residential - Rural - 5 acres', 'Residential - Agricultural', 'R3', 'R3-PD', 'R1', 'R1-PD', 'R2', 'RA/R1', 'R1/SC', 'C-PD', 'CCH', 'CCL', 'CCR', 'RHD', 'RMD', 'RLD', 'RH'], 'rh': ['Residential - Medium - 6,000 sq ft', 'Residential - Low - 14,500 sq ft', 'R3', 'R3-PD', 'CC', 'CC/H', 'PD', 'CCR', 'RHD']}, 'constraints': ['undevelopable', 'low_gw', 'vpools']}, u'Subarea_bnd': 'subareas'}
#initable = au.MakePolyList(UPConfig)
#initable.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\TestOut0.csv")



#UPConfig = UPConfig.ReadUPConfigFromGDB(r"G:\Public\UPLAN\Uplan4\testing","calaveras_complete.gdb")
#UPConfig = UPConfig.ReadUPConfigFromGDB(r"G:\Public\UPLAN\HumboldtUPlan","humboldt_run1.gdb")
UPConfig = UPConfig.ReadUPConfigFromGDB(r"G:\Public\UPLAN\HumboldtUPlan\backup","humboldt_run2.gdb")
print(UPConfig)
TimeStep = ['ts1','timestep1']
UPConfig['Redev'] = None
initable = au.MakePolyList(UPConfig)
initable.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\iniout_r1_1.csv")
# outtable = au.MakeDevSpace(UPConfig, TimeStep)
# outtable.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\DevSpace_r2_2.csv")

# lu='ind'
# ##test merge data frames
# # get unconstrained space
# dswhereclause = """ TimeStep = '{ts}' and lu = '{lu}' """.format(ts= TimeStep[0],lu=lu)
# dsarray = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_const'),[UPConfig['BaseGeom_id'],'developable_acres'],dswhereclause) # TODO: rename this to unconstrained_acres
# dsdf = pd.DataFrame(dsarray)
# dsdf.columns = [[UPConfig['BaseGeom_id'],'uncon_ac_{ts}_{lu}'.format(ts=TimeStep[0],lu=lu)]]
# dsarray = None
#   
# dsdf.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\dsdf1.csv")
#   
# testmerge = Utilities.MergeDataFrames([initable,dsdf], str(UPConfig['BaseGeom_id']))
# testmerge.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\testmerge1.csv")
# 
# # get gp permissablity (boolean)
# gparray = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_bg_gp_avail_{ts}'.format(ts=TimeStep[0])),[UPConfig['BaseGeom_id'],'gp_{lu}'.format(lu=lu)])
# gpdf = pd.DataFrame(gparray)
# gpdf.columns = [[UPConfig['BaseGeom_id'],'gp_{ts}_{lu}'.format(ts=TimeStep[0],lu=lu)]]
# gparray = None
# 
# gpdf.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\gpdf1.csv")
# 
# testmerge2 = Utilities.MergeDataFrames([initable,dsdf,gpdf], str(UPConfig['BaseGeom_id']))
# testmerge2.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\testmerge2.csv")
# 
# # get net weights
# wtwhereclause = """ timestep = '{ts}' and lu = '{lu}' """.format(ts= TimeStep[0],lu=lu)
# wtarray = arcpy.da.TableToNumPyArray(os.path.join(UPConfig['paths']['dbpath'],UPConfig['paths']['dbname'],'up_net_weights'),[UPConfig['BaseGeom_id'],'weight'],wtwhereclause)
# wtdf = pd.DataFrame(wtarray)
# wtdf.columns = [[UPConfig['BaseGeom_id'],'wt_{ts}_{lu}'.format(ts=TimeStep[0],lu=lu)]]
# wtarray = None
# 
# wtdf.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\wtdf1.csv")
# 
# testmerge3 = Utilities.MergeDataFrames([initable,dsdf,gpdf,wtdf], str(UPConfig['BaseGeom_id']))
# testmerge3.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\testmerge3.csv")





# devSpaceTable = au.MakeDevSpace(UPConfig, ['ts1','timestep1'])
# devSpaceTable.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\TestOut6.csv")



# OutArray = Utilities.ConvertPdDataFrameToNumpyArray(devSpaceTable)
# dtype = OutArray.dtype.descr
# dtype[0] = (dtype[0][0],'|S8')
# dtype = np.dtype(dtype)
# OutArray = OutArray.astype(dtype)
# arcpy.da.NumPyArrayToTable(OutArray,r"G:\Public\UPLAN\Uplan4\testing\temp\TestOut2")

# # test utilites.mergedataframe
# table1 = {
#         'pid': ['1', '2', '3', '4'],
#         'gp': ['A', 'B', 'C', 'D']}
# df1 = pd.DataFrame(table1, columns = ['pid','gp'])
# table2 = {
#         'pid': ['1', '4', '2', '3'],
#         'lu': ['J', 'K', 'L', 'M']}
# df2 = pd.DataFrame(table2, columns = ['pid','lu'])
# table3 = {
#         'pid': ['4', '1', '3', '2'],
#         'cons': ['Q', 'R', 'S', 'T']}
# df3 = pd.DataFrame(table3, columns = ['pid','cons'])
#  
# df3 = Utilities.MergeDataFrames([df1,df2,df3], 'pid')
# df3.to_csv(r"G:\Public\UPLAN\Uplan4\testing\temp\testmerge01.csv")








print('script finished!!')