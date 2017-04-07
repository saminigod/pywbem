#!/usr/bin/env python
#
# (C) Copyright 2003-2007 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006-2007 Novell, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

"""
The :class:`~pywbem.Statistics` class allows measuring the elapsed
time of instrumented coded and keeping statistics on the measured times

It consists of two classes:

The :class:`~pywbem.TimeStatistic` class is a helper class that contains the
actual measurement data for all invocations of a particular name. Its
objects are under control of the :class:`~pywbem.Statistics` class.
This class should be used indepently.  user the start_timer in the
Statistics class to both start a timer and if it does not exist, create
a new named statistic  category.

The :class:`~pywbem.Statistics` class maintins time statistics over
multiple separate named statistics gatherers (TimeStatistic class) and provides
tools for reporting these statistics


"""

from __future__ import absolute_import

import time
import copy

__all__ = ['Statistics']


class NamedStatistic(object):
    """
    Elapsed time information for all invocations of a particular named
    operation.

    This class maintains max, min, avg and count for a single named
    statistics

    Use :meth:`pywbem.Statistics.get_statistic` method  to
    create objects of this class.

    Ex:

        stats = container.start_timer('EnumerateInstances')
        ...
        stats.stop_timer()
    """
    display_col_hdr = "Count   Avg     Min     Max     Exc Name\n"

    def __init__(self, container, name):
        """
        Parameters:

          container (Statistics):
            The statistics container that holds this time statistics.

          name (string):
            Name of the operation.
        """
        self._container = container
        self._stat_start_time = None
        self._name = name
        self._count = 0
        self._exception_count = 0
        self._time_sum = float(0)
        self._time_min = float('inf')
        self._time_max = float(0)
        self._start_time = None

    @property
    def stat_start_time(self):
        """
        :py:time: Time the first statistic was taken since this object
        was either created or reset.
        """
        return self._stat_start_time

    @property
    def name(self):
        """
        :term:`string`: Name for a sequence of time statistics that represents
        a single entitiy (ex. pywbem operation name)

        This name is used by the :class:`~pywbem.Statistics` object
        holding this time statistics as a key.
        """
        return self._name

    @property
    def container(self):
        """
        :class:`~pywbem.Statistics`: This time statistics container.
        """
        return self._container

    @property
    def count(self):
        """
        :term:`integer`: The number of invocations of the start_timer() and
        stop_timer()).
        """
        return self._count

    @property
    def avg_time(self):
        """
        float: The average elapsed time for invoking the operation, in seconds.
        """
        try:
            return self._time_sum / self._count
        except ZeroDivisionError:
            return 0

    @property
    def min_time(self):
        """
        float: The minimum elapsed time for invoking the operation, in seconds.
        """
        return self._time_min

    @property
    def max_time(self):
        """
        float: The maximum elapsed time for invoking the operation, in seconds.
        """
        return self._time_max

    @property
    def exception_count(self):
        """
            :py:time: Count of exceptions that occurred for named operation
        """
        return self._exception_count

    def reset(self):
        """
        Reset the statistics data.
        """
        self._count = 0
        self._exception_count = 0
        self._stat_start_time = None
        self._time_sum = float(0)
        self._time_min = float('inf')
        self._time_max = float(0)

    def start_timer(self):
        """
        This method starts the timer for this NamedStatistic object if
        the container is enabled.

        A subsequent :meth:`~pywbem.NamedStatistic.stop_timer` computes the
        statistics for the time duration between the start and stop for this
        :meth:`~pywbem.NamedStatistic.

        If the statistics container holding this time statistics is disabled,
        this method does nothing.
        """
        if self.container.enabled:
            self._start_time = time.time()
            if not self._stat_start_time:
                self._stat_start_time = self._start_time

    def stop_timer(self, exception=None):
        """
        This method is called at the completion of the timed event. It
        captures current time, computes the event duration since the
        corresponding :meth:`~pywbem.NamedStatistic.start_timer` and computes
        average, max, and min for the timedduration if the container is enabled.

        If the statistics container is disabled, this method does nothing.

        Returns the time for this operation on None if not recorded
        """
        if self.container.enabled:
            if self._start_time is None:
                raise RuntimeError('stop_timer() called without preceding '
                                   ' start_timer()')
            dt = time.time() - self._start_time
            self._start_time = None
            self._count += 1
            self._time_sum += dt
            if dt > self._time_max:
                self._time_max = dt
            if dt < self._time_min:
                self._time_min = dt
            if exception:
                self._exception_count += 1
            return dt
        else:
            return None

    def __str__(self):
        """
        Return a human readable string with the time statistics for this
        name.
        """
        return 'NamedStatistic: {} count={:d} AvgTime={:.3f}s MinTime={:.3f}s '\
               'MaxTime={:.3f}s exceptions={:d}'.format(self.name, self.count,
                                                        self.avg_time,
                                                        self.min_time,
                                                        self.max_time,
                                                        self.exception_count)

    def formatted(self):
        """
        Returns a formatted NamedStatistic consistent with the display header.
        """
        return ("{:5d} {:7.3f} {:7.3f} {:7.3f} {:5d} {}\n".
                format(self.count, self.avg_time, self.min_time, self.max_time,
                       self.exception_count, self.name))


