import numpy as np
import theano
import theano.tensor as T
import utils
from utils import *
from theano.tensor.nnet import conv
import theano.sandbox.neighbours as TSN


class kmax_pooling_layer_1(object):
    """
    Take as input a 4D array, and return the same array where
    we only take the k largest elements of the last dimension.
    """
    def __init__(self, k_max):
        """
        k_max can be an int or a scalar int.
        """
        self.k_max = k_max

    def link(self, input):
        self.input = input

        # select the lines where we apply k-max pooling
        neighborsForPooling = TSN.images2neibs(
            ten4=self.input,
            neib_shape=(self.input.shape[2], 1), # we look the max on every dimension
            mode='valid'# 'ignore_borders'
        )

        neighborsArgSorted = T.argsort(neighborsForPooling, axis=1)
        kNeighborsArg = neighborsArgSorted[:,-self.k_max:]
        kNeighborsArgSorted = T.sort(kNeighborsArg, axis=1)

        ii = T.repeat(T.arange(neighborsForPooling.shape[0]), self.k_max)
        jj = kNeighborsArgSorted.flatten()
        flattened_pooled_out = neighborsForPooling[ii, jj]

        pooled_out_pre_shape = T.join(0, self.input.shape[:-2], [self.input.shape[3]], [self.k_max])
        self.output = flattened_pooled_out.reshape(pooled_out_pre_shape, ndim=self.input.ndim).dimshuffle(0, 1, 3, 2)
        return self.output


class kmax_pooling_layer_2(object):
    """
    Take as input a 4D array, and return the same array where
    we only take the k largest elements of the last dimension.
    Slightly slower than the previous one, but works even when
    k-max is bigger than the third dimension.
    """
    def __init__(self, k_max):
        """
        k_max can be an int or a scalar int.
        """
        self.k_max = k_max

    def link(self, input):
        self.input = input.dimshuffle(0, 1, 3, 2)
        # get the indexes that give the max on every line and sort them
        ind = T.argsort(self.input, axis=3)
        sorted_ind = T.sort(ind[:, :, :, -self.k_max:], axis=3)
        dim0, dim1, dim2, dim3 = sorted_ind.shape

        # prepare indices for selection
        indices_dim0 = T.arange(dim0).repeat(dim1 * dim2 * dim3)
        indices_dim1 = T.arange(dim1).repeat(dim2 * dim3).reshape((dim1 * dim2 * dim3, 1)).repeat(dim0, axis=1).T.flatten()
        indices_dim2 = T.arange(dim2).repeat(dim3).reshape((dim2 * dim3, 1)).repeat(dim0 * dim1, axis=1).T.flatten()

        # output
        self.output = self.input[indices_dim0, indices_dim1, indices_dim2, sorted_ind.flatten()].reshape(sorted_ind.shape).dimshuffle(0, 1, 3, 2)
        return self.output


def set_k_max(layer, k_top, layer_position, nb_layers, sentence_length):
    """
    Set k_max based on the number of convolutional layers,
    and the layer position in the network.
    http://nal.co/papers/Kalchbrenner_DCNN_ACL14
    """
    alpha = (nb_layers - layer_position) * 1. / nb_layers
    layer.k_max = T.maximum(k_top, T.cast(T.ceil(sentence_length * alpha), 'int32'))