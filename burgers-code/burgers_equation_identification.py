# -*- coding: utf-8 -*-
"""Burgers_equation_identification.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Mo-xvOVLLY--jU5oM3_OSbzBtkiNHpvF
"""

import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import scipy.io
from scipy.interpolate import griddata
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.gridspec as gridspec
import time

import pandas as pd
import matplotlib as mpl

from google.colab import drive, files
drive.mount('/content/gdrive/')

class PhysicsInformedNN:
    # Initialize the class
    def __init__(self, X, u, layers, lb, ub, gamma):
        
        self.lb = lb # lower bound [t_lower, x_lower]
        self.ub = ub # upper bound [t_upper, x_upper]
        
        self.gamma = gamma
        
        self.x = X[:,0:1]
        self.t = X[:,1:2]
        self.u = u
        
        self.layers = layers
        
        # Initialize NNs
        self.weights, self.biases = self.initialize_NN(layers)
        
        # tf placeholders and graph
        self.sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True,
                                                     log_device_placement=True))
        
        # Initialize parameters
        self.lambda_1 = tf.Variable([0.0], dtype=tf.float32)
        self.lambda_2 = tf.Variable([-6.0], dtype=tf.float32)
        
        self.x_tf = tf.placeholder(tf.float32, shape=[None, self.x.shape[1]])
        self.t_tf = tf.placeholder(tf.float32, shape=[None, self.t.shape[1]])
        self.u_tf = tf.placeholder(tf.float32, shape=[None, self.u.shape[1]])
                
        self.u_pred = self.net_u(self.x_tf, self.t_tf)
        self.f_pred = self.net_f(self.x_tf, self.t_tf)
        
        self.loss = tf.reduce_mean(tf.square(self.u_tf - self.u_pred)) + \
                    self.gamma * tf.reduce_mean(tf.square(self.f_pred))
        
        self.optimizer = tf.contrib.opt.ScipyOptimizerInterface(self.loss, 
                                                                method = 'L-BFGS-B', 
                                                                options = {'maxiter': 50000,
                                                                           'maxfun': 50000,
                                                                           'maxcor': 50,
                                                                           'maxls': 50,
                                                                           'ftol' : 1.0 * np.finfo(np.float32).eps})
    
        self.optimizer_Adam = tf.train.AdamOptimizer()
        self.train_op_Adam = self.optimizer_Adam.minimize(self.loss)
        
        init = tf.global_variables_initializer()
        self.sess.run(init)
    
    # Initializes the weights and the biases for the NN with the Xavier weight that generally scales the weights 
    # with the shapes of the input and output dimensions of the layers
    def initialize_NN(self, layers):        
        weights = []
        biases = []
        num_layers = len(layers) 
        for l in range(0,num_layers-1):
            W = self.xavier_init(size=[layers[l], layers[l+1]])
            b = tf.Variable(tf.zeros([1,layers[l+1]], dtype=tf.float32), dtype=tf.float32)
            weights.append(W)
            biases.append(b)        
        return weights, biases
        
    def xavier_init(self, size):
        in_dim = size[0]
        out_dim = size[1]        
        xavier_stddev = np.sqrt(2/(in_dim + out_dim))
        return tf.Variable(tf.truncated_normal([in_dim, out_dim], stddev=xavier_stddev), dtype=tf.float32)
    
    # sets the NN
    def neural_net(self, X, weights, biases):
        num_layers = len(weights) + 1
        
        H = 2.0*(X - self.lb)/(self.ub - self.lb) - 1.0
        for l in range(0,num_layers-2):
            W = weights[l]
            b = biases[l]
            H = tf.tanh(tf.add(tf.matmul(H, W), b)) # this is activation function
        W = weights[-1]
        b = biases[-1]
        Y = tf.add(tf.matmul(H, W), b)
        return Y
            
    def net_u(self, x, t):  
        u = self.neural_net(tf.concat([x,t],1), self.weights, self.biases)
        return u
    
    def net_f(self, x, t):
        lambda_1 = self.lambda_1        
        lambda_2 = tf.exp(self.lambda_2)
        u = self.net_u(x,t)
        u_t = tf.gradients(u, t)[0]
        u_x = tf.gradients(u, x)[0]
        u_xx = tf.gradients(u_x, x)[0]
        f = u_t + lambda_1*u*u_x - lambda_2*u_xx # here it is setted up our function.
        
        return f
    
    # print out the loss result
    def callback(self, loss, lambda_1, lambda_2):
        pass
        #print('Loss: %e, l1: %.5f, l2: %.5f' % (loss, lambda_1, np.exp(lambda_2)))
        
    def train(self, nIter):
        tf_dict = {self.x_tf: self.x, self.t_tf: self.t, self.u_tf: self.u}
        
        start_time = time.time()
       # nIter = 0
        for it in range(nIter):
            self.sess.run(self.train_op_Adam, tf_dict)
            
            # Print
           # if it % 1000 == 0:
           #     elapsed = time.time() - start_time
           #     loss_value = self.sess.run(self.loss, tf_dict)
           #     lambda_1_value = self.sess.run(self.lambda_1)
           #     lambda_2_value = np.exp(self.sess.run(self.lambda_2))
           #     print('It: %d, Loss: %.3e, Lambda_1: %.3f, Lambda_2: %.6f, Time: %.2f' % 
           #             (it, loss_value, lambda_1_value, lambda_2_value, elapsed))

                
                #start_time = time.time()
        
        self.optimizer.minimize(self.sess,
                                feed_dict = tf_dict,
                                fetches = [self.loss, self.lambda_1, self.lambda_2],
                                loss_callback = self.callback)        
        
    def predict(self, X_star):
        
        tf_dict = {self.x_tf: X_star[:,0:1], self.t_tf: X_star[:,1:2]} # check out how does it work
        
        u_star = self.sess.run(self.u_pred, tf_dict)
        f_star = self.sess.run(self.f_pred, tf_dict)
        
        return u_star, f_star
                          
    def get_pde_params(self):
        """Return PDE parameters as tuple."""
        lambda_1 = self.sess.run(self.lambda_1)
        lambda_2 = self.sess.run(self.lambda_2)
        lambda_2 = np.exp(lambda_2)
        
        return lambda_1, lambda_2

