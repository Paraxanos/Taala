"""
Taala Rule Learner (N3 / D2.1).
Learns spelling normalization rules from the pilot variant set (Train Half only).
Implements Architecture §4.2.

Usage:
    python tools/learn_rules.py
"""
import csv
import difflib
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple, Set

ROOT = Path(__file__).resolve().parents[1]
SPLIT_PATH = ROOT / "survey" / "split.tsv"
WORDS_PATH = ROOT / "survey" / "words.tsv"
WILD_PATH = ROOT / "data" / "variants" / "wild.tsv"
CONSTRUCTED_PATH = ROOT / "data" / "variants" / "constructed.tsv"
OUT_PATH = ROOT / "locales" / "hi-latn" / "rules.tsv"

# High-frequency English words used to calculate collision rate.
# These are the words most likely to collide with Hinglish transliterations.
ENGLISH_WORDS = [
    "art", "men", "son", "god", "key", "pay", "day", "bay", "may", "say", "way",
    "hay", "lay", "ray", "toy", "joy", "boy", "cow", "how", "now", "low", "mow",
    "row", "sow", "tow", "wow", "buy", "guy", "shy", "sky", "spy", "try", "dry",
    "cry", "fry", "pry", "ply", "sly", "fly", "dye", "eye", "rye", "tie", "pie",
    "die", "lie", "vie", "hie", "bye", "aye", "gym", "hymn", "him", "rim", "dim",
    "tim", "sim", "vim", "yam", "cam", "dam", "ham", "jam", "lam", "ram", "sam",
    "tam", "vam", "bam", "fan", "can", "man", "pan", "ran", "tan", "van", "ban",
    "dan", "jan", "ken", "pen", "ten", "den", "fen", "hen", "ben", "wen", "yen",
    "zen", "bin", "din", "fin", "gin", "hin", "jin", "kin", "lin", "min", "nin",
    "pin", "rin", "sin", "tin", "vin", "win", "yin", "zin", "don", "con", "fon",
    "gon", "hon", "ion", "jon", "kon", "lon", "mon", "non", "pon", "ron", "son",
    "ton", "von", "won", "yon", "zon", "cop", "hop", "mop", "nop", "pop", "sop",
    "top", "bop", "fop", "lop", "bun", "fun", "gun", "hun", "jun", "lun", "mun",
    "nun", "pun", "run", "sun", "tun", "dun", "cub", "dub", "hub", "lub", "nub",
    "pub", "rub", "sub", "tub", "bud", "cud", "dud", "mud", "pud", "bug", "dug",
    "hug", "jug", "lug", "mug", "pug", "rug", "tug", "bum", "gum", "hum", "mum",
    "pum", "rum", "sum", "tum", "cat", "bat", "fat", "hat", "mat", "pat", "rat",
    "sat", "vat", "eat", "tea", "ate", "sea", "see", "ear", "are", "ere", "owe",
    "own", "won", "one", "two", "too", "for", "fore", "four", "fir", "fur", "far",
    "fare", "fair", "hair", "hare", "here", "hear", "heir", "air", "err", "urn",
    "earn", "erne", "tern", "turn", "torn", "tone", "ton", "tun", "tin", "ten",
    "tan", "pin", "pen", "pan", "pun", "sun", "son", "bun", "bin", "ben", "ban",
    "fun", "fin", "fen", "fan", "gun", "gin", "gen", "gan", "run", "rin", "ren",
    "ran", "dun", "din", "den", "dan", "nun", "nin", "nen", "nan", "nit", "net",
    "nat", "nut", "not", "note", "knot", "rot", "root", "rote", "write", "right",
    "rite", "white", "wight", "weight", "wait", "wade", "weed", "we", "us", "use",
    "you", "ewe", "yew", "i", "aisle", "isle", "him", "hymn", "her", "hers", "year",
    "fear", "feer", "deer", "dear", "dare", "door", "do", "due", "dew", "blue",
    "blew", "new", "knew", "gnu", "shoe", "shoo", "who", "whose", "whom", "loom",
    "loam", "home", "holm", "hole", "whole", "heal", "heel", "hill", "will", "well",
    "weal", "wheel", "real", "reel", "read", "reed", "red", "led", "lead", "lad",
    "laid", "lid", "lie", "lye", "rye", "tie", "dye", "guy", "buy", "by", "bye",
    "bi", "pie", "pi", "pea", "pee", "tea", "tee", "key", "quay", "lee", "lea",
    "flee", "flea", "glee", "plea", "pale", "pail", "tale", "tail", "sale", "sail",
    "male", "mail", "jail", "gale", "fail", "bail", "hail", "nail", "wail", "mate",
    "meat", "meet", "mete", "teak", "tik", "pass", "word", "love", "god", "ram",
    "sit", "pass", "word", "love", "god", "ram", "sit", "pass", "word", "love"
]

