import os
import time
from google import genai
from google.genai.errors import ClientError

# ---------------------------
# 1️⃣ Load API key from environment variable
# ---------------------------
API_KEY = "AIzaSyAXprsvJy44V14AsnqoGRQOtMEaEdEZAdU"
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not set! Please set it in your environment.")

# ---------------------------
# 2️⃣ Create the client
# ---------------------------
client = genai.Client(api_key=API_KEY)

# ---------------------------
# 3️⃣ Safe generation function with retry
# ---------------------------
def generate_text_safe(prompt, model="gemini-2.5-flash", max_retries=5):
    """
    Generate text safely with exponential backoff on rate limits.
    """
    for attempt in range(max_retries):
        try:
            # Generate text
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            return response.text
        except ClientError as e:
            # Check if it's a rate-limit error
            if "RESOURCE_EXHAUSTED" in str(e):
                wait_time = (attempt + 1) * 10  # Exponential backoff: 10s, 20s, 30s...
                print(f"Rate limit hit. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise e
    raise RuntimeError("Failed after maximum retries")

# ---------------------------
# 4️⃣ Example batch prompts
# ---------------------------
prompts = [
    "what is the capital of France?",
]

# Process each prompt safely
for prompt in prompts:
    result = generate_text_safe(prompt)
    print(f"\nPrompt: {prompt}\nResponse: {result}")
# 3️⃣ List all available models
# ---------------------------
# Fetch and list all models
for model in client.models.list():
    # You can filter models by supported actions, e.g., 'generateContent'
    actions = ", ".join(model.supported_actions)
    print(f"Name: {model.name}")
    print(f"Display Name: {model.display_name}")
    print(f"Capabilities: {actions}\n")
# ---------------------------
# 4️⃣ Close client
# ---------------------------
client.close()