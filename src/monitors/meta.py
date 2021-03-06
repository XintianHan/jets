import os

import numpy as np
import matplotlib
import matplotlib.pyplot as plt

from .baseclasses import ScalarMonitor, Monitor
from ..visualizing.utils import ensure_numpy_array
from ..visualizing.utils import ensure_numpy_float
from ..visualizing.plot_training_stats import plot_one_training_stat
from ..visualizing.utils import image_and_pickle

class Best(ScalarMonitor):
    def __init__(self, monitor, track='max', **kwargs):
        super().__init__('best_' + monitor.name, **kwargs)
        self.monitor = monitor
        self.track = track
        if self.track == 'max':
            self.best_value = -np.inf
        elif self.track == 'min':
            self.best_value = np.inf
        else:
            raise ValueError("track must be max or min")
        self.changed = False

    def call(self, **kwargs):
        value = self.monitor.value
        if self.track == 'max':
            if value > self.best_value:
                self.changed = True
                self.best_value = value
            else:
                self.changed = False
        elif self.track == 'min':
            if value < self.best_value:
                self.changed = True
                self.best_value = value
            else:
                self.changed = False
        return self.best_value

class LogOnImprovement(ScalarMonitor):
    def __init__(self, monitor, trigger_monitor):
        super().__init__('{}_at_{}'.format(monitor.name, trigger_monitor.name))
        self.monitor = monitor
        self.trigger_monitor = trigger_monitor

    def call(self, **kwargs):
        if self.trigger_monitor.changed:
            self.value = self.monitor.value
        return self.value

class Regurgitate(ScalarMonitor):
    def __init__(self, value_name, **kwargs):
        self.value_name = value_name
        super().__init__(value_name, **kwargs)

    def call(self, **kwargs):
        self.value = ensure_numpy_float(kwargs[self.value_name])
        return self.value

class Collect(ScalarMonitor):
    def __init__(self, value_name, fn=None,**kwargs):
        super().__init__(value_name, **kwargs)
        self.value_name = value_name
        if fn == 'mean':
            self.fn = np.mean
        elif fn == 'sum':
            self.fn = np.sum
        elif fn == 'last':
            self.fn = lambda x: x[-1]
        else:
            raise ValueError('only mean/sum/last supported right now')
        self.collection = []

    def call(self, **kwargs):
        value = ensure_numpy_float(kwargs[self.value_name])
        self.collection.append(value)
        self.value = self.fn(self.collection)
        return self.value

    def visualize(self, plotname=None, **kwargs):
        super().visualize()
        if plotname is None:
            plotname = self.name
        plot_one_training_stat(
            plotname,
            self.collection,
            self.plotsdir,
            **kwargs
            )



class Histogram(Monitor):
    def __init__(self, name, n_bins=30, rootname=None, append=False, max_capacity=None, **kwargs):
        super().__init__('{}'.format(name + '_histogram'), **kwargs)
        self.value = None
        self.max_capacity = max_capacity if max_capacity is not None else np.inf
        self.n_bins = n_bins
        self.bin_edges = None
        self.hist = np.zeros((n_bins,))
        self.append = append
        if rootname is None:
            self.rootname = name
        else:
            self.rootname = rootname

    def normalize(self):
        Z = self.hist.sum()
        bin_width = self.bin_edges[1] - self.bin_edges[0]
        self.hist /= (Z * bin_width)

    def call(self, values=None,**kwargs):
        values = ensure_numpy_array(values)
        hist, self.bin_edges = np.histogram(values, bins=self.n_bins, range=(0, 1), density=True)
        self.hist += hist
        return None

    def visualize(self, plotname=None):
        super().visualize()
        fig, ax = plt.subplots()
        #hist, bin_edges = np.histogram(self.value, bins=self.n_bins, range=(0, 1), density=True)
        #import ipdb; ipdb.set_trace()
        self.normalize()
        hist, bin_edges = self.hist, self.bin_edges
        plt.bar(bin_edges[:-1], hist, width=0.7 / self.n_bins)
        # labelling
        plt.suptitle('Histogram of {}'.format(self.name))
        plt.xlabel("Range of {}".format(self.name))
        plt.ylabel("Density")

        if plotname is None:
            plotname = self.name + str(self.visualize_count)

        image_and_pickle(fig, os.path.join(plotname, 'histogram'), self.plotsdir, os.path.join(self.plotsdir, 'pkl'))
        plt.close(fig)

        #self.visualize_count += 1


    def clear(self):
        self.value = None

class EachClassHistogram(Monitor):
    def __init__(self, target_values, target_name, output_name, append=False, **kwargs):
        super().__init__('histogram-{}'.format(target_name), **kwargs)
        self.scalar = False
        self.target_name = target_name
        self.output_name = output_name
        self.target_values = target_values
        self.histogram_monitors = {val: Histogram(self.target_name + str(val), rootname=self.name, append=append,**kwargs) for val in self.target_values}

    def initialize(self, statsdir, plotsdir):
        super().initialize(statsdir, plotsdir)
        for child in self.histogram_monitors.values():
            child.initialize(statsdir, plotsdir)

    def call(self, **kwargs):
        targets = kwargs[self.target_name]
        outputs = kwargs[self.output_name]
        for val, hm in self.histogram_monitors.items():
            values = np.array([o for (t,o) in zip(targets, outputs) if t == val])
            hm(values=values)


    #def finish(self):
    #    for _, hm in self.histogram_monitors.items():
    #        hm.finish()
    #    plt.figure()
    #    plt.ylabel('Probability density')
    #    plt.xlabel('Positive classification probability')
    #    for name, hm in self.histogram_monitors.items():
    #        bins, hist = hm.bins, hm.hist
    #        width = 0.7 * (bins[1] - bins[0])
    #        center = (bins[:-1] + bins[1:]) / 2
    #        bars = plt.bar(center, hist, align='center', width=width)
    #    plt.savefig(os.path.join(self.plotsdir, self.name + '-fig'))
