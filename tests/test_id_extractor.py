from src.id_extractor import extract_sample_id, extract_process_name


class TestExtractSampleId:
    def test_p_id_in_parentheses(self):
        name = "nf-NFCORE_KREWLYZER_KREWLYZER_FILTER_MAF_(P-0000001-T01-TEST)"
        assert extract_sample_id(name) == "P-0000001-T01-TEST"

    def test_c_id_embedded(self):
        name = "alignment_C-003DS_hg38"
        assert extract_sample_id(name) == "C-003DS"

    def test_s_c_id_prefix(self):
        name = "s_C_00ABC_variant_call"
        assert extract_sample_id(name) == "s_C_00ABC"

    def test_no_id(self):
        name = "my_custom_job"
        assert extract_sample_id(name) is None

    def test_p_id_no_parentheses(self):
        name = "filter_P-0000002_step2"
        assert extract_sample_id(name) == "P-0000002"

    def test_p_id_with_long_suffix(self):
        name = "nf-PIPELINE_STEP_(P-0000001-T01-TEST-IGO-12345)"
        assert extract_sample_id(name) == "P-0000001-T01-TEST-IGO-12345"

    def test_parenthesized_content_as_id(self):
        name = "some_job_(SAMPLE123-A)"
        assert extract_sample_id(name) == "SAMPLE123-A"

    def test_c_id_with_dash_suffixes(self):
        assert extract_sample_id("alignment_C-006729-M001-d01_hg38") == "C-006729-M001-d01"

    def test_c_id_with_short_suffix(self):
        assert extract_sample_id("some_job_(C-006729-T001-d)") == "C-006729-T001-d"

    def test_c_id_with_n_suffix(self):
        assert extract_sample_id("nf-PIPELINE_(C-006729-N010-d)") == "C-006729-N010-d"

    def test_p_id_with_igo_suffix(self):
        assert extract_sample_id("job_(P-0070000-T05-IH4)") == "P-0070000-T05-IH4"

    def test_p_id_with_normal_suffix(self):
        assert extract_sample_id("job_(P-0070000-N08-IM7)") == "P-0070000-N08-IM7"

    def test_custom_sample_in_parens(self):
        assert extract_sample_id("some_job_(C00_34)") == "C00_34"


class TestExtractProcessName:
    def test_nextflow_full_name(self):
        name = "nf-NFCORE_KREWLYZER_KREWLYZER_FILTER_MAF_(P-0000001-T01-TEST)"
        assert extract_process_name(name) == "FILTER_MAF"

    def test_c_id_embedded(self):
        name = "alignment_C-003DS_hg38"
        assert extract_process_name(name) == "alignment_hg38"

    def test_s_c_id_prefix(self):
        name = "s_C_00ABC_variant_call"
        assert extract_process_name(name) == "variant_call"

    def test_no_id_passthrough(self):
        name = "my_custom_job"
        assert extract_process_name(name) == "my_custom_job"

    def test_nextflow_different_pipeline(self):
        name = "nf-NFCORE_SAREK_SAREK_MARKDUP_(P-0000002-T01)"
        assert extract_process_name(name) == "MARKDUP"

    def test_cleanup_dangling_separators(self):
        name = "step__C-003DS__final"
        assert extract_process_name(name) == "step_final"
