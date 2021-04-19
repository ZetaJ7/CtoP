"""
@author: Junjie.Li
@Citation: Maziar Raissi
"""
import argparse
import tensorflow as tf
from tensorflow.python import pywrap_tensorflow
import numpy as np
import scipy.io
import time
import sys
import os

from utilities import neural_net, Navier_Stokes_2D, \
    tf_session, mean_squared_error, relative_error

class C2P(object):
    # notational conventions
    # _tf: placeholders for input/output data and points used to regress the equations
    # _pred: output of neural network
    # _eqns: points used to regress the equations
    # _data: input-output data
    # _star: preditions

    def __init__(self, t_data, x_data, y_data, c_data,
                 t_eqns, x_eqns, y_eqns,
                 layers, batch_size,
                 Pec, Rey):

        # specs
        self.layers = layers
        self.batch_size = batch_size

        # flow properties
        self.Pec = Pec
        self.Rey = Rey

        # data
        [self.t_data, self.x_data, self.y_data, self.c_data] = [t_data, x_data, y_data, c_data]
        [self.t_eqns, self.x_eqns, self.y_eqns] = [t_eqns, x_eqns, y_eqns]

        # placeholders
        [self.t_data_tf, self.x_data_tf, self.y_data_tf, self.c_data_tf] = [tf.compat.v1.placeholder(tf.float32, shape=[None, 1])
                                                                            for _ in range(4)]
        [self.t_eqns_tf, self.x_eqns_tf, self.y_eqns_tf] = [tf.compat.v1.placeholder(tf.float32, shape=[None, 1]) for _ in
                                                            range(3)]

        # physics "uninformed" neural networks
        self.net_cuvp = neural_net(self.t_data, self.x_data, self.y_data, layers=self.layers)

        [self.c_data_pred,
         self.u_data_pred,
         self.v_data_pred,
         self.p_data_pred] = self.net_cuvp(self.t_data_tf,
                                           self.x_data_tf,
                                           self.y_data_tf)

        # physics "informed" neural networks
        [self.c_eqns_pred,
         self.u_eqns_pred,
         self.v_eqns_pred,
         self.p_eqns_pred] = self.net_cuvp(self.t_eqns_tf,
                                           self.x_eqns_tf,
                                           self.y_eqns_tf)

        [self.e1_eqns_pred,
         self.e2_eqns_pred,
         self.e3_eqns_pred,
         self.e4_eqns_pred] = Navier_Stokes_2D(self.c_eqns_pred,
                                               self.u_eqns_pred,
                                               self.v_eqns_pred,
                                               self.p_eqns_pred,
                                               self.t_eqns_tf,
                                               self.x_eqns_tf,
                                               self.y_eqns_tf,
                                               self.Pec,
                                               self.Rey)

        # loss
        self.loss = mean_squared_error(self.c_data_pred, self.c_data_tf) + \
                    mean_squared_error(self.e1_eqns_pred, 0.0) + \
                    mean_squared_error(self.e2_eqns_pred, 0.0) + \
                    mean_squared_error(self.e3_eqns_pred, 0.0) + \
                    mean_squared_error(self.e4_eqns_pred, 0.0)

        # optimizers
        self.learning_rate = tf.compat.v1.placeholder(tf.float32, shape=[])
        self.optimizer = tf.compat.v1.train.AdamOptimizer(learning_rate=self.learning_rate)
        self.train_op = self.optimizer.minimize(self.loss)

        self.sess = tf_session()

    def train(self, total_time, learning_rate):

        N_data = self.t_data.shape[0]
        N_eqns = self.t_eqns.shape[0]

        start_time = time.time()
        running_time = 0
        it = 0
        while running_time < total_time:

            idx_data = np.random.choice(N_data, min(self.batch_size, N_data))
            idx_eqns = np.random.choice(N_eqns, self.batch_size)

            (t_data_batch,
             x_data_batch,
             y_data_batch,
             c_data_batch) = (self.t_data[idx_data, :],
                              self.x_data[idx_data, :],
                              self.y_data[idx_data, :],
                              self.c_data[idx_data, :])

            (t_eqns_batch,
             x_eqns_batch,
             y_eqns_batch) = (self.t_eqns[idx_eqns, :],
                              self.x_eqns[idx_eqns, :],
                              self.y_eqns[idx_eqns, :])

            tf_dict = {self.t_data_tf: t_data_batch,
                       self.x_data_tf: x_data_batch,
                       self.y_data_tf: y_data_batch,
                       self.c_data_tf: c_data_batch,
                       self.t_eqns_tf: t_eqns_batch,
                       self.x_eqns_tf: x_eqns_batch,
                       self.y_eqns_tf: y_eqns_batch,
                       self.learning_rate: learning_rate}

            self.sess.run([self.train_op], tf_dict)

            # Print
            if it % 10 == 0:
                elapsed = time.time() - start_time
                running_time += elapsed / 1.0
                [loss_value,
                 learning_rate_value] = self.sess.run([self.loss,
                                                       self.learning_rate], tf_dict)
                if running_time<=60:
                    print('It: %d, Loss: %.3e, Time: %.2fs, Running Time: %.2fs, Learning Rate: %.1e'
                          % (it, loss_value, elapsed, running_time, learning_rate_value))
                elif (running_time>60) and (running_time<=3600):
                    show_time=running_time/60.0
                    print('It: %d, Loss: %.3e, Time: %.2fs, Running Time: %.2fmin, Learning Rate: %.1e'
                          % (it, loss_value, elapsed, show_time, learning_rate_value))
                else:
                    show_time=running_time/3600.0
                    print('It: %d, Loss: %.3e, Time: %.2fs, Running Time: %.2fh, Learning Rate: %.1e'
                          % (it, loss_value, elapsed, show_time, learning_rate_value))
                sys.stdout.flush()
                start_time = time.time()
            it += 1
        print('--------------------------Model Train Completed--------------------------')

    def predict(self, t_star, x_star, y_star):

        tf_dict = {self.t_data_tf: t_star, self.x_data_tf: x_star, self.y_data_tf: y_star}

        c_star = self.sess.run(self.c_data_pred, tf_dict)
        u_star = self.sess.run(self.u_data_pred, tf_dict)
        v_star = self.sess.run(self.v_data_pred, tf_dict)
        p_star = self.sess.run(self.p_data_pred, tf_dict)

        return c_star, u_star, v_star, p_star

    def w_extract(self,save_file):
        print('Saving model Weights................')
        self.net_cuvp.save_weights(sess=self.sess,save_file=save_file)

    def w_input(self,model_path):
        print('Loading model Weights................')
        self.net_cuvp.read_weights(sess=self.sess,model_path=model_path)

