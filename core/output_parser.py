import re

def strip_think_tags(text: str) -> str:
    """
    Strips <think>...</think> tags and their contents from the model's response.
    This is necessary because reasoning models (DeepSeek-R1, Qwen 3.5 Plus) often
    express struggles or mention safety filters internally, which could cause
    false positives in refusal detection. We only evaluate the final output.
    """
    if not isinstance(text, str):
        return str(text)
        
    # DOTALL allows dot to match newlines
    stripped_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return stripped_text.strip()

def extract_code_blocks(text: str) -> list:
    """
    Extracts purely the code blocks from the markdown response.
    """
    pattern = r'```[\w]*\n(.*?)```'
    matches = re.findall(pattern, text, flags=re.DOTALL)
    return [match.strip() for match in matches]
