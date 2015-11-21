import numpy as np
import theano
import theano.tensor as T
from utils import create_shared, random_weights

floatX = theano.config.floatX
device = theano.config.device


class RNN(object):
    """
    Recurrent neural network. Can be used with or without batches.
    Without batches:
        Input: matrix of dimension (sequence_length, input_dim)
        Output: vector of dimension (output_dim)
    With batches:
        Input: tensor3 of dimension (sequence_length, batch_size, input_dim)
        Output: matrix of dimension (batch_size, output_dim)
    """

    def __init__(self, input_dim, hidden_dim, activation=T.nnet.sigmoid,
                 with_batch=True, name='RNN'):
        """
        Initialize neural network.
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.activation = activation
        self.with_batch = with_batch
        self.name = name

        # Randomly generate weights
        self.w_x = create_shared(random_weights((input_dim, hidden_dim)), name + '__w_x')
        self.w_h = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__w_h')

        # Initialize the bias vector and h_0 to zero vectors
        self.b_h = create_shared(np.zeros((hidden_dim,)), name + '__b_h')
        self.h_0 = create_shared(np.zeros((hidden_dim,)), name + '__h_0')

        # Define parameters
        self.params = [self.w_x, self.w_h, self.b_h, self.h_0]

    def link(self, input):
        """
        Propagate the input through the network and return the last hidden vector.
        The whole sequence is also accessible through self.h
        """

        def recurrence(x_t, h_tm1):
            return self.activation(T.dot(x_t, self.w_x) + T.dot(h_tm1, self.w_h) + self.b_h)

        # If we used batches, we have to permute the first and second dimension.
        if self.with_batch:
            self.input = input.dimshuffle(1, 0, 2)
            outputs_info = T.alloc(self.h_0, self.input.shape[1], self.hidden_dim)
        else:
            self.input = input
            outputs_info = self.h_0

        h, _ = theano.scan(
            fn=recurrence,
            sequences=self.input,
            outputs_info=outputs_info,
            n_steps=self.input.shape[0]
        )
        self.h = h
        self.output = h[-1]

        return self.output


class LSTM(object):
    """
    Recurrent neural network. Can be used with or without batches.
    Without batches:
        Input: matrix of dimension (sequence_length, input_dim)
        Output: vector of dimension (output_dim)
    With batches:
        Input: tensor3 of dimension (sequence_length, batch_size, input_dim)
        Output: matrix of dimension (batch_size, output_dim)
    """

    def __init__(self, input_dim, hidden_dim, with_batch=True, name='LSTM'):
        """
        Initialize neural network.
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.with_batch = with_batch
        self.name = name

        # Input gate weights
        self.w_xi = create_shared(random_weights((input_dim, hidden_dim)), name + '__w_xi')
        self.w_hi = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__w_hi')
        self.w_ci = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__w_ci')

        # Forget gate weights
        #self.w_xf = create_shared(random_weights((input_dim, hidden_dim)), name + '__w_xf')
        #self.w_hf = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__w_hf')
        #self.w_cf = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__w_cf')

        # Output gate weights
        self.w_xo = create_shared(random_weights((input_dim, hidden_dim)), name + '__w_xo')
        self.w_ho = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__w_ho')
        self.w_co = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__w_co')

        # Cell weights
        self.w_xc = create_shared(random_weights((input_dim, hidden_dim)), name + '__w_xc')
        self.w_hc = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__w_hc')

        # Initialize the bias vectors, c_0 and h_0 to zero vectors
        self.b_i = create_shared(np.zeros((hidden_dim,)), name + '__b_i')
        self.b_f = create_shared(np.zeros((hidden_dim,)), name + '__b_f')
        self.b_c = create_shared(np.zeros((hidden_dim,)), name + '__b_c')
        self.b_o = create_shared(np.zeros((hidden_dim,)), name + '__b_o')
        self.c_0 = create_shared(np.zeros((hidden_dim,)), name + '__c_0')
        self.h_0 = create_shared(np.zeros((hidden_dim,)), name + '__h_0')

        # Define parameters
        self.params = [self.w_xi, self.w_hi, self.w_ci,
                       # self.w_xf, self.w_hf, self.w_cf,
                       self.w_xo, self.w_ho, self.w_co,
                       self.w_xc, self.w_hc,
                       self.b_i, self.b_c, self.b_o, # self.b_f, 
                       self.c_0, self.h_0]

    def link(self, input):
        """
        Propagate the input through the network and return the last hidden vector.
        The whole sequence is also accessible through self.h
        """

        def recurrence(x_t, c_tm1, h_tm1):
            i_t = T.nnet.sigmoid(T.dot(x_t, self.w_xi) + T.dot(h_tm1, self.w_hi) + T.dot(c_tm1, self.w_ci) + self.b_i)
            # f_t = T.nnet.sigmoid(T.dot(x_t, self.w_xf) + T.dot(h_tm1, self.w_hf) + T.dot(c_tm1, self.w_cf) + self.b_f)
            c_t = (1 - i_t) * c_tm1 + i_t * T.tanh(T.dot(x_t, self.w_xc) + T.dot(h_tm1, self.w_hc) + self.b_c)
            o_t = T.nnet.sigmoid(T.dot(x_t, self.w_xo) + T.dot(h_tm1, self.w_ho) + T.dot(c_t, self.w_co) + self.b_o)
            h_t = o_t * T.tanh(c_t)
            return [c_t, h_t]

        # If we used batches, we have to permute the first and second dimension.
        if self.with_batch:
            self.input = input.dimshuffle(1, 0, 2)
            outputs_info = [T.alloc(x, self.input.shape[1], self.hidden_dim) for x in [self.c_0, self.h_0]]
        else:
            self.input = input
            outputs_info = [self.c_0, self.h_0]

        [_, h], _ = theano.scan(
            fn=recurrence,
            sequences=self.input,
            outputs_info=outputs_info,
            n_steps=self.input.shape[0]
        )
        self.h = h
        self.output = h[-1]

        return self.output


