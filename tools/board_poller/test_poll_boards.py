#!/usr/bin/env python3
"""Offline unit tests for poll_boards. Stdlib unittest, no network."""
import unittest
import poll_boards as pb


class TestClassify(unittest.TestCase):
    def j(self, t):  # expect junior
        self.assertEqual(pb.classify(t), "junior", t)

    def w(self, t):  # expect watch
        self.assertEqual(pb.classify(t), "watch", t)

    def d(self, t):  # expect dropped
        self.assertIsNone(pb.classify(t), t)

    def test_junior_signals(self):
        self.j("Junior Software Engineer")
        self.j("Software Engineer I")
        self.j("Associate Developer")
        self.j("New Grad Software Engineer, Full-Stack")
        self.j("Entry-Level Data Analyst")
        self.j("Graduate Software Developer")
        self.j("Software Engineering Apprentice")
        self.j("Junior IT Analyst")            # IT/analyst adjacent + junior marker
        self.j("Associate Data Analyst")       # data/analyst adjacent + associate

    def test_business_ops_noise_dropped(self):
        # Tightened 2026-08-19: bare business/ops/compliance/specialist titles are no
        # longer tech-adjacent. They generated noise ("Sanitation Specialist", etc.)
        # are not the targeted families (IT/Analyst/QA/SWE/Solutions).
        self.d("Business Compliance Associate")
        self.d("Operations Associate")
        self.d("Sanitation Specialist")
        self.d("Content Specialist")
        self.d("Fraud Specialist 1")
        self.d("Revenue Operations Coordinator")

    def test_yoe_extraction(self):
        self.assertEqual(pb.extract_yoe("5+ years of experience building X"), 5)
        self.assertEqual(pb.extract_yoe("0-2 years of relevant experience"), 0)
        self.assertEqual(pb.extract_yoe("Minimum of 3 years experience"), 3)
        self.assertEqual(pb.extract_yoe("1-3 years professional experience"), 1)
        # min across mentions wins (recall-safe)
        self.assertEqual(pb.extract_yoe("2 years experience; 8 years leadership experience"), 2)
        # no YoE, or 'years' not tied to 'experience' -> None (no false gate)
        self.assertIsNone(pb.extract_yoe("Bachelor degree with zero experience"))
        self.assertIsNone(pb.extract_yoe("3 years of college coursework"))
        self.assertIsNone(pb.extract_yoe(""))

    def test_watch_plain_titles(self):
        self.w("Software Engineer")
        self.w("Full Stack Developer")
        self.w("Data Analyst")
        self.w("Backend Engineer")
        self.w("QA Engineer")

    def test_seniority_drops(self):
        self.d("Senior Software Engineer")
        self.d("Staff Engineer")
        self.d("Principal Software Engineer - Platform")
        self.d("Engineering Manager")
        self.d("Software Engineer II")
        self.d("Software Engineer III")
        self.d("Lead Product Manager")
        self.d("Site Reliability Engineer Team Lead")
        self.d("Director of Engineering")
        self.d("Head of Data")

    def test_negative_beats_positive(self):
        # "Senior Associate" contains the junior word "associate" but must drop
        self.d("Senior Associate Engineer")
        self.d("Senior Associate - Paid Media")

    def test_non_eng_titles_drop(self):
        self.d("Collections Team Lead")
        self.d("Account Executive")
        self.d("Sales Development Representative")
        self.d("Assistant General Counsel, Litigation")

    def test_ii_word_boundary_does_not_match_hawaii(self):
        # the \bii\b seniority rule must NOT fire on "Hawaii"
        self.w("Software Engineer - Hawaii")
        self.j("Junior Developer, Hawaii")

    def test_empty(self):
        self.d("")
        self.d(None)