class Rule:
    def __init__(self, ctx_left: str, old: str, new: str, ctx_right: str):
        self.ctx_left = ctx_left
        self.old = old
        self.new = new
        self.ctx_right = ctx_right
        self.support = 0

    @property
    def pattern(self) -> str:
        return f"{self.ctx_left}{self.old}{self.ctx_right}"

    @property
    def replacement(self) -> str:
        return f"{self.ctx_left}{self.new}{self.ctx_right}"

    def apply(self, text: str) -> str:
        if not self.pattern: return text # Safeguard against empty pattern
        return text.replace(self.pattern, self.replacement)

    def __repr__(self):
        return f"{self.pattern} -> {self.replacement}"

    def __hash__(self):
        return hash((self.ctx_left, self.old, self.new, self.ctx_right))

    def __eq__(self, other):
        return (self.ctx_left, self.old, self.new, self.ctx_right) == (
            other.ctx_left, other.old, other.new, other.ctx_right
        )

def load_data() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """Load Train Half variants and Reference spellings."""
    train_ids = set()
    with open(SPLIT_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["split"] == "train":
                train_ids.add(row["id"])

    refs = {}
    with open(WORDS_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["id"] in train_ids:
                refs[row["id"]] = row["ref_latin"]

    variants = defaultdict(list)
    
    def read_variants(path, spelling_col="spelling"):
        if not path.exists(): return
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                wid = row["word_id"]
                if wid in train_ids:
                    variants[wid].append(row[spelling_col])

    read_variants(WILD_PATH)
    read_variants(CONSTRUCTED_PATH)

    for wid, ref in refs.items():
        variants[wid].append(ref)
        
    for wid in variants:
        variants[wid] = list(set(s.lower() for s in variants[wid] if s.isalpha()))
        
    return variants, refs

def extract_candidates(variants: Dict[str, List[str]]) -> List[Rule]:
    """Extract candidate rules with a STRICT safety filter to prevent mangling."""
    candidate_counts = defaultdict(int)
    
    for wid, spellings in variants.items():
        if len(spellings) < 2: continue
        
        for i in range(len(spellings)):
            for j in range(i + 1, len(spellings)):
                s1, s2 = spellings[i], spellings[j]
                if s1 == s2: continue
                
                matcher = difflib.SequenceMatcher(None, s1, s2)
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag == "equal": continue
                    
                    old_part = s1[i1:i2]
                    new_part = s2[j1:j2]
                    
                    if old_part == new_part: continue
                    
                    # --- STRICT SAFETY FILTER ---
                    # 1. Forbid ALL deletions (new_part is empty)
                    if not new_part: continue
                    # 2. Forbid ALL insertions (old_part is empty)
                    if not old_part: continue
                    # 3. Forbid ALL 1-to-1 character swaps (e.g., 'k'->'c', 'w'->'v')
                    if len(old_part) == 1 and len(new_part) == 1: continue
                    # 4. Forbid rules that are too long (likely whole words)
                    if len(old_part) > 3 or len(new_part) > 3: continue
                    # ----------------------------

                    # We ONLY generate context-free rules for multi-char swaps.
                    # Context-specific rules via str.replace() are unsafe in Python 
                    # (e.g., replacing "ka" with "k" globally destroys "karan").
                    candidate_counts[("", old_part, new_part, "")] += 1
                    candidate_counts[("", new_part, old_part, "")] += 1
                                
    # Architecture §4.2: Keep candidates seen at least 3 times.
    rules = []
    for (cl, old, new, cr), count in candidate_counts.items():
        if count >= 3:
            r = Rule(cl, old, new, cr)
            r.support = count
            rules.append(r)
            
    return rules

def apply_rules(text: str, rules: List[Rule]) -> str:
    """Apply a list of rules iteratively until stable."""
    prev = None
    curr = text
    for _ in range(10):
        prev = curr
        for r in rules:
            curr = r.apply(curr)
        if curr == prev:
            break
    return curr

def calculate_metrics(rules: List[Rule], variants: Dict[str, List[str]], english_words: List[str]) -> Tuple[float, float, float]:
    """Calculate Merge Rate, False Merge Rate, and English Collision Rate."""
    canon_map = defaultdict(set) 
    total_pairs = 0
    merged_pairs = 0
    
    for wid, spellings in variants.items():
        canons = set(apply_rules(s, rules) for s in spellings)
        for c in canons:
            canon_map[c].add(wid)
            
        n = len(spellings)
        total_pairs += n * (n - 1) / 2
        counts = defaultdict(int)
        for s in spellings:
            counts[apply_rules(s, rules)] += 1
        merged_pairs += sum(c * (c - 1) / 2 for c in counts.values())
        
    merge_rate = merged_pairs / total_pairs if total_pairs > 0 else 0.0
    
    false_merges = sum(1 for wids in canon_map.values() if len(wids) > 1)
    total_words = len(variants)
    false_merge_rate = false_merges / total_words if total_words > 0 else 0.0
    
    hinglish_canons = set(canon_map.keys())
    collisions = 0
    for ew in english_words:
        c = apply_rules(ew, rules)
        if c in hinglish_canons:
            collisions += 1
            
    collision_rate = collisions / len(english_words) if english_words else 0.0
    
    return merge_rate, false_merge_rate, collision_rate

def greedy_select(candidates: List[Rule], variants: Dict[str, List[str]], english_words: List[str], max_rules: int = 80) -> List[Rule]:
    """Greedy selection maximizing score."""
    selected = []
    current_score = -1.0
    
    LAMBDA = 2.0  
    MU = 2.0      
    
    total_cands = len(candidates)
    print(f"Evaluating {total_cands} candidates...")
    
    for step in range(max_rules):
        best_rule = None
        best_gain = 0.0
        
        for idx, cand in enumerate(candidates):
            if cand in selected: continue
            
            # Progress indicator
            if idx % 50 == 0:
                sys.stdout.write(f"\rStep {step+1}: testing candidate {idx+1}/{total_cands}...")
                sys.stdout.flush()
            
            test_rules = selected + [cand]
            m, fm, ec = calculate_metrics(test_rules, variants, english_words)
            score = m - LAMBDA * fm - MU * ec
            
            gain = score - current_score
            if gain > best_gain:
                best_gain = gain
                best_rule = cand
                
        if best_rule is None or best_gain < 0.001:
            break
            
        selected.append(best_rule)
        current_score += best_gain
        print(f"\nSelected: {best_rule} (Support: {best_rule.support}, Gain: {best_gain:.4f}, Score: {current_score:.4f})")
        
    return selected

def main():
    print("Loading data...")
    variants, refs = load_data()
    print(f"Loaded {len(variants)} train words.")
    
    print("Extracting candidates...")
    candidates = extract_candidates(variants)
    print(f"Found {len(candidates)} candidate rules with support >= 3.")
    
    print("Greedy selection...")
    selected = greedy_select(candidates, variants, ENGLISH_WORDS)
    
    print(f"\nFinal Rules ({len(selected)}):")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["ctx_left", "old", "new", "ctx_right", "pattern", "replacement", "support"])
        for r in selected:
            writer.writerow([r.ctx_left, r.old, r.new, r.ctx_right, r.pattern, r.replacement, r.support])
            print(f"  {r} (support: {r.support})")
            
    print(f"\nSaved to {OUT_PATH}")

if __name__ == "__main__":
    main()