# pylint: disable=unidiomatic-typecheck

from unittest import TestCase
from time import time

from pymongo import MongoClient

from mongotime.sampler import take_sample


class TestSampling(TestCase):
    def setUp(self):
        self.db = MongoClient()

    def test_return_format(self):
        sample = take_sample(self.db, None)

        assert sample
        assert type(sample) == dict
        assert set(sample.keys()) == {'t', 'o'}
        assert type(sample['t']) == float
        assert type(sample['o']) == list

    def test_time(self):
        t_before = time()
        t_sample = take_sample(self.db, None)['t']
        t_after = time()

        assert t_sample >= t_before
        assert t_sample <= t_after

    def test_ops(self):
        # taking a sample with given client_id will include our own op, so
        # it's a way of guaranteeing an op to check
        op = take_sample(self.db, None)['o'][0]

        assert op
        assert type(op) == dict