class Statistics(object):
    """
    Statistics is a container for multiple statistics capture objects each
    defined by the :class:`~pywbem.NamedStatistic`).

    Each capture object is identified by a name defined in the start_timer
    method.

    The statistics container can be in a state of enabled or disabled.
    If enabled, it accumulates the elapsed times between subsequent calls to the
    :meth:`~pywbem.NamedStatistic.start_timer` and
     :meth:`~pywbem.NamedStatistic.stop_timer`
    methods of class :class:`~pywbem.NamedStatistic`.
    If disabled, calls to these methods do not accumulate any time.

    Initially, the statistics container is disabled.
    """

    def __init__(self, enabled=False):
        self._enabled = enabled
        self._time_stats = {}
        self._disabled_stats = NamedStatistic(self, "disabled")

    @property
    def enabled(self):
        """
        Indicates whether the statistics container is enabled.
        """
        return self._enabled

    def enable(self):
        """
        Enable the statistics container.
        """
        self._enabled = True

    def disable(self):
        """
        Disable the statistics container.
        """
        self._enabled = False

    def start_timer(self, name):
        """
        Start the timer for a defined timer name. If that  timer name does not
        exist, it is created in Statistics.

        Parameters:

          name (string):
            Name of the timer.

        Returns:

          NamedStatistic: The time statistics for the specified name. If the
          statistics container is disabled, a dummy time statistics object is
          returned.
        """
        named_statistic = self.get_named_statistic(name)
        named_statistic.start_timer()
        return named_statistic

    def get_named_statistic(self, name):
        """
        Get the NamedStatistic instance for a name or create a new
        NamedStatistic instance if that name does not exist

        Parameters:

          name (string):
            Name of the timer.

        Returns:

          NamedStatistic: The time statistics for the specified name. If the
          statistics container is disabled, a dummy time statistics object is
          returned.
        """
        if not self.enabled:
            return self._disabled_stats
        if name not in self._time_stats:
            self._time_stats[name] = NamedStatistic(self, name)
        return self._time_stats[name]

    def snapshot(self):
        """
        Return a snapshot of the time statistics of this container.

        The snapshot represents the statistics data at the time this method
        is called, and remains unchanged even if the statistics of this
        container continues to be updated.

        Returns:

          : A list of tuples (name, stats) with:

          - name (:term:`string`): Name of the operation
          - stats (:class:`~pywbem.NamedStatistic`): Time statistics for the
            operation
        """
        return copy.deepcopy(self._time_stats).items()

    def __str__(self):
        """ Return a human readable display of the contents"""
        for stat in self._time_stats:
            print(stat)

    def display(self):
        """
        Return a display formatted string with the time statistics for this
        container. The operations are sorted by decreasing average time.
        """
        ret = "Statistics (time in sec.):\n"
        if self.enabled:
            ret += NamedStatistic.display_col_hdr
            snapshot = sorted(self.snapshot(),
                              key=lambda item: item[1].avg_time,
                              reverse=True)
            for name in snapshot:
                ret += snapshot[name].formatted()
        else:
            ret += "Disabled"
        return ret.strip()
