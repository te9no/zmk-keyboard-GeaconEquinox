"""Workflow contract tests; requires PyYAML in the test environment."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.load(
            (ROOT / '.github/workflows/build.yml').read_text(),
            Loader=yaml.BaseLoader,
        )

    def test_daily_checks_do_not_publish_commits(self):
        self.assertEqual(self.workflow['on']['schedule'], [{'cron': '0 20 * * *'}])
        inputs = self.workflow['jobs']['build']['with']
        self.assertEqual(inputs['commit_firmware'],
                         "${{ github.event_name == 'push' || inputs.commit_firmware == true }}")
        self.assertEqual(inputs['target'], "${{ inputs.target || 'all' }}")

    def test_no_firmware_commit_loop(self):
        paths = self.workflow['on']['push']['paths']
        self.assertNotIn('firmware/**', paths)
        self.assertIn('config/**', paths)
        self.assertIn('snippets/**', paths)

    def test_shared_builder_and_daily_notification(self):
        jobs = self.workflow['jobs']
        self.assertEqual(jobs['build']['uses'],
                         'te9no/zmk-workspace/.github/workflows/build-zmk-firmware.yml@main')
        self.assertIn("github.event_name == 'schedule'", jobs['notify-daily-build-failure']['if'])
        self.assertIn("needs.build.result == 'failure'", jobs['notify-daily-build-failure']['if'])


if __name__ == '__main__':
    unittest.main()
