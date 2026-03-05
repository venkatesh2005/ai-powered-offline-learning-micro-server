"""Quick test of quiz generator quality."""
import sys, os, pickle, json
sys.path.insert(0, 'backend')
from quiz_generator import quiz_generator, _is_code

emb = 'backend/embeddings_cache/embeddings.pkl'
with open(emb, 'rb') as f:
    metadata = pickle.load(f)

texts = [m.get('text', '') for m in metadata if isinstance(m, dict) and m.get('text')]
print(f"Chunks: {len(texts)}")

quiz_generator.set_chunks(texts, metadata)
print(f"Sentences: {len(quiz_generator._all_sentences)}")
print(f"Definitions: {len(quiz_generator._all_definitions)}")
print(f"Lists: {len(quiz_generator._all_lists)}")
print(f"Categories: {len(quiz_generator._category_items)}")

# Show all categories and items
print(f"\nAll {len(quiz_generator._category_items)} categories:")
for cat, items in quiz_generator._category_items.items():
    print(f"  '{cat}': {items[:4]}")

print(f"\nAll {len(quiz_generator._all_definitions)} definitions:")
for d in quiz_generator._all_definitions:
    print(f"  [{d['kind']}] '{d['subject']}' -> '{d['definition'][:80]}...'")

print(f"\n{'='*60}")
print("GENERATING 15 QUESTIONS...")
print('='*60)
qs = quiz_generator.generate_quiz(15, 'Python')

for q in qs:
    print(f"\nQ{q['id']}: {q['question']}")
    print(f"  A: {q['optionA']}")
    print(f"  B: {q['optionB']}")
    print(f"  C: {q['optionC']}")
    print(f"  D: {q['optionD']}")
    print(f"  Answer: {q['correctAnswer']}")

print(f"\nTotal: {len(qs)} questions")
