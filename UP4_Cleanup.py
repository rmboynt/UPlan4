'''
might be old (RB,NR 8/15/15)

Created on Jan 16, 2015

@author: roth
'''
import arcpy, os, sys, UPlan4

   

if __name__ == "__main__":
    fds = r"cal_fds"
    dbpath = r"..\testing\cal_test.gdb"
    LUPriorities= ['ind','ret','ser','rh','rm','rl','rvl']
    
    UPlan4.UPCleanup(dbpath,fds,LUPriorities)
    pass