
import re

from core.app_context import app_context

def unwrap_page_divs(html):
    """
    Remove the editor page wrapper elements while preserving their content.

    Target wrapper:

        <div class="page" contenteditable="true"  page-number="N">
            ...
        </div>

    Result:

        The opening and closing page wrapper tags are removed,
        but all nested content remains unchanged.

    Returns:
        Modified HTML string.

    Dependencies:
        - Assumes editor pages are represented by
          <div class="page" contenteditable="true" page-number="N">.
        - Assumes page wrappers are properly balanced HTML div elements.
        - Assumes nested content may contain arbitrary div structures.
        - Assumes page-number contains only numeric values.

    Potential bugs / limitations:
        - This is not an HTML parser; it performs text scanning.
        - Attribute order must exactly match the regex.
          For example this will NOT match:

              <div page-number="1"
                   class="page"
                   contenteditable="true">

        - Additional attributes may prevent matching:

              <div class="page"
                   contenteditable="true"
                   page-number="1"
                   data-id="123">

        - Single malformed or unclosed div may raise ValueError.
        - If HTML contains invalid nesting, depth tracking may fail.
        - Div-like strings inside JavaScript, CSS, comments,
          or text nodes may theoretically affect matching.
        - Uses a custom div counter instead of a DOM parser,
          therefore correctness depends on reasonably valid HTML.
    """

    # ------------------------------------------------------------------
    # Compile a regex that matches ONLY the editor page opening tag.
    #
    # Example:
    #
    # <div class="page"
    #      contenteditable="true"
    #      page-number="3">
    #
    # Notes:
    #   - Matching is case-insensitive.
    #   - Attribute order must match exactly.
    # ------------------------------------------------------------------
    open_tag = re.compile(
        r'<div\s+class="page"\s+contenteditable="true"\s+page-number="\d+"\s*>',
        re.IGNORECASE
    )

    # ------------------------------------------------------------------
    # Match any opening div tag.
    #
    # Examples:
    #
    # <div>
    # <div class="x">
    # <DIV>
    #
    # Used for nested div depth tracking.
    # ------------------------------------------------------------------
    div_open = re.compile(r'<div[\s>]', re.IGNORECASE)

    # ------------------------------------------------------------------
    # Match any closing div tag.
    #
    # Example:
    #
    # </div>
    #
    # Used together with div_open to maintain nesting depth.
    # ------------------------------------------------------------------
    div_close = re.compile(r'</div>',re.IGNORECASE)

    # ------------------------------------------------------------------
    # Collect output fragments here.
    #
    # The final HTML will be assembled by joining all fragments.
    # ------------------------------------------------------------------
    parts = []

    # ------------------------------------------------------------------
    # Tracks how much of the original HTML has already been copied
    # into the output.
    # ------------------------------------------------------------------
    last_index = 0

    # ------------------------------------------------------------------
    # Iterate through every editor page wrapper found in the document.
    # ------------------------------------------------------------------
    for match in open_tag.finditer(html):

        # --------------------------------------------------------------
        # Skip matches that fall inside a block already processed.
        #
        # This is mainly a safety mechanism against overlapping matches.
        # --------------------------------------------------------------
        if match.start() < last_index:
            continue

        # --------------------------------------------------------------
        # Position immediately after the opening page wrapper tag.
        #
        # This marks the beginning of the content we want to preserve.
        # --------------------------------------------------------------
        start_content = match.end()

        # --------------------------------------------------------------
        # Depth counter.
        #
        # Starts at 1 because we have already entered the target page div.
        # --------------------------------------------------------------
        depth = 1

        # --------------------------------------------------------------
        # Current scan position.
        # --------------------------------------------------------------
        pos = start_content

        # --------------------------------------------------------------
        # Scan forward until the matching closing </div> for the page
        # wrapper is found.
        #
        # Nested divs increase depth.
        # Closing divs decrease depth.
        # --------------------------------------------------------------
        while depth > 0 and pos < len(html):

            # ----------------------------------------------------------
            # Find next opening div after current position.
            # ----------------------------------------------------------
            next_open = div_open.search(html, pos)

            # ----------------------------------------------------------
            # Find next closing div after current position.
            # ----------------------------------------------------------
            next_close = div_close.search(html, pos)

            # ----------------------------------------------------------
            # If no closing div exists, the HTML structure is broken.
            # ----------------------------------------------------------
            if not next_close:
                raise ValueError("Unclosed <div>")

            # ----------------------------------------------------------
            # If the next opening div appears before the next closing div,
            # we entered a nested div.
            # ----------------------------------------------------------
            if next_open and next_open.start() < next_close.start():

                # Increase nesting level.
                depth += 1

                # Continue scanning after this opening tag.
                pos = next_open.end()

            else:

                # ------------------------------------------------------
                # Found a closing div.
                # ------------------------------------------------------
                depth -= 1

                # ------------------------------------------------------
                # Depth reaching zero means we found the matching
                # closing tag for the original page wrapper.
                # ------------------------------------------------------
                if depth == 0:

                    # Start index of the closing page wrapper.
                    closing_start = next_close.start()

                    # End index of the closing page wrapper.
                    closing_end = next_close.end()

                    break

                # ------------------------------------------------------
                # Continue scanning after this closing tag.
                # ------------------------------------------------------
                pos = next_close.end()

        # --------------------------------------------------------------
        # Copy everything before the page wrapper unchanged.
        # --------------------------------------------------------------
        parts.append(
            html[last_index:match.start()]
        )

        # --------------------------------------------------------------
        # Copy only the inner content of the page wrapper.
        #
        # Opening and closing page div tags are intentionally omitted.
        # --------------------------------------------------------------
        parts.append(
            html[start_content:closing_start]
        )

        # --------------------------------------------------------------
        # Advance the processed region beyond the closing page wrapper.
        # --------------------------------------------------------------
        last_index = closing_end

    # ------------------------------------------------------------------
    # Append any remaining HTML after the final processed page wrapper.
    # ------------------------------------------------------------------
    parts.append(
        html[last_index:]
    )

    # ------------------------------------------------------------------
    # Reassemble the document.
    #
    # Newlines are inserted between collected fragments to reduce the
    # chance of accidental tag concatenation.
    # ------------------------------------------------------------------
    return ''.join(parts)


