# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from django_migrate_sql.autodetector import is_sql_equal


class SQLComparisonTestCase(TestCase):
    """
    Tests comparison algorithm for two SQL item contents.
    """
    def test_flat(self):
        self.assertTrue(is_sql_equal('SELECT 1', 'SELECT 1'))
        self.assertFalse(is_sql_equal('SELECT 1', 'SELECT 2'))

    def test_nested(self):
        self.assertTrue(is_sql_equal(['SELECT 1', 'SELECT 2'], ['SELECT 1', 'SELECT 2']))
        self.assertFalse(is_sql_equal(['SELECT 1', 'SELECT 2'], ['SELECT 1', 'SELECT 3']))

    def test_nested_with_params(self):
        self.assertTrue(is_sql_equal([('SELECT %s', [1]), ('SELECT %s', [2])],
                                     [('SELECT %s', [1]), ('SELECT %s', [2])]))
        self.assertFalse(is_sql_equal([('SELECT %s', [1]), ('SELECT %s', [2])],
                                      [('SELECT %s', [1]), ('SELECT %s', [3])]))

    def test_mixed_with_params(self):
        self.assertFalse(is_sql_equal([('SELECT %s', [1]), ('SELECT %s', [2])],
                                      ['SELECT 1', ('SELECT %s', [2])]))
        self.assertFalse(is_sql_equal(['SELECT 1', ('SELECT %s', [2])],
                                      ['SELECT 1', ('SELECT %s', [3])]))

    def test_mixed_nesting(self):
        self.assertTrue(is_sql_equal('SELECT 1', ['SELECT 1']))
        self.assertFalse(is_sql_equal('SELECT 1', [('SELECT %s', [1])]))
