#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Test that the CLI works as expected
"""

import sys
import unittest

from uuid import uuid4

from six import StringIO

from gabbi import driver
from gabbi.fixture import InterceptFixture
from gabbi import handlers
from gabbi import runner
from gabbi.simple_wsgi import SimpleWsgi


class RunnerTest(unittest.TestCase):

    def setUp(self):
        super(RunnerTest, self).setUp()

        host, port = (str(uuid4()), 8000)
        self.server = lambda: InterceptFixture(host, port, SimpleWsgi, '')

        self._stdin = sys.stdin

        self._stdout = sys.stdout
        sys.stdout = StringIO()  # swallow output to avoid confusion

        self._stderr = sys.stderr
        sys.stderr = StringIO()  # swallow output to avoid confusion

        self._argv = sys.argv
        sys.argv = ['gabbi-run', '%s:%s' % (host, port)]

    def tearDown(self):
        sys.stdin = self._stdin
        sys.stdout = self._stdout
        sys.stderr = self._stderr
        sys.argv = self._argv

    def test_custom_response_handler(self):
        sys.stdin = StringIO("""
        tests:
        - name: unknown response handler
          GET: /
          response_html: ...
        """)
        with self.assertRaises(driver.GabbiFormatError):
            runner.run()

        sys.argv.insert(1, "--response-handler")
        sys.argv.insert(2, "gabbi.tests.test_runner:HTMLResponseHandler")

        sys.stdin = StringIO("""
        tests:
        - name: custom response handler
          GET: /presenter
          response_html:
              h1: Hello World
              p: lorem ipsum dolor sit amet
        """)
        with self.server():
            try:
                runner.run()
            except SystemExit as err:
                self.assertSuccess(err)

        sys.stdin = StringIO("""
        tests:
        - name: custom response handler failure
          GET: /presenter
          response_html:
              h1: lipsum
        """)
        with self.server():
            try:
                runner.run()
            except SystemExit as err:
                self.assertFailure(err)

    def test_exit_code(self):
        sys.stdin = StringIO()
        with self.assertRaises(driver.GabbiFormatError):
            runner.run()

        sys.stdin = StringIO("""
        tests:
        - name: expected failure
          GET: /
          status: 666
        """)
        try:
            runner.run()
        except SystemExit as err:
            self.assertFailure(err)

        sys.stdin = StringIO("""
        tests:
        - name: expected success
          GET: /
          status: 200
        """)
        with self.server():
            try:
                runner.run()
            except SystemExit as err:
                self.assertSuccess(err)

    def assertSuccess(self, exitError):
        errors = exitError.args[0]
        self.assertEqual(errors, False)

    def assertFailure(self, exitError):
        errors = exitError.args[0]
        self.assertEqual(errors, True)


class HTMLResponseHandler(handlers.ResponseHandler):

    test_key_suffix = 'html'
    test_key_value = {}

    def action(self, test, item, value):
        doc = test.output
        html = '<{tag}>{content}</{tag}>'.format(tag=item, content=value)
        test.assertTrue(html in doc, "no elements matching '%s'" % html)
