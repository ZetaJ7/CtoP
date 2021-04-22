import os
import scipy.io
import numpy as np
file1='/home/ljj/PycharmWork/CtoP/Data/Cylinder2D_tsplit_5.mat'
#file2=''
r0=scipy.io.loadmat(file1)
print('shape of file=',np.shape(r0['C_star']),'\nfile message:\n',r0)