# chfnge for other files, when you will be doing the bootstrap
#np.random.seed(1234)
#tf.set_random_seed(1234)

"""# $\gamma$ Cross-Validation"""

nu = 0.01/np.pi

N_u = 3700
layers = [2, 10, 10, 10, 10, 1]

data = scipy.io.loadmat('gdrive/My Drive/Colab Notebooks/burgers_shock.mat')


t = data['t'].flatten()[:, None]
x = data['x'].flatten()[:, None]
Exact = np.real(data['usol']).T

#x = np.linspace(-1, 1, num=201)
#t = np.linspace(0, 1.0, num=101)

X, T = np.meshgrid(x, t)
#Exact = -np.pi*nu*np.sin(np.pi*X) / (np.pi*nu*np.exp(np.pi**2 * nu* T) - (np.exp(np.pi**2 * nu* T) - 1)*np.cos(np.pi*X))
#Exact = np.exp(-X**2 / (1 + 4*T)) / np.sqrt(1 + 4*T)
#Exact = np.exp(-T) * np.exp(-X**2)


X_star = np.hstack((X.flatten()[:, None], T.flatten()[:, None]))
u_star = Exact.flatten()[:, None]

# Doman bounds
lb = X_star.min(axis=0)
ub = X_star.max(axis=0)

start_time = time.time()

#gamma_values = np.array([0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
#gamma_values = np.array([2, 3])
gamma_values = np.logspace(-10, 0.7, num=15)
#gamma_values = np.concatenate((np.linspace(-2.7, -1.7, num=10), np.linspace(-1., -0.2, num=10)))
# Number of folds in cross-validation.
K = 5

noise = 0.0
CV_times = 10
cv_res = []

