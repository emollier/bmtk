# Copyright 2017. Allen Institute. All rights reserved
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
# disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote
# products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
from neuron import h
import numpy as np
import pandas as pd

from bmtk.simulator.bionet.io_tools import io
from bmtk.simulator.bionet.pyfunction_cache import py_modules
from bmtk.utils.reports.spike_trains.spike_trains import SpikeTrains


class VirtualCell(object):
    """Representation of a Virtual/External node"""

    def __init__(self, node, population, spike_train_dataset, spikes_generator=None, sim=None):
        # VirtualCell is currently not a subclass of bionet.Cell class b/c the parent has a bunch of properties that
        # just don't apply to a virtual cell. May want to make bionet.Cell more generic in the future.
        self._node_id = node.node_id
        self._node = node
        self._population = population
        self._hobj = None
        self._spike_train_dataset = spike_train_dataset
        self._train_vec = []
        self._sim = sim
        
        if spike_train_dataset is not None:
            self.set_stim(node, self._spike_train_dataset)
        elif spikes_generator is not None:
            self.set_stim_from_generator(node, spikes_generator)
        else:
            io.log_exception('Could not find source of spikes-trains (eg file or generator function)'
                            f' for virtual cell #{self._node_id} from {self._population}')
        
    @property
    def node_id(self):
        return self._node_id

    @property
    def hobj(self):
        return self._hobj

    def set_stim(self, stim_prop, spike_train):
        """Gets the spike trains for each individual cell."""
        if isinstance(spike_train, SpikeTrains) or hasattr(spike_train, 'get_times'):
            spikes = spike_train.get_times(node_id=self.node_id)
        elif isinstance(spike_train, (list, np.ndarray, pd.Series)):
            spikes = spike_train
        elif spike_train is None:
            spikes = []
        else:
            spikes = None

        if spikes is None:
            spikes = []

        if np.any(np.array(spikes) < 0.0):
            # NRN will fail if VecStim contains negative spike-time, throw an exception and log info for user
            io.log_exception('spike train {} contains negative number, unable to run virtual cell in NEURON'.format(
                spikes
            ))

        spikes = np.sort(spikes)  # sort the spikes for NEURON, will throw a segfault if not sorted

        self._train_vec = h.Vector(spikes)
        vecstim = h.VecStim()
        vecstim.play(self._train_vec)
        self._hobj = vecstim

    def set_stim_from_generator(self, node, spikes_generator):
        if spikes_generator not in py_modules.spikes_generators:
            io.log_exception(f'Could not find @spikes_generator function "{spikes_generator}". Unable to load spikes for virtual cell {self._node_id}')
        spikes_func = py_modules.spikes_generator(name=spikes_generator)
        spikes = spikes_func(self._node, self._sim)
        
        self._train_vec = h.Vector(spikes)
        vecstim = h.VecStim()
        vecstim.play(self._train_vec)
        self._hobj = vecstim

    def __getitem__(self, item):
        return self._node[item]
