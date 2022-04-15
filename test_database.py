import time
import unittest
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from jinja2 import Environment

from database import Database

TESTING_PORT_MIN = 8001
TESTING_PORT_MAX = 8030
TESTING_HOST = 'localhost'
TESTING_FOLDER = './test_data'
EXAMPLE_URL = "http://example.com"
with open("test_data/example_1.html", "r") as f:
    EXAMPLE_HTML = f.read()

env = Environment()


class TestDatabase(unittest.TestCase):
    """
    Test the database class where max_depth is set to 1
    """
    t: 'TestServer'
    
    @classmethod
    def setUpClass(cls):
        t = TestServer()
        t.start()
        cls.t = t
        
    @classmethod
    def tearDownClass(cls):
        cls.t.stop()
        
    def setUp(self):
        self.db = Database(max_depth=1, max_workers=10)
        self.db.store_html(url=EXAMPLE_URL, html=EXAMPLE_HTML)

    def test_has_url(self):
        self.assertTrue(self.db.has_url(url=EXAMPLE_URL))
        self.assertFalse(self.db.has_url(url="https://bad.com"))

    def test_count(self):
        self.assertEqual(1, self.db.count(url=EXAMPLE_URL, term="an"))

    def test_count_case_insensitive(self):
        self.assertEqual(2, self.db.count(url=EXAMPLE_URL, term="example"))

    def test_count_ignore_partial_matches(self):
        self.assertEqual(0, self.db.count(url=EXAMPLE_URL, term="exam"))

    def test_count_ignore_tags(self):
        self.assertEqual(0, self.db.count(url=EXAMPLE_URL, term="p"))

    def test_count_exclude_periods(self):
        self.assertEqual(1, self.db.count(url=EXAMPLE_URL, term="page"))
        self.assertEqual(1, self.db.count(url=EXAMPLE_URL, term="page."))

    def test_count_include_hyphens(self):
        self.assertEqual(1, self.db.count(url=EXAMPLE_URL, term="sign-in"))

    def test_count_ignore_head(self):
        self.assertEqual(0, self.db.count(url=EXAMPLE_URL, term="test"))

    def test_store_url(self):
        url = self.t.file_url("example_2_server.html")
        self.db.store_url(url=url)
        self.assertTrue(self.db.has_url(url=url))
        self.assertEqual(1, self.db.count(url=url, term="webserver"))

    def test_store_relative_url_with_depth_level_1(self):
        url = self.t.file_url("example_3_parent.html")
        neighbor = self.t.file_url("example_3_child.html")
        self.db.store_url(url=url)
        self.assertTrue(self.db.has_url(url=url))
        self.assertTrue(self.db.has_url(url=neighbor))
        self.assertEqual(1, self.db.count(url=url, term="parent"))
        self.assertEqual(1, self.db.count(url=url, term="child"))
        self.assertEqual(2, self.db.count(url=url, term="the"))

    def test_store_absolute_url_with_depth_level_1(self):
        with open(f"{TESTING_FOLDER}/example_3_parent_absolute_template.html", "r") as f:
            html = env.from_string(f.read()).render(TESTING_HOST=self.t.host, TESTING_PORT=self.t.port)
        with open(f"{TESTING_FOLDER}/example_3_parent_absolute.html", "w+") as f:
            f.write(html)
        url = self.t.file_url("example_3_parent_absolute.html")
        neighbor = self.t.file_url("example_3_child.html")
        self.db.store_url(url=url)

        self.assertTrue(self.db.has_url(url=url))
        self.assertTrue(self.db.has_url(url=neighbor))
        self.assertEqual(1, self.db.count(url=url, term="parent"))
        self.assertEqual(1, self.db.count(url=url, term="child"))
        self.assertEqual(2, self.db.count(url=url, term="the"))

    def test_store_url_with_self_reference(self):
        url = self.t.file_url("example_4_recursive.html")
        self.db.store_url(url=url)
        self.assertTrue(self.db.has_url(url=url))
        self.assertEqual(1, self.db.count(url=url, term="recursive"))

    def test_store_url_with_many_references(self):
        t1 = time.time()
        url = self.t.file_url("example_5_parent.html")
        self.db.store_url(url=url)
        self.assertTrue(self.db.has_url(url=url))
        self.assertEqual(1, self.db.count(url=url, term="parent"))
        self.assertEqual(50, self.db.count(url=url, term="child"))
        t2 = time.time()
        self.assertLess(t2 - t1, 20)

    def test_store_with_depth_level_2(self):
        url = self.t.file_url("example_6_grandparent.html")
        self.db.store_url(url=url)
        self.assertTrue(self.db.has_url(url=url))
        self.assertEqual(1, self.db.count(url=url, term="grandparent"))
        self.assertEqual(1, self.db.count(url=url, term="parent"))
        self.assertEqual(0, self.db.count(url=url, term="child"))

    def test_store_with_anchor(self):
        url = self.t.file_url("example_7_anchor.html")
        self.db.store_url(url=url)
        self.assertTrue(self.db.has_url(url=url))
        self.assertEqual(1, self.db.count(url=url, term="anchor"))

    def test_store_with_404(self):
        url = self.t.file_url("fake_example.html")
        self.db.store_url(url=url)
        self.assertFalse(self.db.has_url(url=url))

    def test_store_with_connection_error(self):
        url = "https://localhost:9999/fake_example.html"
        self.db.store_url(url=url)
        self.assertFalse(self.db.has_url(url=url))


class TestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=TESTING_FOLDER, **kwargs)


class TestServer(threading.Thread):
    def run(self, host=TESTING_HOST, port=TESTING_PORT_MIN):
        self.host = host
        self.port = port
        while True:
            try:
                self.server = ThreadingHTTPServer((self.host, self.port), TestHandler)
                break
            except OSError:
                self.port += 1
                if self.port > TESTING_PORT_MAX:
                    raise
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def file_url(self, filename):
        return "http://{}:{}/{}".format(self.host, self.port, filename)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


if __name__ == '__main__':
    unittest.main()