for iteration in range(CV_times):

  idx = np.random.choice(X_star.shape[0], N_u, replace=False)
  X_u_observed = X_star[idx,:]
  u_observed = u_star[idx,:]

  error_MSE_table = np.empty((len(gamma_values), K))
  error_MSE_rel_table = np.empty((len(gamma_values), K))
  error_loss_table = np.empty((len(gamma_values), K))
  error_lambda_1_table = np.empty((len(gamma_values), K))
  error_lambda_2_table = np.empty((len(gamma_values), K))

  lambda_exact_1 = 1.0
  lambda_exact_2 = 0.01 / np.pi

  from sklearn.model_selection import KFold
  kfold = KFold(n_splits=K, shuffle=False)

  res = {'i': [], 'gamma': [], 'j': [], 'error_MSE_table': [], 'error_MSE_rel_table': [], 'error_lambda_1_table': [], 
        'error_lambda_2_table': [], 'lambda_1_estim': [], 'lambda_2_estim': []}

  for i, gamma in enumerate(gamma_values):
    print('=== {} ==='.format(iteration))
    print('Gamma = ', gamma)
    j = 0
    for train_idx, test_idx in kfold.split(X_u_observed):

      print('Fold :', j)
      X_u_train, X_u_test = X_u_observed[train_idx], X_u_observed[test_idx]
      u_train, u_test = u_observed[train_idx], u_observed[test_idx]

      #u_train = u_train + noise*np.std(u_train)*np.random.randn(u_train.shape[0], u_train.shape[1])
      u_train = u_train (1 + noise*randn)

      model = PhysicsInformedNN(X_u_train, u_train, layers, lb, ub, gamma)
      model.train(0)

      u_pred, f_pred = model.predict(X_u_test)

      error_MSE_table[i, j] = np.sum((u_test-u_pred)**2) / len(u_test)
      error_MSE_rel_table[i, j] = np.linalg.norm(u_test-u_pred,2)/np.linalg.norm(u_test,2)
      #res['loss'] += model.sess.run(model.loss)

      lambda_estim_1, lambda_estim_2 = model.get_pde_params()

      error_lambda_1_table[i, j], error_lambda_2_table[i, j] = abs(lambda_estim_1 - lambda_exact_1), abs(lambda_estim_2 - lambda_exact_2)

      res['i'].append(i)
      res['gamma'].append(gamma)
      res['j'].append(j)
      res['error_MSE_table'].append(error_MSE_table[i, j])
      res['error_MSE_rel_table'].append(error_MSE_rel_table[i, j])
      res['error_lambda_1_table'].append(error_lambda_1_table[i, j])
      res['error_lambda_2_table'].append(error_lambda_2_table[i, j])
      res['lambda_1_estim'].append(lambda_estim_1)
      res['lambda_2_estim'].append(lambda_estim_2)
      j += 1
 
  result = pd.DataFrame(res)  
  path = 'gdrive/My Drive/Colab Notebooks/CV/burgers-CV_{}.csv'.format(iteration)
  result.to_csv(path)
  #files.download(path)
  print("It took: ", time.time() - start_time)

"""# $\lambda$ bootstrap"""

# bootstrap of lambdas
gamma = 0.025535411282038508 # was gotten in the previous cell

nu = 0.01/np.pi

N_u = 3700 # points across the entire spatio-temporal domain 

N_u = 3700
layers = [2, 10, 10, 10, 10, 1]

iter_train = 0

data = scipy.io.loadmat('gdrive/My Drive/Colab Notebooks/burgers_shock.mat')

t = data['t'].flatten()[:,None]
x = data['x'].flatten()[:,None]
Exact = np.real(data['usol']).T

X, T = np.meshgrid(x,t)

X_star = np.hstack((X.flatten()[:,None], T.flatten()[:,None]))
u_star = Exact.flatten()[:,None]              

# Domain bounds
lb = X_star.min(0)
ub = X_star.max(0)    

######################################################################
######################## Noiseles Data ###############################
######################################################################
noise = 0.0            

idx = np.random.choice(X_star.shape[0], N_u, replace=False)
X_u_train = X_star[idx,:]
u_train = u_star[idx,:]

######################################################################
########################## Bootstrap #################################
######################################################################

boot_num = 100
res = {'l1': [], 'l2': [], 'err_l1': [], 'err_l2': []}