def extract_editor_parts(html_source: str) -> tuple[str, str]:
    """
    Extract editor-specific data from a complete HTML document.

    Returns:
        (
            external_style_html,  # Complete <style id="custom-styles">...</style>
            pages_content         # Inner HTML of the pages-wrapper container
        )

    Potential dependencies:
        - Assumes there is only ONE stylesheet with
          id="custom-styles".
        - Assumes there is only ONE pages-wrapper element.
        - Assumes pages-wrapper is the LAST major element inside <body>.
        - Assumes HTML was generated by this editor or follows the same structure.

    Potential bugs / limitations:
        - Regex is not a true HTML parser.
        - If another </body> string appears inside a script, comment, or text node, extraction may fail.
        - If pages-wrapper is followed by additional elements before </body>, the regex may capture unwanted content.
        - If multiple pages-wrapper elements exist, only the first matching structure is processed.
        - If class order changes (e.g. class="foo pages-wrapper bar") this regex will NOT match.
        - If single and double quotes are removed from class attributes by another tool, extraction may fail.
    """
    # Search for the external stylesheet block previously injected
    # by the editor.
    #
    # Expected format:
    #
    # <style id="external-imported-styles">
    #     ...
    # </style>
    #
    # Regex explanation:
    #
    # <style[^>]*                -> opening style tag
    # id="external-imported-styles"
    #                             required identifier
    # [^>]*>                     -> remaining attributes + tag close
    # .*?                        -> stylesheet content (non-greedy)
    # </style>                   -> closing style tag
    #
    # Flags:
    #   re.I -> ignore case
    #   re.S -> allow '.' to match newlines
    
    style_match = re.search(r'<style[^>]*id=["\']custom-styles["\'][^>]*>.*?</style>',
                            html_source, flags=re.I | re.S)
    
    # Extract the entire matched stylesheet block.
    #
    # group(0) returns:
    #
    # <style id="external-imported-styles">...</style>
    #
    # If no stylesheet exists, return an empty string.
    
    external_style = (style_match.group(0) if style_match else '')
    external_style = external_style.replace('id="custom-styles"',"")

    # Locate the editor's pages-wrapper container.
    #
    # Expected structure:
    #
    # <body>
    #     <div class="pages-wrapper">
    #         ...
    #     </div>
    # </body>
    #
    # Group(1) captures ONLY the inner content of pages-wrapper.
    #
    # The regex intentionally anchors to </body> so that nested page
    # divs do not prematurely terminate the match.
    #
    # IMPORTANT DEPENDENCY:
    #     pages-wrapper should remain the final content container
    #     inside the body.
    
    wrapper_match = re.search(r'<div[^>]*class=["\'][^"\']*\bpages-wrapper\b[^"\']*["\'][^>]*>(.*)</div>\s*</body>',
                            html_source, flags=re.I | re.S)

    # Extract only the inner HTML content of pages-wrapper.
    #
    # Example:
    #
    # Input:
    #
    # <div class="pages-wrapper">
    #     <div class="page">A</div>
    #     <div class="page">B</div>
    # </div>
    #
    # Output:
    #
    # <div class="page">A</div>
    # <div class="page">B</div>
    #
    # If wrapper is not found, return an empty string.
    
    pages_content = (wrapper_match.group(1) if wrapper_match else '')
    
    # Return:
    #
    # external_style :
    #     Complete external stylesheet tag.
    #
    # pages_content :
    #     Inner HTML of pages-wrapper.
    
    return external_style, pages_content


