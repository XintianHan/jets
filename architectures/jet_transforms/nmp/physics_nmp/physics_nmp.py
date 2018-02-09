import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable

from data_ops.batching import batch_leaves

from architectures.readout import construct_readout
from architectures.embedding import construct_embedding
from ..stacked_nmp.attention_pooling import construct_pooling_layer
from .adjacency import construct_physics_based_adjacency_matrix
from ..message_passing import construct_mp_layer
from ..message_passing.adjacency import construct_adjacency_matrix_layer

class FixedAdjacencyNMP(nn.Module):
    def __init__(self,
        features=None,
        hidden=None,
        iters=None,
        readout=None,
        **kwargs
        ):
        super().__init__()
        self.iters = iters
        self.embedding = construct_embedding('simple', features + 1, hidden, act=kwargs.get('act', None))
        self.mp_layers = nn.ModuleList([construct_mp_layer('fixed', hidden=hidden,**kwargs) for _ in range(iters)])
        self.readout = construct_readout(readout, hidden, hidden)
        self.adjacency_matrix = self.set_adjacency_matrix(features=features, **kwargs)

    def set_adjacency_matrix(self, **kwargs):
        pass

    def forward(self, jets, mask=None, **kwargs):
        h = self.embedding(jets)
        dij = self.adjacency_matrix(jets, mask=mask)
        for mp in self.mp_layers:
            h, _ = mp(h=h, mask=mask, dij=dij, **kwargs)
        out = self.readout(h)
        return out, _

class PhysicsNMP(FixedAdjacencyNMP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_adjacency_matrix(self, **kwargs):
        self.alpha = kwargs.pop('alpha', None)
        self.R = kwargs.pop('R', None)
        self.trainable_physics = kwargs.pop('trainable_physics', None)

        return construct_physics_based_adjacency_matrix(
                        alpha=self.alpha,
                        R=self.R,
                        trainable_physics=self.trainable_physics
                        )

class EyeNMP(FixedAdjacencyNMP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_adjacency_matrix(self, **kwargs):
        def eye(jets, **kwargs):
            bs, sz, _ = jets.size()
            matrix = Variable(torch.eye(sz).unsqueeze(0).repeat(bs, 1, 1))
            if torch.cuda.is_available():
                matrix = matrix.cuda()
            return matrix
        return eye

class OnesNMP(FixedAdjacencyNMP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_adjacency_matrix(self, **kwargs):
        def ones(jets, **kwargs):
            bs, sz, _ = jets.size()
            matrix = Variable(torch.ones(bs, sz, sz))
            if torch.cuda.is_available():
                matrix = matrix.cuda()
            return matrix
        return ones

class LearnedFixedNMP(FixedAdjacencyNMP):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_adjacency_matrix(self, **kwargs):
        matrix = construct_adjacency_matrix_layer(
                    kwargs.get('adaptive_matrix', None),
                    hidden=kwargs.get('features', None) + 1,
                    symmetric=kwargs.get('symmetric', None)
                    )
        return matrix

class PhysicsStackNMP(nn.Module):
    def __init__(self,
        features=None,
        hidden=None,
        iters=None,
        readout=None,
        scales=None,
        mp_layer=None,
        pooling_layer=None,
        **kwargs
        ):
        super().__init__()
        self.iters = iters
        self.embedding = construct_embedding('simple', features + 1, hidden, act=kwargs.get('act', None))
        self.physics_nmp = PhysicsNMP(features, hidden, 1, readout='constant', **kwargs)
        self.readout = construct_readout(readout, hidden, hidden)
        self.attn_pools = nn.ModuleList([construct_pooling_layer(pooling_layer, scales[i], hidden) for i in range(len(scales))])
        self.nmps = nn.ModuleList([construct_mp_layer(mp_layer, hidden=hidden, **kwargs) for _ in range(len(scales))])

    def forward(self, jets, mask=None, **kwargs):
        h, _ = self.physics_nmp(jets, mask, **kwargs)
        for pool, nmp in zip(self.attn_pools, self.nmps):
            h = pool(h)
            h, A = nmp(h=h, mask=None, **kwargs)
        out = self.readout(h)
        return out, A
