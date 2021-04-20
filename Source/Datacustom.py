import os
import scipy.io
import numpy as np
import argparse

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--file", type=str, default='/home/ljj/PycharmWork/CtoP/Data/Cylinder2D.mat')
parser.add_argument("--gap", type=int, default=2)
args = parser.parse_args()
file1 = args.file
gap = args.gap

r0=scipy.io.loadmat(file1)

c0=r0['C_star']
cc=c0[0]
cx=c0[0][0]
cy=c0[0][1]
p0=r0['P_star']
u0=r0['U_star']
v0=r0['V_star']
t0=r0['t_star']
x0=r0['x_star']
y0=r0['y_star']
shape=np.shape(c0)
t_step=shape[1]
pos_num=shape[0]

if t_step%gap==0:
    new_tstep = int(t_step / gap)
else:
    new_tstep=int(t_step/gap)+1

c1=np.zeros((pos_num,new_tstep))
p1=np.zeros((pos_num,new_tstep))
u1=np.zeros((pos_num,new_tstep))
v1=np.zeros((pos_num,new_tstep))
t1=np.zeros((new_tstep,np.shape(t0)[1]))
print('origin.shape=',np.shape(c0),'  new.shape=',np.shape(c1),np.shape(p1),np.shape(u1),np.shape(v1),'  new_t.shape=',np.shape(t1))
for i in range(t_step):
    if (i % gap) == 0:
        t1[int(i/gap)][0]=t0[i]
# print(t1,np.shape(t1))
for j in range(pos_num):
    for i in range(t_step):
        if (i%gap)==0:
            c1[j][int(i/gap)]=c0[j][i]
            p1[j][int(i/gap)]=p0[j][i]
            u1[j][int(i/gap)]=u0[j][i]
            v1[j][int(i/gap)]=v0[j][i]

# print(t1[0:20],t0[0:20])
# print(c1[0][:20],\n c0[0][:20])
# print(p1[0][:20],\n p0[0][:20])
# print(u1[0][:20],\n u0[0][:20])
# print(v1[0][:20],\n v0[0][:20])

# Linux system savepath (Not compliant with Windows for '/' split)
workdir=os.getcwd()
savemat_path='/'.join(workdir.split('/')[:-1])+'/Data'
if not os.path.exists(savemat_path):
    os.makedirs(savemat_path)

origin_fname=(file1.split('/')[-1]).split('.')[0]
savemat_name=origin_fname+'_tsplit_{}.mat'.format(gap)
savefile=savemat_path+'/'+savemat_name
scipy.io.savemat(savefile,{'C_star': c1, 'U_star': u1, 'V_star': v1, 'P_star': p1,'t_star':t1,'x_star':x0,'y_star':y0})
print('------------Mission accomplished: .mat custom:{}.-----------------\nTime split (gap)={}'.format(savefile,gap))