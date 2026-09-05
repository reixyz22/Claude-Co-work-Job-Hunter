#!/usr/bin/env python3
"""Offline unit tests for skill_clusters. Stdlib unittest, no network, no corpus."""
import unittest
import skill_clusters as sc


class TestPostingKey(unittest.TestCase):
    def test_pipe_heading(self):
        self.assertEqual(
            sc.posting_key("Northwind Logistics | Applied AI Engineer I | R12345 | Chicago, IL"),
            "northwind logistics")

    def test_strips_lead_numbering(self):
        self.assertEqual(
            sc.posting_key("STANDING #1 — Harborline Trading | Junior Developer"),
            "harborline trading")
        self.assertEqual(
            sc.posting_key("3. Meridian Mutual, Software Engineer I (Remote)"),
            "meridian mutual")

    def test_roundup_headings_are_not_postings(self):
        # These name several employers in one block. Counting one as a posting
        # invents co-occurrence that no single JD asked for.
        self.assertIsNone(sc.posting_key("Two leads worth chasing"))
        self.assertIsNone(sc.posting_key("Everything else that died tonight"))
        self.assertIsNone(sc.posting_key("Kills and why"))

    def test_heading_without_separator_rejected(self):
        self.assertIsNone(sc.posting_key("Source ledger"))

    def test_bare_decoration_rejected(self):
        self.assertIsNone(sc.posting_key("LEAD 2 — "))


class TestSkillExtraction(unittest.TestCase):
    def test_language_hits(self):
        s = sc.skills_in("Stack is C#, .NET Core and SQL Server on Azure.")
        self.assertIn("C#", s)
        self.assertIn(".NET / ASP.NET", s)
        self.assertIn("SQL Server", s)
        self.assertIn("Azure", s)

    def test_java_does_not_match_javascript(self):
        s = sc.skills_in("Frontend is JavaScript and React.")
        self.assertNotIn("Java", s)
        self.assertIn("JavaScript", s)

    def test_sql_server_not_double_counted_as_sql(self):
        self.assertNotIn("SQL", sc.skills_in("Experience with SQL Server required."))

    def test_go_needs_a_language_context(self):
        self.assertNotIn("Go", sc.skills_in("Go to the careers page and apply."))
        self.assertIn("Go", sc.skills_in("Backend services in Go, with Postgres."))

    def test_epic_the_company_is_not_healthcare_it(self):
        self.assertNotIn("Healthcare IT", sc.skills_in("Epic Games gameplay internship."))
        self.assertIn("Healthcare IT", sc.skills_in("Epic, HL7 and FHIR interfaces."))


class TestApriori(unittest.TestCase):
    def test_support_counting(self):
        sets = [{"a", "b"}, {"a", "b"}, {"a", "c"}, {"b"}]
        out = sc.apriori(sets, min_count=2)
        self.assertEqual(out[frozenset({"a"})], 3)
        self.assertEqual(out[frozenset({"a", "b"})], 2)
        self.assertNotIn(frozenset({"a", "c"}), out)


if __name__ == "__main__":
    unittest.main()
