import os
import scipy.io
import numpy as np
a=int('60*60')
file1='/home/ljj/PycharmWork/CtoP/Results/C2P_result_Cylinder2D_train_testPythontest.mat'
#file2=''
r0=scipy.io.loadmat(file1)
print('shape of file=',np.shape(r0['C_star']),'\nfile message:\n',r0)