import re
import json

def censor_text(text):
    # Load inappropriate words 
    file_path = "./configs/inappropriate_words.json"
    with open(file_path, "r") as f:
        words_list = json.load(f)
    bad_words = words_list
    pattern = re.compile("|".join(map(re.escape, bad_words)), re.IGNORECASE)
    return pattern.sub("xxxx", text)
   