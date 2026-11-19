import json,tempfile,unittest
from pathlib import Path
from citation_metadata_reconciler.cli import parse,validate,rank_candidates,apply_mappings,main
class CitationTests(unittest.TestCase):
    def test_validation_doi_and_required_fields(self):
        self.assertEqual(validate({"title":"Work","author":["A"],"issued":{"date-parts":[[2024]]},"DOI":"10.1234/foo"}),[])
        self.assertIn("invalid DOI syntax",validate({"title":"x","author":"a","year":2020,"doi":"doi:bad"}))
        self.assertIn("missing title",validate({}))
    def test_confirmed_mapping_only_and_source_preserved(self):
        item={"record":{"id":"r1","title":"Study","author":[],"year":2020},"source_record":{"raw":"keep"}}
        candidates=[{"id":"c1","title":"Study","author":["Ada"],"year":2020}]
        with self.assertRaises(ValueError): apply_mappings([item],candidates,{"r1":{"candidate_id":"c1"}})
        result=apply_mappings([item],candidates,{"r1":{"candidate_id":"c1","confirm":True}})[0]
        self.assertTrue(result["mapping_applied"]); self.assertEqual(result["source_record"],{"raw":"keep"}); self.assertEqual(result["record"]["author"],["Ada"])
        self.assertEqual(rank_candidates(item["record"],candidates)[0]["confidence"],1.0)
    def test_csl_parse_and_bad_mapping_cli(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); src=td/"a.json"; src.write_text(json.dumps({"id":"a","title":"T","author":[{"family":"X"}],"issued":{"date-parts":[[2024]]}}),encoding="utf-8")
            self.assertEqual(len(parse(src)),1); mapping=td/"m.json"; mapping.write_text('{"a":{"candidate_id":"missing","confirm":true}}',encoding="utf-8")
            self.assertEqual(main([str(src),"--mapping",str(mapping)]),2)
    def test_bibtex_and_ris_imports_preserve_source(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); bib=td/"r.bib"; bib.write_text("@article{key,\n title={A title},\n author={A Writer},\n year={2023}\n}\n",encoding="utf-8")
            ris=td/"r.ris"; ris.write_text("TY  - JOUR\nTI  - A title\nAU  - A Writer\nPY  - 2023\nER  -\n",encoding="utf-8")
            parsed_bib=parse(bib)[0]; parsed_ris=parse(ris)[0]
            self.assertEqual(parsed_bib["record"]["title"],"A title")
            self.assertIn("@article",parsed_bib["source_record"]["raw"])
            self.assertEqual(parsed_ris["record"]["title"],"A title")
            self.assertIn("TI  - A title",parsed_ris["source_record"]["raw"])
            inline=td/"inline.bib"; inline.write_text("@article{k, title={A {nested} title}, author={Writer}, year={2023}}",encoding="utf-8")
            self.assertEqual(parse(inline)[0]["record"]["title"],"A {nested} title")
if __name__=="__main__": unittest.main()