def main():
    batch_size = 10000

    layers = [3] + 10 * [4 * 50] + [4]

    # Load Data
    data = scipy.io.loadmat('../Data/Cylinder2D_flower.mat')

    t_star = data['t_star']  # T x 1
    x_star = data['x_star']  # N x 1
    y_star = data['y_star']  # N x 1

    T = t_star.shape[0]
    N = x_star.shape[0]

    U_star = data['U_star']  # N x T
    V_star = data['V_star']  # N x T
    P_star = data['P_star']  # N x T
    C_star = data['C_star']  # N x T

    # Rearrange Data
    T_star = np.tile(t_star, (1, N)).T  # N x T
    X_star = np.tile(x_star, (1, T))  # N x T
    Y_star = np.tile(y_star, (1, T))  # N x T

    ######################################################################
    ######################## Training Data ###############################
    ######################################################################
    workdir = os.getcwd()
    test_time = 4

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--T", type=int,default=201)
    parser.add_argument("--N", type=int,default=157859)
    parser.add_argument("--mode", type=str,default='train')
    parser.add_argument("--model_path",type=str,default='/'.join(workdir.split('/')[:-1])+'/Model/test_{}/'.format(test_time))
    args = parser.parse_args()
    T_data = args.T
    N_data = args.N
    Running_Mode = args.mode
    model_path=args.model_path
    if Running_Mode=='input':
        if not os.path.exists(model_path):
            raise EnvironmentError('Model path not exist, Please check!')
    # T_data = int(sys.argv[1])
    # N_data = int(sys.argv[2])
    # Running_Mode=sys.argv[3]

    if Running_Mode not in ['train','input']:
        raise ValueError('Wrong Running mode, please check!')
    idx_t = np.concatenate([np.array([0]), np.random.choice(T - 2, T_data - 2, replace=False) + 1, np.array([T - 1])])
    idx_x = np.random.choice(N, N_data, replace=False)
    t_data = T_star[:, idx_t][idx_x, :].flatten()[:, None]
    x_data = X_star[:, idx_t][idx_x, :].flatten()[:, None]
    y_data = Y_star[:, idx_t][idx_x, :].flatten()[:, None]
    c_data = C_star[:, idx_t][idx_x, :].flatten()[:, None]

    T_eqns = T
    N_eqns = N
    idx_t = np.concatenate([np.array([0]), np.random.choice(T - 2, T_eqns - 2, replace=False) + 1, np.array([T - 1])])
    idx_x = np.random.choice(N, N_eqns, replace=False)
    t_eqns = T_star[:, idx_t][idx_x, :].flatten()[:, None]
    x_eqns = X_star[:, idx_t][idx_x, :].flatten()[:, None]
    y_eqns = Y_star[:, idx_t][idx_x, :].flatten()[:, None]

    # Training
    model = C2P(t_data, x_data, y_data, c_data,
                t_eqns, x_eqns, y_eqns,
                layers, batch_size,
                Pec=100, Rey=100)
    print('-----Model Class set completed!-----')

    # Training parameters
    if Running_Mode=='train':
        total_time = 60
        learning_rate = 1e-3
        tgap = 0.08
        print('Working on [{}] mode:training.................'.format(Running_Mode))
        model.train(total_time = total_time, learning_rate=learning_rate)

    #Weighs output
    if Running_Mode !='input':
        print('Working on [{}] mode:Weighs saving.............'.format(Running_Mode))
        fname='test_model.ckpt'
        filepath='/'.join(workdir.split('/')[:-1])+'/Model/test_{}'.format(test_time)
        file=filepath+'/'+fname
        model.w_extract(save_file=file)

    # Weighs input
    if Running_Mode == 'input':
        print('Working on [{}] mode:Weighs loading.............'.format(Running_Mode))
        model.w_input(model_path=model_path)

    # Test Data
    snap = np.array([100])
    t_test = T_star[:, snap]
    x_test = X_star[:, snap]
    y_test = Y_star[:, snap]

    c_test = C_star[:, snap]
    u_test = U_star[:, snap]
    v_test = V_star[:, snap]
    p_test = P_star[:, snap]

    # Prediction
    c_pred, u_pred, v_pred, p_pred = model.predict(t_test, x_test, y_test)

    # Error
    error_c = relative_error(c_pred, c_test)
    error_u = relative_error(u_pred, u_test)
    error_v = relative_error(v_pred, v_test)
    error_p = relative_error(p_pred - np.mean(p_pred), p_test - np.mean(p_test))

    print('Error c: %e' % (error_c))
    print('Error u: %e' % (error_u))
    print('Error v: %e' % (error_v))
    print('Error p: %e' % (error_p))

    ################# Save Data ###########################

    C_pred = 0 * C_star
    U_pred = 0 * U_star
    V_pred = 0 * V_star
    P_pred = 0 * P_star
    for snap in range(0, t_star.shape[0]):
        t_test = T_star[:, snap:snap + 1]
        x_test = X_star[:, snap:snap + 1]
        y_test = Y_star[:, snap:snap + 1]

        c_test = C_star[:, snap:snap + 1]
        u_test = U_star[:, snap:snap + 1]
        v_test = V_star[:, snap:snap + 1]
        p_test = P_star[:, snap:snap + 1]

        # Prediction
        c_pred, u_pred, v_pred, p_pred = model.predict(t_test, x_test, y_test)

        C_pred[:, snap:snap + 1] = c_pred
        U_pred[:, snap:snap + 1] = u_pred
        V_pred[:, snap:snap + 1] = v_pred
        P_pred[:, snap:snap + 1] = p_pred

        # Error
        error_c = relative_error(c_pred, c_test)
        error_u = relative_error(u_pred, u_test)
        error_v = relative_error(v_pred, v_test)
        error_p = relative_error(p_pred - np.mean(p_pred), p_test - np.mean(p_test))

        print('Error c: %e' % (error_c))
        print('Error u: %e' % (error_u))
        print('Error v: %e' % (error_v))
        print('Error p: %e' % (error_p))

    savemat_path='/'.join(workdir.split('/')[:-1])+'/Results'
    if not os.path.exists(savemat_path):
        os.makedirs(savemat_path)
    savemat_name='C2P_result_{}_test{}.mat'.format(Running_Mode,test_time)
    savefile=savemat_path+'/'+savemat_name
    scipy.io.savemat(savefile,{'C_pred': C_pred, 'U_pred': U_pred, 'V_pred': V_pred, 'P_pred': P_pred,
                               'Error c':error_c, 'Error u':error_u,'Error v':error_v, 'Error p':error_p})


if __name__ == "__main__":
    main()
