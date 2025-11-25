import unicodedata
import re
# If the text contains the digits, converts to local culture digit.  
def local_culture_digits(text, language:str = 'en'):
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    #latin_digits  = "0123456789"
    if type(text) == type(None) : return ''
    if language.lower() in ['en', 'eng', 'english']: return text
    if language.lower() in ['fa', 'farsi', 'persian','arabic']: 
        return ''.join(persian_digits[int(ch)] if ch.isdigit() else ch for ch in text)

def is_mostly_rtl(text: str, threshold: float = 0.5) -> bool:
    """
    Determines if the given text is mostly right-to-left, ignoring initial Latin/English letters or numbers.

    :param text: Input text to analyze.
    :param threshold: Proportion of RTL characters required to classify as right-aligned (default: 50%).
    :return: True if the text is mostly RTL, False otherwise.
    """
    if not text.strip():
        return False  # Empty or whitespace-only text is not RTL

    rtl_count = 0
    total_count = 0

    for char in text:
        # Skip punctuation, whitespace, and symbols
        if unicodedata.category(char).startswith(("P", "S", "Z")):
            continue  

        # Check if the character is in the RTL Unicode ranges
        if (
            "\u0600" <= char <= "\u06FF"     # Arabic, Persian, Urdu
            or "\u0750" <= char <= "\u077F"  # Arabic Supplement
            or "\u08A0" <= char <= "\u08FF"  # Arabic Extended-A
            or "\u0590" <= char <= "\u05FF"  # Hebrew
            or "\uFB50" <= char <= "\uFDFF"  # Arabic Presentation Forms
            or "\uFE70" <= char <= "\uFEFF"  # Arabic Presentation Forms-B
        ):
            rtl_count += 1
        
        total_count += 1

    # Determine if RTL characters are dominant
    return rtl_count / total_count >= threshold if total_count else False


def get_html_body_content(html_content):
    if type(html_content) == type(None) : return ''

    # Regular expression to match the <body> tag and its content
    body_regex = re.compile(r'<body[^>]*>(.*?)</body>', re.DOTALL)

    # Search for the <body> content
    body_match = body_regex.search(html_content)

    if body_match:
        return body_match.group(1).strip()  # Extract the content inside <body>
    else:
        return ''