class GRU(object):
    """
    Gated Recurrent Units (GRU). Can be used with or without batches.
    Without batches:
        Input: matrix of dimension (sequence_length, input_dim)
        Output: vector of dimension (output_dim)
    With batches:
        Input: tensor3 of dimension (sequence_length, batch_size, input_dim)
        Output: matrix of dimension (batch_size, output_dim)
    """

    def __init__(self, input_dim, hidden_dim, with_batch=True, name='LSTM'):
        """
        Initialize neural network.
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.with_batch = with_batch
        self.name = name

        # Update gate weights and bias
        self.w_z = create_shared(random_weights((input_dim, hidden_dim)), name + '__w_z')
        self.u_z = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__u_z')
        self.b_z = create_shared(np.zeros((hidden_dim,)), name + '__b_z')

        # Reset gate weights and bias
        self.w_r = create_shared(random_weights((input_dim, hidden_dim)), name + '__w_r')
        self.u_r = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__u_r')
        self.b_r = create_shared(np.zeros((hidden_dim,)), name + '__b_r')

        # New memory content weights and bias
        self.w_c = create_shared(random_weights((input_dim, hidden_dim)), name + '__w_c')
        self.u_c = create_shared(random_weights((hidden_dim, hidden_dim)), name + '__u_c')
        self.b_c = create_shared(np.zeros((hidden_dim,)), name + '__b_c')

        # Initialize the bias vector, h_0, to the zero vector
        self.h_0 = create_shared(np.zeros((hidden_dim,)), name + '__h_0')

        # Define parameters
        self.params = [self.w_z, self.u_z, self.b_z,
                       self.w_r, self.u_r, self.b_r,
                       self.w_c, self.u_c, self.b_c,
                       self.h_0]

    def link(self, input):
        """
        Propagate the input through the network and return the last hidden vector.
        The whole sequence is also accessible through self.h
        """

        def recurrence(x_t, h_tm1):
            z_t = T.nnet.sigmoid(T.dot(x_t, self.w_z) + T.dot(h_tm1, self.u_z) + self.b_z)
            r_t = T.nnet.sigmoid(T.dot(x_t, self.w_r) + T.dot(h_tm1, self.u_r) + self.b_r)
            c_t = T.tanh(T.dot(x_t, self.w_c) + T.dot(r_t * h_tm1, self.u_c) + self.b_c)
            h_t = (1 - z_t) * h_tm1 + z_t * c_t
            return h_t

        # If we used batches, we have to permute the first and second dimension.
        if self.with_batch:
            self.input = input.dimshuffle(1, 0, 2)
            outputs_info = T.alloc(self.h_0, self.input.shape[1], self.hidden_dim)
        else:
            self.input = input
            outputs_info = self.h_0

        h, _ = theano.scan(
            fn=recurrence,
            sequences=self.input,
            outputs_info=outputs_info,
            n_steps=self.input.shape[0]
        )
        self.h = h
        self.output = h[-1]

        return self.output
