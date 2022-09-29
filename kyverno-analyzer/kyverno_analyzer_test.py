import os
import unittest
from kyverno_analyzer import Analyzer


class TestAnalyzer(unittest.TestCase):

    def test_different_occurrences(self):
        path = os.path.dirname(__file__)
        config = path + "/config/config-1.yaml"
        report_path = path + "/report/test-1-policy-report.yaml"
        analyzer = Analyzer(config, report_path)
        assert not analyzer.analyze()

    def test_matches(self):
        path = os.path.dirname(__file__)
        config = path + "/config/config-1.yaml"
        report_path = path + "/report/test-2-policy-report.yaml"
        analyzer = Analyzer(config, report_path)
        assert analyzer.analyze()