for i in range(boot_num):
  start_time = time.time()

  idx = np.random.choice(X_u_train.shape[0], int(0.8*N_u), replace=True)
  X_u_boot = X_u_train[idx,:]
  u_boot = u_train[idx,:]
  """ в модель передаем буты, чистую лямбду получишь ниже """

  model = PhysicsInformedNN(X_u_boot, u_boot, layers, lb, ub, gamma)
  model.train(iter_train)

  u_pred, f_pred = model.predict(X_star)

  error_u = np.linalg.norm(u_star-u_pred,2)/np.linalg.norm(u_star,2)

  U_pred = griddata(X_star, u_pred.flatten(), (X, T), method='cubic')

  lambda_1_value = model.sess.run(model.lambda_1)
  lambda_2_value = model.sess.run(model.lambda_2)
  lambda_2_value = np.exp(lambda_2_value)

  error_lambda_1 = np.abs(lambda_1_value - 1.0)*100
  error_lambda_2 = np.abs(lambda_2_value - nu)/nu * 100

  print('Error u: %e' % (error_u))    
  print('Error l1: %.5f%%' % (error_lambda_1))                             
  print('Error l2: %.5f%%' % (error_lambda_2))  

  ######################################################################
  ########################### Noisy Data ###############################
  ######################################################################
  noise = 0.05 # noise is 5%
  
  #u_train = u_train + noise*np.std(u_train)*np.random.randn(u_train.shape[0], u_train.shape[1])

  #model = PhysicsInformedNN(X_u_train, u_train, layers, lb, ub)
  #model.train(iter_train)

  #u_pred, f_pred = model.predict(X_star)

  #lambda_1_value_noisy = model.sess.run(model.lambda_1)
  #lambda_2_value_noisy = model.sess.run(model.lambda_2)
  #lambda_2_value_noisy = np.exp(lambda_2_value_noisy)

  #error_lambda_1_noisy = np.abs(lambda_1_value_noisy - 1.0)*100
  #error_lambda_2_noisy = np.abs(lambda_2_value_noisy - nu)/nu * 100

  #print('Error lambda_1: %f%%' % (error_lambda_1_noisy))
  #print('Error lambda_2: %f%%' % (error_lambda_2_noisy))

  # save data
  #res = np.append([lambda_1_value, lambda_2_value, error_lambda_1, error_lambda_2, lambda_1_value_noisy, 
  #               lambda_2_value_noisy, error_lambda_1_noisy, error_lambda_2_noisy]).flatten()
  
  res['l1'].append(lambda_1_value)
  res['l2'].append(lambda_2_value)
  res['err_l1'].append(error_lambda_1)
  res['err_l2'].append(error_lambda_2)
  
  print('Took time: ', time.time() - start_time)
  print()
  
  result = pd.DataFrame(res)  
  result.to_csv('gdrive/My Drive/Colab Notebooks/bootstrap.csv')

testtt = []
for i in range(len(X_star)):
  if i not in idx: testtt.append(X_star[i])
testtt = np.array(testtt)

print(len(testtt), len(idx), len(X_star))

X_star[23000]

# '$\lamnda dependance on the network capacity. забыл посчитать true value'
nu = 0.01/np.pi
gamma = 0.025535411282038508 # was gotten in the previous cell

N_u = 13200 # [1060, 2200, 5620, 17300] # 0, 1, 2, 4
layers_array = [[2, 5, 1], [2, 5, 5, 1], [2, 5, 5, 5, 5, 1], [2, 5, 5, 5, 5, 5, 5, 1], [2, 5, 5, 5, 5, 5, 5, 5, 5, 1],
                [2, 10, 1], [2, 10, 10, 1], [2, 10, 10, 10, 10, 1], [2, 10, 10, 10, 10, 10, 10, 1], [2, 10, 10, 10, 10, 10, 10, 10, 10, 1],
                [2, 20, 1], [2, 20, 20, 1], [2, 20, 20, 20, 20, 1], [2, 20, 20, 20, 20, 20, 20, 1], [2, 20, 20, 20, 20, 20, 20, 20, 20, 1]]
#layers_array = [[2, 32, 32, 32, 32, 1]]
#layers_array = []
iter_train = 0

