"""
Quick test script to verify TinyLlama model performance
Run this to test the new model before using it in the main app
"""
import time
from ai.chatbot import ChatBot
from config import Config

print("=" * 60)
print("TinyLlama Model Speed Test")
print("=" * 60)

# Initialize chatbot with TinyLlama
print(f"\n📋 Current Model: {Config.GPT4ALL_MODEL}")
print(f"📂 Model Path: {Config.MODELS_PATH}")

bot = ChatBot(
    model_name=Config.GPT4ALL_MODEL,
    model_path=Config.MODELS_PATH
)

# Test question
test_question = "What is a variable in programming?"
test_context = "A variable is a named storage location in computer memory that holds a value. Variables can store different types of data like numbers, text, or boolean values."

print(f"\n❓ Test Question: {test_question}")
print("\n⏳ Generating response...\n")

start_time = time.time()
answer, gen_time = bot.generate_response(
    test_question,
    context=test_context,
    max_tokens=100,
    temperature=0.1
)
total_time = time.time() - start_time

print("=" * 60)
print("📝 Response:")
print("-" * 60)
print(answer)
print("-" * 60)
print(f"\n⏱️  Generation Time: {gen_time:.2f} seconds")
print(f"⏱️  Total Time: {total_time:.2f} seconds")
print("=" * 60)

# Speed comparison
if gen_time < 20:
    print("✅ EXCELLENT! Model is working fast!")
elif gen_time < 40:
    print("✅ GOOD! Model is reasonably fast.")
elif gen_time < 70:
    print("⚠️  MODERATE: Still slower than expected.")
else:
    print("❌ SLOW: Model may need further optimization.")

print("\n💡 Tip: Subsequent identical questions will be instant due to caching!")
print("\nTest complete. You can now use the main app with this model.")
