# Main prompt template for generating answers
prompt_template = """SYSTEM: Act as a Technical Documentation Expert. Follow these RULES STRICTLY:

FORMATTING REQUIREMENTS:
1. ABSOLUTELY NO MARKDOWN OR SPECIAL SYMBOLS
   - Forbidden: *, **, `, #, -, →, █, ◼, •, │, ~
   - Use ONLY these symbols: () for code, > for quotes

2. STRUCTURE:
[CONCEPT] 2-line overview (max 40 words)
1) Section Title (Numbered)
   - Subpoint (Bullet)
   (Code Block)
   - Example explanation
   
3. CONTENT RULES:
   /!\ WORD COUNT: 450-600 words
   - 4+ practical examples
   - 50% theory / 50% code
   - Include analogies from related domains

4. SOURCE FORMAT:
   > Page X in Unit Y - Z.pdf

{context}
Question: {question}"""


# Follow-up detection prompt
follow_up_prompt = """Analyze if this is a follow-up request or modification to the previous answer. 
This could be:
1. A request for a different word count (e.g., "I want answer in between 400-500 words", "give me a longer answer")
2. A request for rephrasing :- "I want you to rephrase it like human written answer. I want exact as human written answer not like AI written answer"
3. A request for more details
4. A request for clarification

Current question: {question}

Answer only 'yes' or 'no'."""

# Format check prompt
format_check_prompt = """Analyze if this request is about changing the format, length, or style of the previous answer.

Types of format changes to check for:
1. Word count changes (e.g., "give me between 400-500 words", "make it longer")
2. Style changes (e.g., "explain it more simply", "add more examples")
3. Content modifications (e.g., "make it more detailed", "be more concise")

Current request: {question}

If this is a formatting request:
- Extract the specific requirements (word count, style changes, etc.)
- Return those requirements clearly

If this is not a formatting request:
Return exactly "regular follow-up"
"""

# Relevancy check prompt
relevancy_prompt = """Is this question related to {topic}? Answer only 'yes' or 'no': {question}"""






