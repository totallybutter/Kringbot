import os
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()
DATA_FOLDER = "data"

# CATEGORY_FILE = DATA_FOLDER + "/categories.txt"
# def load_categories(filepath=CATEGORY_FILE) -> dict:
#     category_keywords = defaultdict(list)
#     current_category = None

#     with open(filepath, "r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()
#             if not line or line.startswith("#"):  # skip comments or blank lines
#                 continue
#             if line.startswith("[") and line.endswith("]"):
#                 current_category = line[1:-1].lower()
#             elif current_category:
#                 category_keywords[current_category].append(line.lower())

#     return category_keywords

# RESPONSES_FILE = DATA_FOLDER + "/responses.txt"
# def load_responses(filepath=RESPONSES_FILE) -> dict:
#     responses = defaultdict(list)
#     current_category = "general"

#     with open(filepath, "r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()
#             if not line:
#                 continue
#             if line.startswith("[") and line.endswith("]"):
#                 current_category = line[1:-1].lower()
#             else:
#                 responses[current_category].append(line)

#     return responses

# SPECIALS_FILE = DATA_FOLDER + "/special.txt"
# def load_special_responses(filepath=SPECIALS_FILE) -> dict:
#     special_responses = {}
#     with open(filepath, "r", encoding="utf-8") as f:
#         current_key = None
#         for line in f:
#             line = line.strip()
#             if not line:
#                 continue
#             if line.startswith("[") and line.endswith("]"):
#                 current_key = line[1:-1].lower()
#             elif current_key:
#                 special_responses[current_key] = line  # only one response per special
#     return special_responses

def generate_ngrams(tokens, n):
    """
    Return a list of all consecutive n‑word chunks (n‑grams) from the given list of tokens.
    For example, if tokens = ["when", "will", "i", "sleep"] and n=2,
    the result is ["when will", "will i", "i sleep"].
    """
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]

def categorize_question(question: str, category_keywords: dict) -> str:
    """
    Categorize the user's question using an n‑gram approach.

    :param question: The user’s question string (e.g., "When will I sleep?")
    :param category_keywords: A dictionary mapping categories to lists of keywords,
                             e.g. {
                               "timing": ["when", "when will i"],
                               "yesno": ["will i", "can i"]
                             }

    :return: The name of the chosen category (e.g. "timing").
    """
    # 1) Convert the question to lowercase, then split into tokens (words).
    tokens = question.lower().split()

    # 2) Determine the maximum keyword size (in words) across all categories,
    #    so we know how many n‑grams we should generate.
    #    For example, if there's a keyword "when will i" (3 words),
    #    max_kw_size becomes at least 3.
    max_kw_size = 1
    for keywords in category_keywords.values():
        for kw in keywords:
            kw_size = len(kw.split())  # number of words in this keyword
            if kw_size > max_kw_size:
                max_kw_size = kw_size


    # 3) Generate all n‑grams from size 1 up to max_kw_size.
    #    For instance, if max_kw_size is 3, we collect 1‑grams, 2‑grams, 3‑grams.
    all_ngrams = []
    for n in range(1, max_kw_size + 1):
        all_ngrams.extend(generate_ngrams(tokens, n))
    # Now all_ngrams might be something like:
    # ["when", "will", "i", "sleep",  # (1‑grams)
    #  "when will", "will i", "i sleep",  # (2‑grams)
    #  "when will i", "will i sleep"]  # (3‑grams)


     # 4) Score each category based on how many keyword phrases it matches in the question.
    scores = {}
    for category, keywords in category_keywords.items():
        score = 0
        for kw in keywords:
            # Normalize the keyword, then see if that exact phrase is among our n‑grams
            # e.g. if kw = "when will i", we look for "when will i" in all_ngrams
            normalized_kw = kw.lower()
            if normalized_kw in all_ngrams:
                # 5) Weight the match by the number of words in the keyword.
                #    e.g. "when will i" => 3 words => +3 points
                score += len(normalized_kw.split())

        scores[category] = score


    # 6) Pick the category with the highest total score.
    best_score = max(scores.values())
    if best_score == 0:
        return "general"
    tied_categories = [cat for cat, s in scores.items() if s == best_score]

    # Tie‑break by whichever category appears first in the original dictionary order
    for cat in category_keywords:
        if cat in tied_categories:
            return cat

    # Safety fallback, shouldn't reach here
    return list(category_keywords.keys())[-1]
