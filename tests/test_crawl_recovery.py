from types import SimpleNamespace
import unittest

from lead_engine import BrowserUnavailable, RecoveringCrawler, WebsiteUnavailable

FIRST = "https://first.example/"
SECOND = "https://second.example/"
CLOSED = "BrowserContext.new_page: Target page, context or browser has been closed"


class Browser:
    def __init__(self, failures):
        self.failures = failures
        self.visits = []
        self.closed = False

    async def start(self):
        return self

    async def close(self):
        self.closed = True

    async def arun(self, target, config):
        self.visits.append(target)
        error = self.failures.get(target)
        return SimpleNamespace(success=not error, url=target, error_message=error,
                               html="<main>Business website</main>")


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_crash_retries_then_reuses_replacement(self):
        first = Browser({FIRST: CLOSED})
        replacement = Browser({})
        modes = []

        def factory(shell):
            modes.append(shell)
            return replacement if shell else first

        async with RecoveringCrawler(factory) as crawler:
            self.assertIn(FIRST, (await crawler.crawl(FIRST))[0])
            self.assertIn(SECOND, (await crawler.crawl(SECOND))[0])
            self.assertEqual(crawler.restarts, 1)
        self.assertEqual(modes, [False, True])
        self.assertEqual(replacement.visits, [FIRST, SECOND])
        self.assertTrue(first.closed and replacement.closed)

    async def test_repeated_crash_does_not_poison_next_business(self):
        browsers = iter([Browser({FIRST: CLOSED}), Browser({FIRST: CLOSED}), Browser({})])
        async with RecoveringCrawler(lambda shell: next(browsers)) as crawler:
            with self.assertRaises(BrowserUnavailable):
                await crawler.crawl(FIRST)
            self.assertIn(SECOND, (await crawler.crawl(SECOND))[0])

    async def test_website_timeout_does_not_restart_browser(self):
        browser = Browser({FIRST: "Page.goto: Timeout 25000ms exceeded"})
        async with RecoveringCrawler(lambda shell: browser) as crawler:
            with self.assertRaisesRegex(WebsiteUnavailable, "timeout"):
                await crawler.crawl(FIRST)
            self.assertIn(SECOND, (await crawler.crawl(SECOND))[0])
            self.assertEqual(crawler.restarts, 0)

    async def test_optional_page_crash_keeps_homepage_and_reopens_browser(self):
        contact = FIRST + "contact"

        class BrowserWithContact(Browser):
            async def arun(self, target, config):
                result = await super().arun(target, config)
                if target == FIRST:
                    result.html = '<main>Business website<a href="/contact">Contact</a></main>'
                return result

        first = BrowserWithContact({contact: CLOSED})
        replacement = Browser({})
        browsers = iter((first, replacement))
        async with RecoveringCrawler(lambda shell: next(browsers)) as crawler:
            self.assertIn(FIRST, (await crawler.crawl(FIRST, coohom=True))[0])
            self.assertTrue(first.closed)
            self.assertIn(SECOND, (await crawler.crawl(SECOND))[0])
        self.assertEqual(first.visits, [FIRST, contact])
        self.assertEqual(replacement.visits, [SECOND])

    async def test_dns_has_specific_message_and_does_not_restart_browser(self):
        browser = Browser({FIRST: "Page.goto: net::ERR_NAME_NOT_RESOLVED"})
        async with RecoveringCrawler(lambda shell: browser) as crawler:
            with self.assertRaisesRegex(WebsiteUnavailable, "DNS"):
                await crawler.crawl(FIRST)
            self.assertEqual(crawler.restarts, 0)
