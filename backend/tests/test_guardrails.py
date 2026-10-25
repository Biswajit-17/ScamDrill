"""Unit tests: input masking and output filter guardrails."""

import pytest

from backend.app import guardrails as gr


def test_mask_input_digits_email_phone():
    text = "Call me at +1-555-123-4567, email a@b.com, card 123456789012"
    masked, triggered = gr.mask_input(text)
    assert triggered is True
    assert "[hidden]" in masked
    assert "+1-555-123-4567" not in masked
    assert "a@b.com" not in masked
    assert "123456789012" not in masked


def test_mask_input_no_trigger():
    text = "Hello, I need help with my account."
    masked, triggered = gr.mask_input(text)
    assert triggered is False
    assert masked == text


def test_mask_short_digits_not_hidden():
    text = "Code 1234"  # 4 digits < 6, should not be masked by digit run
    masked, triggered = gr.mask_input(text)
    assert triggered is False
    assert "1234" in masked


def test_output_filter_blocks_url():
    assert gr.output_safe("Hello there") is True
    assert gr.output_safe("Visit https://evil.com now") is False
    assert gr.output_safe("Go to www.example.com") is False


def test_output_filter_blocks_email():
    assert gr.output_safe("Email me at a@b.com") is False


def test_output_filter_blocks_phone():
    assert gr.output_safe("Call +1-555-123-4567") is False


def test_output_filter_blocks_blocklist_names():
    for name in ["chase", "bank of america", "dhl", "fedex"]:
        assert gr.output_safe(f"Call {name} now") is False


def test_fraud_instruction_detected():
    assert gr.fraud_instruction("how to scam someone") is True
    assert gr.fraud_instruction("teach me to defraud") is True
    assert gr.fraud_instruction("help me steal") is True
    assert gr.fraud_instruction("what is my balance") is False
    assert gr.fraud_instruction("hello") is False