def unpack_block(block:str)->tuple[str, str]:
    """
    Returns (styles, content)
    """
    block = block.replace('<BLOCK>','')
    block = block.replace('</BLOCK>','')

    # Extract all style blocks from imported HTML.
    styles = re.findall( r"<style[^>]*>.*?</style>", block, flags=re.I | re.S)
    styles = ''.join(styles)

    # Remove style blocks from body.
    # They will be reinserted later after synchronization.
    block = re.sub(r"<style[^>]*>.*?</style>", "", block, flags=re.I | re.S)

    block = block.replace("<CONTENT>","")
    block = block.replace("</CONTENT>","")
    
    return styles, block

Edu_Template_Files = ['01-Quiz','02-Formal-Exam']

NEW_CONTENT_PLACEHOLDER = '<!-- NEW CONTENT PLACEHOLDER -->'

assessment_row_template =  '<tr>\n'
assessment_row_template += f'  <td style="text-align: center; vertical-align:top; width:--SideColumnsInches--;">{{}}</td>\n'
assessment_row_template += f'  <td style="border-left:none;border-right:none; width:auto;">{{}}</td>\n'
assessment_row_template += f'  <td style="text-align: center; vertical-align:top; width:--SideColumnsInches--;">{{}}</td>\n'
assessment_row_template +=  '</tr>\n'

def replace_placeholders(html, language_setting, data) -> str:
        
        replacements = {
            '-- 2.43 Inches --': f'{2.43*app_context.DPI}px',
            '-- 2.42 Inches --': f'{2.42*app_context.DPI}px',
            '--SideColumnsInches--': f'{0.35*app_context.DPI}px',
            '-- 6.19 Inches --': f'{app_context.EDU_ITEM_PIXELS}px',

            '--Student Name--': language_setting['Student Name'], 
            '--StudentNameValue--': data['Student'], 
            '--Title--': language_setting['Title'],
            '--TitleValue--':data['Title'],
            '--Time--': language_setting['Time'],
            '--TimeValue--': data['Time'],
            '--Date--':language_setting['Date'],
            '--DateValue--': data['Date'], 
            '--Duration--': language_setting['Duration'],
            '--DurationValue--': data['Duration'],
            '--Time Unit--': language_setting['Time Unit'],
            '--Header--': language_setting['Header'],
            '--Row--': language_setting['Row'],
            '--Score--': language_setting['Score'],
            '--Total Score--':language_setting['Total Score'], 
            '--TotalScoreValue--': data['Total Score'],
            '--Teacher--': language_setting['Teacher'],
            '--TeacherValue--': data['Teacher']
        }
        
        if str(data['Template']).lower().find('formal')>-1:
            # Replace content placeholders
            replacements['--In The Name Of God--']= language_setting['In The Name Of God']
            replacements['--Student Id--']= language_setting['Student Id'] 
            replacements['--StudentIdValue--']= data['Student Id']
            replacements['--Organisation Info--']= data['Org-Info'].replace('\n','<br>')
            replacements['--Academic Year--']= language_setting['Academic Year']
            replacements['--AcademicYearValue--'] = data['Academic Year']
            replacements['--Term--']= language_setting['Term']
            replacements['--TermValue--']= data['Term']
            replacements['--Field--']= data['Field']

        for placeholder, value in replacements.items(): html = html.replace(placeholder, value)

        return html