class TestParseUrl(unittest.TestCase):
    def test_greenhouse(self):
        for u in ("https://job-boards.greenhouse.io/enova",
                  "https://boards.greenhouse.io/enova",
                  "https://boards-api.greenhouse.io/v1/boards/enova/jobs"):
            info = pb.parse_url(u)
            self.assertEqual(info["ats"], "greenhouse")
            self.assertEqual(info["token"], "enova")

    def test_lever(self):
        info = pb.parse_url("https://jobs.lever.co/activecampaign")
        self.assertEqual(info["ats"], "lever")
        self.assertEqual(info["company"], "activecampaign")

    def test_ashby(self):
        info = pb.parse_url("https://jobs.ashbyhq.com/renterra/430dc36f/application")
        self.assertEqual(info["ats"], "ashby")
        self.assertEqual(info["org"], "renterra")

    def test_workday(self):
        info = pb.parse_url("https://acme.wd1.myworkdayjobs.com/External?jobFamilyGroup=abc")
        self.assertEqual(info["ats"], "workday")
        self.assertEqual(info["host"], "acme.wd1.myworkdayjobs.com")
        self.assertEqual(info["tenant"], "acme")
        self.assertEqual(info["board"], "External")

    def test_unsupported_flagged_skip(self):
        info = pb.parse_url("https://careers-acme.icims.com/jobs/intro")
        self.assertEqual(info["ats"], "icims")
        self.assertTrue(info["skip"])

    def test_unrecognized_returns_none(self):
        self.assertIsNone(pb.parse_url("https://example.com/careers"))

    def test_rippling(self):
        # Added 2026-09-12. Rippling was an unrecognized vendor until Nerdio surfaced it;
        # Loop and Supernova are on the same ATS, so this was a three-employer blind spot.
        for u in ("https://ats.rippling.com/nerdio-careers/jobs",
                  "https://ats.rippling.com/nerdio-careers/jobs/0b82e6f3-fd54-40d7",
                  "https://api.rippling.com/platform/api/ats/v1/board/nerdio-careers/jobs"):
            info = pb.parse_url(u)
            self.assertEqual(info["ats"], "rippling", u)
            self.assertEqual(info["tenant"], "nerdio-careers", u)


class TestRipplingShape(unittest.TestCase):
    """Offline: feed fetch_rippling the real 2026-09-12 response shape via a stubbed _get."""

    SAMPLE = [
        {"uuid": "8dbd3afd-a657", "name": "Application Security Architect",
         "department": {"id": "Impl", "label": "Impl"},
         "url": "https://ats.rippling.com/nerdio-careers/jobs/8dbd3afd-a657",
         "workLocation": {"label": "Remote (United States)", "id": "Remote (United States)"}},
        {"uuid": "0b82e6f3-fd54", "name": "Solutions Engineer (Early Career)",
         "department": {"id": "Corp", "label": "Corp"},
         "url": "https://ats.rippling.com/nerdio-careers/jobs/0b82e6f3-fd54",
         "workLocation": {"label": "Remote (United States)", "id": "Remote (United States)"}},
        {"uuid": "", "name": "Malformed row with no uuid", "workLocation": None},
    ]

    def setUp(self):
        self._real = pb._get
        pb._get = lambda url, data=None, headers=None: self.SAMPLE

    def tearDown(self):
        pb._get = self._real

    def test_maps_fields_and_skips_uuidless_rows(self):
        out = pb.fetch_rippling({"ats": "rippling", "tenant": "nerdio-careers"})
        self.assertEqual(len(out), 2)          # the uuid-less row is dropped
        self.assertEqual(out[1]["title"], "Solutions Engineer (Early Career)")
        self.assertEqual(out[1]["location"], "Remote (United States)")
        self.assertTrue(out[1]["url"].endswith("0b82e6f3-fd54"))

    def test_posted_is_always_blank(self):
        # Rippling ships no posting date. Asserted so a future change that starts
        # inventing one has to break a test first -- a fabricated age would promote
        # dead reqs straight to the top under the freshness-first ranking rule.
        for row in pb.fetch_rippling({"ats": "rippling", "tenant": "nerdio-careers"}):
            self.assertEqual(row["posted"], "")

    def test_classify_finds_the_junior_req(self):
        out = pb.fetch_rippling({"ats": "rippling", "tenant": "nerdio-careers"})
        titles = [r["title"] for r in out if pb.classify(r["title"])]
        self.assertIn("Solutions Engineer (Early Career)", titles)


class TestLocation(unittest.TestCase):
    def ok(self, l):
        self.assertTrue(pb.location_ok(l), l)

    def no(self, l):
        self.assertFalse(pb.location_ok(l), l)

    def test_local_and_remote_pass(self):
        for l in ("Chicago, IL", "Lake Forest, IL", "Illinois", "Chicago",
                  "Remote", "Remote - US", "Chicago / Remote", "Chicago, IL; New York, NY"):
            self.ok(l)

    def test_blank_kept(self):
        self.ok("")
        self.ok(None)

    def test_foreign_and_far_us_drop(self):
        for l in ("Bangalore", "Krakow, Poland", "S\u00e3o Paulo, Brazil",
                  "London, UK", "Toronto, Canada", "Denver, CO", "New York, NY",
                  "San Francisco, CA"):
            self.no(l)


if __name__ == "__main__":
    unittest.main(verbosity=2)