data = scipy.io.loadmat('gdrive/My Drive/Colab Notebooks/burgers_shock.mat')

t = data['t'].flatten()[:,None]
x = data['x'].flatten()[:,None]
Exact = np.real(data['usol']).T

X, T = np.meshgrid(x,t)

X_star = np.hstack((X.flatten()[:,None], T.flatten()[:,None]))
u_star = Exact.flatten()[:,None]              

# Doman bounds
lb = X_star.min(0)
ub = X_star.max(0)    

noise = 0.0            

idx = np.random.choice(X_star.shape[0], N_u, replace=False)
X_u_train = X_star[idx,:]
u_train = u_star[idx,:]

X_left, u_left = [], []
for i in range(len(X_star)):
  if i not in idx: 
    X_left.append(X_star[i])
    u_left.append(u_star[i])
X_left, u_left = np.array(X_left), np.array(u_left)
idx2 = np.random.choice(X_left.shape[0], N_u, replace=False)
X_u_test = X_left[idx2, :]
u_test = u_star[idx2, :]

res = {'err_l1': [], 'err_l2': [], 'MSE': []}

for layers in layers_array:

  model = PhysicsInformedNN(X_u_train, u_train, layers, lb, ub, gamma)
  model.train(iter_train)

  u_pred, f_pred = model.predict(X_star)
  u_pred2, f_pred2 = model.predict(X_u_test)

  error_u = np.linalg.norm(u_star-u_pred,2)/np.linalg.norm(u_star,2)
  error_u2 = np.linalg.norm(u_star[idx2, :]-u_pred2,2)/np.linalg.norm(u_star,2)


  U_pred = griddata(X_star, u_pred.flatten(), (X, T), method='cubic')

  lambda_1_value = model.sess.run(model.lambda_1)
  lambda_2_value = model.sess.run(model.lambda_2)
  lambda_2_value = np.exp(lambda_2_value)

  error_lambda_1 = np.abs(lambda_1_value - 1.0)*100
  error_lambda_2 = np.abs(lambda_2_value - nu)/nu * 100

  print('Error u: %e' % (error_u2))    
  print('Error l1: %.5f%%' % (error_lambda_1))                             
  print('Error l2: %.5f%%' % (error_lambda_2))     
  
  res['err_l1'].append(error_lambda_1)
  res['err_l2'].append(error_lambda_2)
  res['MSE'].append(error_u2)
  
result = pd.DataFrame(res)  
result.to_csv('gdrive/My Drive/Colab Notebooks/layers_neuron_error.csv')

result

nu = 0.01/np.pi

N_u = 370
layers = [2, 10, 10, 10, 10, 1]
gamma = 0.025535411282038508 # was gotten in the previous cell

iter_train = 10000

data = scipy.io.loadmat('gdrive/My Drive/Colab Notebooks/burgers_shock.mat')

t = data['t'].flatten()[:,None]
x = data['x'].flatten()[:,None]
Exact = np.real(data['usol']).T

X, T = np.meshgrid(x,t)

X_star = np.hstack((X.flatten()[:,None], T.flatten()[:,None]))
u_star = Exact.flatten()[:,None]              

# Doman bounds
lb = X_star.min(0)
ub = X_star.max(0)    

######################################################################
######################## Noiseles Data ###############################
######################################################################
noise = 0.0            

idx = np.random.choice(X_star.shape[0], N_u, replace=False)
X_u_train = X_star[idx,:]
u_train = u_star[idx,:]

model = PhysicsInformedNN(X_u_train, u_train, layers, lb, ub, gamma)
model.train(iter_train)

u_pred, f_pred = model.predict(X_star)

error_u = np.linalg.norm(u_star-u_pred,2)/np.linalg.norm(u_star,2)

U_pred = griddata(X_star, u_pred.flatten(), (X, T), method='cubic')

lambda_1_value = model.sess.run(model.lambda_1)
lambda_2_value = model.sess.run(model.lambda_2)
lambda_2_value = np.exp(lambda_2_value)

error_lambda_1 = np.abs(lambda_1_value - 1.0)*100
error_lambda_2 = np.abs(lambda_2_value - nu)/nu * 100

