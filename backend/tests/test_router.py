from app.agents.router import Intent, classify_intent


def test_default_intent_is_grounded_qa():
    assert classify_intent("How should I improve product activation?") == Intent.GROUNDED_QA


def test_essay_request_routes_to_ship30():
    assert classify_intent("Turn the key lessons about retention into an essay") == Intent.SHIP30_ESSAY
    assert classify_intent("Write a ship30 essay about pricing") == Intent.SHIP30_ESSAY


def test_html_artifact_request_routes_to_html():
    assert classify_intent("Generate an html artifact for a landing page") == Intent.ARTIFACT_HTML


def test_markdown_artifact_request_routes_to_markdown():
    assert classify_intent("Create a markdown one-pager summarizing this") == Intent.ARTIFACT_MARKDOWN


def test_plain_followup_question_is_grounded_qa():
    assert classify_intent("What about retention specifically?") == Intent.GROUNDED_QA