attr_patterns = [
        r'class="page"',
        r'contenteditable="[^"]*"',
        r'page-number="[^"]*"',
        r'data-page-observed="[^"]*"',
    ]
# It is used to remove extra attributes of the page class. 
# We will store this class in the database without any added attributes 
# and when displaying it we will need the class name which we will 
# inject into the tag at that moment.
def remove_specific_attrs(html):
    # List of regex patterns for the attributes to remove (values in double quotes)
    patterns = [
        r'class="page"',
        r'contenteditable="[^"]*"',
        r'page-number="[^"]*"',
        r'data-page-observed="[^"]*"',
    ]

    for pat in patterns:
        # Match attribute with optional surrounding whitespace, replace with a single space
        html = re.sub(r'\s*' + pat + r'\s*', ' ', html)

    # Collapse multiple spaces into one, and remove any space immediately before '>'
    html = re.sub(r'\s+', ' ', html)
    html = re.sub(r'\s>', '>', html)

    return html

# We use it to add desired properties like class name, page orientation, etc.
# to the div before sending it to the editor. Our initial goal is to add the name class="page".
def add_attr_to_root_div(html, attribute):
    """
    Adds an attribute string (e.g. 'class="page"') to the first top-level <div>
    (depth 0 among div tags) in the HTML string. Returns the modified HTML.
    """
    # --- 1. Find the position of the root <div> opening tag ---
    pos = None   # start index of the root <div ...> in html
    depth = 0

    # Find all opening and closing div tags, in order of appearance
    tag_pattern = re.compile(r'<(/)?div\b[^>]*>', re.IGNORECASE)
    for m in tag_pattern.finditer(html):
        if m.group(1):          # it's a closing </div>
            depth -= 1
        else:                   # it's an opening <div ...>
            if depth == 0:      # we are at the root level
                pos = m.start()
                break           # take the very first one
            depth += 1

    if pos is None:
        # No root div found – return the HTML unchanged (or raise an exception)
        return html

    # --- 2. Extract and modify the opening tag ---
    # Find the end of this opening tag (the closing '>')
    tag_end = html.index('>', pos)
    opening_tag = html[pos:tag_end+1]   # includes the '>'

    # Insert the attribute right before the closing '>'
    # (If the attribute already exists you may want to skip or replace it;
    #  this simple version just appends it.)
    if opening_tag.rstrip().endswith('/>'):  # self-closing? (unlikely for div but safe)
        new_tag = opening_tag[:-2] + ' ' + attribute + '/>'
    else:
        new_tag = opening_tag[:-1] + ' ' + attribute + '>'

    # --- 3. Rebuild the HTML ---
    return html[:pos] + new_tag + html[tag_end+1:]

# Check the style is valid:
# returns True only if the whole style content is syntactically “clean” 
# (no dangling text outside rule sets or malformed blocks)
def has_clean_style(style):
    """
    Return True if a <style> tag contains only valid rule sets (each with
    at least one declaration) and no stray text outside curly braces.
    """
    style_pattern = re.compile(r'<style[^>]*>(.*?)</style>', re.IGNORECASE | re.DOTALL)
    for m in style_pattern.finditer(style):
        content = re.sub(r'/\*.*?\*/', '', m.group(1), flags=re.DOTALL)
        # Remove all whitespace for the structure check
        stripped = re.sub(r'\s+', '', content)
        # Allow only a sequence of selector{declarations} blocks
        if re.fullmatch(r'(?:[^{}]+?\{[^}]*?;[^}]*?\})*', stripped) and \
           re.search(r'\{[^}]*?\b[a-zA-Z-]+\s*:\s*[^;]+;', content):
            return True
    return False

