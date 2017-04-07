#!/usr/bin/env python

"""
Tests for statistics (`_statistics` module).
"""

from __future__ import absolute_import, print_function

import time
import unittest

from pywbem import Statistics


def time_abs_delta(t1, t2):
    """
    Return the positive difference between two float values.
    """
    return abs(t1 - t2)


class StatisticsTests(unittest.TestCase):
    """All tests for Statistics and TimeCapture."""

    def test_enabling(self):
        """Test enabling and disabling."""

        statistics = Statistics()

        self.assertFalse(statistics.enabled,
                         "Error: initial state is not disabled")

        statistics.disable()
        self.assertFalse(statistics.enabled,
                         "Error: disabling a disabled statistics works")

        statistics.enable()
        self.assertTrue(statistics.enabled,
                        "Error: enabling a disabled statistics works")

        statistics.enable()
        self.assertTrue(statistics.enabled,
                        "Error: enabling an enabled statistics works")

        statistics.disable()
        self.assertFalse(statistics.enabled,
                         "Errror: disabling an enabled statistics works")

    def test_get(self):
        """Test getting statistics."""

        statistics = Statistics()
        snapshot_length = len(statistics.snapshot())
        self.assertEqual(snapshot_length, 0,
                         "Error:  initial state has no time statistics. "
                         "Actual number = %d" % snapshot_length)

        stats = statistics.get_named_statistic('EnumerateInstances')
        snapshot_length = len(statistics.snapshot())
        self.assertEqual(snapshot_length, 0,
                         "Error: getting a new stats with a disabled "
                         "statistics results in no time statistics. "
                         "Actual number = %d" % snapshot_length)
        self.assertEqual(stats.container, statistics)
        self.assertEqual(stats.name, "disabled")
        self.assertEqual(stats.count, 0)
        self.assertEqual(stats.avg_time, 0)
        self.assertEqual(stats.min_time, float('inf'))
        self.assertEqual(stats.max_time, 0)

        statistics.enable()

        method_name = 'OpenEnumerateInstances'

        stats = statistics.get_named_statistic(method_name)
        snapshot_length = len(statistics.snapshot())
        self.assertEqual(snapshot_length, 1,
                         "Error: getting a new stats with an enabled "
                         "statistics results in one time statistics. "
                         "Actual number = %d" % snapshot_length)

        self.assertEqual(stats.container, statistics)
        self.assertEqual(stats.name, method_name)
        self.assertEqual(stats.count, 0)
        self.assertEqual(stats.avg_time, 0)
        self.assertEqual(stats.min_time, float('inf'))
        self.assertEqual(stats.max_time, 0)

        statistics.get_named_statistic(method_name)
        snapshot_length = len(statistics.snapshot())
        self.assertEqual(snapshot_length, 1,
                         "Error: getting an existing stats with an "
                         "enabled statistics results in the same number of "
                         "statistics. "
                         "Actual number = %d" % snapshot_length)

    def test_measure_enabled(self):
        """Test measuring time with enabled statistics."""

        statistics = Statistics()
        statistics.enable()

        duration = 0.4
        # On Windows has only a precision of 1/60 sec:
        delta = 0.04

        stats = statistics.start_timer('EnumerateInstances')
        time.sleep(duration)
        stats.stop_timer()

        for _, stats in statistics.snapshot():
            self.assertEqual(stats.count, 1)
            self.assertTrue(time_abs_delta(stats.avg_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.min_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.max_time, duration) < delta)

        stats.reset()
        self.assertEqual(stats.count, 0)
        self.assertEqual(stats.avg_time, 0)
        self.assertEqual(stats.min_time, float('inf'))
        self.assertEqual(stats.max_time, 0)

    def test_measure_disabled(self):
        """Test measuring time with disabled statistics."""

        statistics = Statistics()

        duration = 0.2

        stats = statistics.get_named_statistic('GetClass')
        self.assertEqual(stats.name, 'disabled')

        stats.start_timer()
        time.sleep(duration)
        stats.stop_timer()

        for _, stats in statistics.snapshot():
            self.assertEqual(stats.count, 0)
            self.assertEqual(stats.avg_time, 0)
            self.assertEqual(stats.min_time, float('inf'))
            self.assertEqual(stats.max_time, 0)

    def test_snapshot(self):
        """Test that snapshot() takes a stable snapshot."""

        statistics = Statistics()
        statistics.enable()

        duration = 0.4
        # On Windows has only a precision of 1/60 sec:
        delta = 0.04

        stats = statistics.start_timer('GetInstance')
        time.sleep(duration)
        stats.stop_timer()

        # take the snapshot
        snapshot = statistics.snapshot()

        # keep producing statistics data
        stats.start_timer()
        time.sleep(duration)
        stats.stop_timer()

        # verify that only the first set of data is in the snapshot
        for _, stats in snapshot:
            self.assertEqual(stats.count, 1)
            self.assertTrue(time_abs_delta(stats.avg_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.min_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.max_time, duration) < delta)


if __name__ == '__main__':
    unittest.main()
