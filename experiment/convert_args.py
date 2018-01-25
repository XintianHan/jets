from architectures import POOLINGS
from architectures import TRANSFORMS
from architectures import MESSAGE_PASSING_LAYERS
from architectures import PREDICTORS
from architectures import ADAPTIVE_MATRICES
from collections import namedtuple

Architecture = namedtuple('Architecture',
        [
         'message_passing_layer',
         'transform',
         'pooling_layer',
         'predict',
         'matrix'
        ]
     )

def convert_args(args):
    def lookup(component_key, component_table):
        if component_key is None: return None, None
        try:
          component_key = int(component_key)
          component_key = [k for k, (n, _) in component_table.items() if n == component_key].pop()
        except ValueError:
          pass
        _, Component = component_table[component_key]
        return component_key, Component

    args.model_type, Transform = lookup(args.model_type, TRANSFORMS)
    args.mp, MessagePassingLayer = lookup(args.mp, MESSAGE_PASSING_LAYERS)
    args.pool, PoolingLayer = lookup(args.pool, POOLINGS)
    args.predict, Predict = lookup(args.predict, PREDICTORS)
    args.matrix, Matrix = lookup(args.matrix, ADAPTIVE_MATRICES)

    architecture = Architecture(
        transform=Transform,
        message_passing_layer=MessagePassingLayer,
        pooling_layer=PoolingLayer,
        predict=Predict,
        matrix=Matrix
    )
    
    return args, architecture