print('Error u: %e' % (error_u))    
print('Error l1: %.5f%%' % (error_lambda_1))                             
print('Error l2: %.5f%%' % (error_lambda_2))  

######################################################################
########################### Noisy Data ###############################
######################################################################
noise = 0.5        
u_train = u_train + noise*np.std(u_train)*np.random.randn(u_train.shape[0], u_train.shape[1])

model = PhysicsInformedNN(X_u_train, u_train, layers, lb, ub, gamma)
model.train(iter_train)

u_pred, f_pred = model.predict(X_star)

U_noisy_pred = griddata(X_star, u_pred.flatten(), (X, T), method='cubic')

lambda_1_value_noisy = model.sess.run(model.lambda_1)
lambda_2_value_noisy = model.sess.run(model.lambda_2)
lambda_2_value_noisy = np.exp(lambda_2_value_noisy)

error_lambda_1_noisy = np.abs(lambda_1_value_noisy - 1.0)*100
error_lambda_2_noisy = np.abs(lambda_2_value_noisy - nu)/nu * 100

print('Error lambda_1: %f%%' % (error_lambda_1_noisy))
print('Error lambda_2: %f%%' % (error_lambda_2_noisy))

error_u = np.linalg.norm(u_star-u_pred,2)/np.linalg.norm(u_star,2)
print(error_u)

fig, subplots = plt.subplots(nrows = 1, ncols = 1, figsize = (12, 8), 
                              facecolor = 'w', edgecolor = 'k')
ax = fig.axes[0]

h = ax.imshow(U_pred.T, interpolation='nearest', cmap='viridis', 
              extent=[t.min(), t.max(), x.min(), x.max()], 
              origin='lower', aspect='auto')
plt.xlabel('$t$', fontsize = 14)
plt.ylabel('$x$', fontsize = 14)

divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.05)
fig.colorbar(h, cax=cax)

ax.plot(X_u_train[:,1], X_u_train[:,0], 'rx', label = 'Data (%d points)' % (u_train.shape[0]), markersize = 4, clip_on = False)


ax.legend(loc=1, frameon=True)
ax.set_title('$u(t,x)$', fontsize = 14)

plt.savefig('gdrive/My Drive/Colab Notebooks/burgers-exact.png', format = 'png', transparent=True)

#plt.style.use('bmh')
fig, subplots = plt.subplots(nrows=1, ncols =3, sharey=True, figsize=(12, 9), facecolor='w', edgecolor='k')

fig.axes[0].plot(x, Exact[25,:], 'y-', linewidth = 2, label = 'Exact')       
fig.axes[0].plot(x, U_noisy_pred[25,:], 'r--', linewidth = 2, label = 'Prediction')  
fig.axes[0].set_title('$t = 0.25$', fontsize = 14)

fig.axes[1].plot(x, Exact[45,:], 'y-', linewidth = 2, label = 'Exact')       
fig.axes[1].plot(x, U_noisy_pred[45,:], 'r--', linewidth = 2, label = 'Prediction')  
fig.axes[1].set_title('$t = 0.45$', fontsize = 14)

fig.axes[2].plot(x, Exact[75,:], 'y-', linewidth = 2, label = 'Exact')       
fig.axes[2].plot(x, U_noisy_pred[75,:], 'r--', linewidth = 2, label = 'Prediction')  
fig.axes[2].set_title('$t = 0.75$', fontsize = 14)

for i in range(len(fig.axes)):
  fig.axes[i].set_xlabel('$x$', fontsize=14) 
  fig.axes[i].axis('square')
  fig.axes[i].set_xlim([-1.1,1.1])
  fig.axes[i].set_ylim([-1.1,1.1])
  fig.axes[i].grid(True)
  fig.axes[i].grid(color='k', linestyle='--', linewidth = 0.5)
  fig.axes[i].legend(fontsize = 10, loc = 1)
  
fig.axes[0].set_ylabel('$u(t,x)$', fontsize=14) 

plt.savefig('gdrive/My Drive/Colab Notebooks/burgers-exact-predict.png', format = 'png', transparent=True)
plt.show()

c