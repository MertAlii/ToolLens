import json
import os
import threading
import unittest
from unittest.mock import patch

from backend import providers


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.context = {"finding": {"location": {"path": "server.py", "range": {"start_line": 10, "end_line": 20}}, "description": "risk"}}

    def response(self, **updates):
        result = {"content": "Açıklama", "evidence_refs": [{"path": "server.py", "start_line": 10, "end_line": 12}], "uncertainties": ["Dinamik test yapılmadı."], "patch": None}
        result.update(updates)
        return result

    def test_unknown_reference_is_not_accepted(self):
        with self.assertRaises(providers.ProviderError):
            providers._parse_payload(self.response(evidence_refs=[{"path": "secret.py", "start_line": 1, "end_line": 1}]), self.context, "explain")

    def test_reference_must_stay_within_supplied_range(self):
        with self.assertRaises(providers.ProviderError):
            providers._parse_payload(self.response(evidence_refs=[{"path": "server.py", "start_line": 10, "end_line": 21}]), self.context, "explain")

    def test_valid_evidence_remains(self):
        output = providers._parse_payload(self.response(), self.context, "explain")
        self.assertEqual(output["evidence_refs"][0]["path"], "server.py")

    def test_patch_cannot_escape_source_scope(self):
        bad = "--- a/server.py\n+++ b/../secret.py\n@@ -1 +1 @@\n-a\n+b\n"
        with self.assertRaises(providers.ProviderError):
            providers._parse_payload(self.response(patch=bad), self.context, "patch")

    def test_unrequested_patch_is_rejected(self):
        with self.assertRaises(providers.ProviderError):
            providers._parse_payload(self.response(patch="diff"), self.context, "explain")

    def test_secrets_redacted_and_context_bounded(self):
        self.assertEqual(providers._sanitize_context({"password": "abc"})["password"], "[MASKELENDİ]")
        with self.assertRaises(providers.ProviderError):
            providers._sanitize_context({str(i): "x" * 12000 for i in range(10)})

    def test_cli_subscription_environment_removes_api_keys(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "private", "ANTHROPIC_API_KEY": "private", "GEMINI_API_KEY": "private"}):
            env = providers._cli_env()
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertNotIn("GEMINI_API_KEY", env)

    def test_no_invented_model_catalog(self):
        with patch.object(providers, "_binary", return_value=None):
            self.assertEqual(providers.get_models("codex", {}), [])
        self.assertEqual(providers.get_models("claude", {"model": "user-selected-model"}), ["user-selected-model"])

    def test_remote_ollama_is_rejected(self):
        with self.assertRaises(providers.ProviderError):
            providers._ollama_url({"base_url": "https://ollama.example.com"})

    def test_cli_tool_call_invalidates_answer(self):
        events = json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "echo x"}})
        with self.assertRaises(providers.ProviderError):
            providers._extract_cli("codex", events)

    def test_antigravity_stream_returns_final_schema_payload(self):
        events='\n'.join(json.dumps(x) for x in [
            {'event':'init','init':{}},
            {'event':'step_update','step_update':{'step_type':'agent_response','text_delta':'partial'}},
            {'event':'result','result':{'status':'SUCCESS','structured_output':self.response(),'usage':{'input_tokens':10}}}])
        result,usage=providers._extract_cli('antigravity',events)
        self.assertEqual(result,self.response())
        self.assertEqual(usage['input_tokens'],10)

    def test_antigravity_stream_tool_use_is_rejected(self):
        event={'event':'step_update','step_update':{'step_type':'tool','tool_name':'run_command'}}
        with self.assertRaises(providers.ProviderError):
            providers._extract_cli('antigravity',json.dumps(event))

    def test_antigravity_schema_finish_is_not_an_environment_tool(self):
        response=self.response()
        events='\n'.join(json.dumps(x) for x in [
            {'event':'step_update','step_update':{'step_type':'tool','state':'ACTIVE','tool_name':'finish','tool_info':{'name':'finish','parameters':response}}},
            {'event':'step_update','step_update':{'step_type':'finish','state':'DONE'}},
            {'event':'result','result':{'status':'SUCCESS','structured_output':response}}])
        result,_=providers._extract_cli('antigravity',events)
        self.assertEqual(result,response)

    def test_antigravity_finish_cannot_hide_tool_output_or_subagents(self):
        response=self.response()
        for changes in ({'tool_info':{'name':'finish','parameters':response,'output':'read contents'}},
                        {'tool_name':'run_command'},
                        {'subagent_info':{'subagents':[{'type_name':'research'}]}}):
            step={'step_type':'tool','tool_name':'finish','tool_info':{'name':'finish','parameters':response},**changes}
            raw='\n'.join(json.dumps(x) for x in [{'event':'step_update','step_update':step},{'event':'result','result':{'status':'SUCCESS','structured_output':response}}])
            with self.assertRaises(providers.ProviderError):providers._extract_cli('antigravity',raw)

    def test_antigravity_finish_must_match_terminal_schema_payload(self):
        raw='\n'.join(json.dumps(x) for x in [
            {'event':'step_update','step_update':{'step_type':'tool','tool_name':'finish','tool_info':{'name':'finish','parameters':self.response()}}},
            {'event':'result','result':{'status':'SUCCESS','structured_output':self.response(content='different')}}])
        with self.assertRaises(providers.ProviderError):providers._extract_cli('antigravity',raw)

    def test_antigravity_long_finish_telemetry_can_be_a_clipped_prefix(self):
        full=self.response(content='long answer '*60)
        display={**full,'content':full['content'][:500]+'…'}
        raw='\n'.join(json.dumps(x) for x in [
            {'event':'step_update','step_update':{'step_type':'tool','tool_name':'finish','tool_info':{'name':'finish','parameters':display}}},
            {'event':'result','result':{'status':'SUCCESS','structured_output':full}}])
        self.assertEqual(providers._extract_cli('antigravity',raw)[0],full)
        self.assertFalse(providers._agy_finish_matches({**display,'patch':'unexpected'},full))
        self.assertFalse(providers._agy_finish_matches({**display,'content':'short…'},full))
        self.assertFalse(providers._agy_finish_matches(display,{**full,'content':'different prefix '+full['content']}))
        self.assertFalse(providers._agy_finish_matches(display,{**full,'evidence_refs':[{'path':'other.py','start_line':1,'end_line':1}]}))

    def test_antigravity_finish_requires_schema_and_terminal_success(self):
        for parameters,final in [({'content':'not enough'},{'status':'SUCCESS','structured_output':{'content':'not enough'}}),
                                 (self.response(),{'status':'ERROR','structured_output':self.response()}),
                                 (self.response(),{'status':'SUCCESS','response':json.dumps(self.response())})]:
            raw='\n'.join(json.dumps(x) for x in [
                {'event':'step_update','step_update':{'step_type':'tool','tool_name':'finish','tool_info':{'name':'finish','parameters':parameters}}},
                {'event':'result','result':final}])
            with self.assertRaises(providers.ProviderError):providers._extract_cli('antigravity',raw)

    def test_antigravity_real_tool_after_finish_still_invalidates_answer(self):
        response=self.response()
        raw='\n'.join(json.dumps(x) for x in [
            {'event':'step_update','step_update':{'step_type':'tool','tool_name':'finish','tool_info':{'name':'finish','parameters':response}}},
            {'event':'step_update','step_update':{'step_type':'tool','tool_name':'mcp_query','tool_info':{'name':'mcp_query','parameters':{}}}},
            {'event':'result','result':{'status':'SUCCESS','structured_output':response}}])
        with self.assertRaises(providers.ProviderError):providers._extract_cli('antigravity',raw)

    def test_extra_fields_and_non_string_uncertainty_are_rejected(self):
        for raw in [self.response(unexpected=True),self.response(uncertainties=[42])]:
            with self.assertRaises(providers.ProviderError):
                providers._parse_payload(raw,self.context,'explain')

    @patch.object(providers, "_http")
    def test_malformed_output_retries_exactly_once(self, request):
        request.return_value = {"message": {"content": "not JSON"}}
        with self.assertRaises(providers.ProviderError):
            providers.generate("ollama", "local-model", "explain", self.context)
        self.assertEqual(request.call_count, 2)

    @patch.object(providers, "_http")
    def test_provider_failure_never_calls_another_provider(self, request):
        request.side_effect = providers.ProviderError("quota")
        with self.assertRaises(providers.ProviderError):
            providers.generate("ollama", "local-model", "explain", self.context)
        self.assertEqual(request.call_count, 1)

    @patch.object(providers, "_http")
    def test_real_transport_response_maps_provider_metadata(self, request):
        request.return_value = {"message": {"content": json.dumps(self.response())}, "prompt_eval_count": 20, "eval_count": 40}
        result = providers.generate("ollama", "user-local-model", "explain", self.context)
        self.assertEqual(result["provider"], "ollama")
        self.assertEqual(result["model"], "user-local-model")
        self.assertIsNone(result["cost"])

    def test_http_cancel_before_request(self):
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(providers.ProviderError):
            providers._http("http://127.0.0.1:11434/api/chat", cancel_event=cancel)


if __name__ == "__main__":
    unittest.main()
