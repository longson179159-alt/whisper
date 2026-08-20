import re
import unicodedata
from typing import List, Optional, Tuple
from typing import List, Literal, Optional, Tuple


def clean_word(word: str) -> str:
    w = word.lower().strip()
    w = unicodedata.normalize("NFKD", w)
    w = w.replace("’", "'").replace("–", "-").replace("—", "-")
    w = re.sub(r"[^a-z0-9\s'-]", "", w)
    return w


def get_sentence_lists(subtext: str) -> list[list[str]]:
    paragraphs = [p.strip() for p in subtext.split("\n") if p.strip()]
    two_dimention_sentence_list = []

    for p in paragraphs:
        p = re.sub(r"\s+([。！？.!?])", r"\1", p)
        p = re.sub(r"([。！？.!?]+)", r"\1<S>", p)
        p = re.sub(r"[ \t]+", " ", p)
        sens = [s.strip() for s in p.split("<S>") if s.strip()]
        two_dimention_sentence_list.append(sens)

    return two_dimention_sentence_list


def get_lists_txt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    two_dimention_sentence_list = get_sentence_lists(text)
    list_id = []
    list_ref = []

    count_sentence = 0
    for p_idx, paragraph in enumerate(two_dimention_sentence_list):
        for s_idx, sentence in enumerate(paragraph):
            sentence_idx = count_sentence + s_idx
            tokens = sentence.split()
            for idx_in_s, word in enumerate(tokens):
                list_id.append((word, p_idx, sentence_idx, idx_in_s))
                list_ref.append(clean_word(word))
        count_sentence += len(paragraph)

    # print("total number of sentences", count_sentence)
    return list_ref, list_id


def get_lists_from_text(text):
    two_dimention_sentence_list = get_sentence_lists(text)
    list_id = []
    list_ref = []

    count_sentence = 0
    for p_idx, paragraph in enumerate(two_dimention_sentence_list):
        for s_idx, sentence in enumerate(paragraph):
            sentence_idx = count_sentence + s_idx
            tokens = sentence.split()
            for idx_in_s, word in enumerate(tokens):
                list_id.append((word, p_idx, sentence_idx, idx_in_s))
                list_ref.append(clean_word(word))
        count_sentence += len(paragraph)

    return list_ref, list_id


def nw_ref_match_flags(
    ref: List[str], whisper: List[str]
) -> List[Tuple[str, int, Optional[int]]]:
    MATCH, MISMATCH, GAP = 1, -1, -1
    n, m = len(ref), len(whisper)

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    bt = [[None] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + GAP
        bt[i][0] = "U"
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + GAP
        bt[0][j] = "L"

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            score_diag = dp[i - 1][j - 1] + (MATCH if ref[i - 1] == whisper[j - 1] else MISMATCH)
            score_up = dp[i - 1][j] + GAP
            score_left = dp[i][j - 1] + GAP

            best = max(score_diag, score_up, score_left)

            if best == score_diag:
                dp[i][j], bt[i][j] = score_diag, "D"
            elif best == score_up:
                dp[i][j], bt[i][j] = score_up, "U"
            else:
                dp[i][j], bt[i][j] = score_left, "L"

    aligned_ref, aligned_wh, aligned_widx = [], [], []
    i, j = n, m
    while i > 0 or j > 0:
        move = bt[i][j] if (i >= 0 and j >= 0) else None
        if i > 0 and j > 0 and move == "D":
            aligned_ref.append(ref[i - 1])
            aligned_wh.append(whisper[j - 1])
            aligned_widx.append(j - 1)
            i -= 1
            j -= 1
        elif i > 0 and (j == 0 or move == "U"):
            aligned_ref.append(ref[i - 1])
            aligned_wh.append(None)
            aligned_widx.append(None)
            i -= 1
        else:
            aligned_ref.append(None)
            aligned_wh.append(whisper[j - 1])
            aligned_widx.append(j - 1)
            j -= 1

    aligned_ref.reverse()
    aligned_wh.reverse()
    aligned_widx.reverse()

    result = []
    for r_tok, w_tok, w_idx in zip(aligned_ref, aligned_wh, aligned_widx):
        if r_tok is None:
            continue
        if w_tok is not None and r_tok == w_tok:
            result.append((r_tok, 1, w_idx))
        else:
            result.append((r_tok, 0, None))
    return result


def Get_timestamp(words_in_the_same_para):
    timestamp_sentence_level = []

    for words in words_in_the_same_para:
        sentence_text = " ".join([w["word"] for w in words])
        p_idx = words[0]["p_idx"]

        first_non_null = next((w for w in words if w["has_timestamp"]), None)
        final_non_null = next((w for w in reversed(words) if w["has_timestamp"]), None)

        if not first_non_null or not final_non_null:
            start = end = None
        else:
            start = round(first_non_null["start"], 2)
            end = round(final_non_null["end"], 2)

        timestamp_sentence_level.append({
            "start": start,
            "end": end,
            "text": sentence_text,
            "p_idx": p_idx
        })

    return timestamp_sentence_level


def group_by_para_or_sentence(list_word_level : list[dict], group_type: Literal['p_idx', 's_idx']) -> list[list[dict]]:
    words_in_the_same_type = []
    current_object = []
    current_idx = 0

    for word in list_word_level:
        if word[group_type] == current_idx:
            current_object.append(word)
        else:
            if current_object:
                words_in_the_same_type.append(current_object)
            current_idx = word[group_type]
            current_object = [word]

    if current_object:
        words_in_the_same_type.append(current_object)

    return words_in_the_same_type
