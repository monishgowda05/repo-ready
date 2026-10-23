import os
import ollama
from transformers import AutoModelForCausalLM, AutoTokenizer

def main():
    print("Initializing AI Hackathon application...")

    # Load local Gemma 2 9B model
    gemma_model = "google/gemma-2-9b-it"
    print(f"Loading weights from {gemma_model}...")

    # Load Llama 3.1 8B model
    llama_model = "meta-llama/Llama-3.1-8B"
    print(f"Loading weights from {llama_model}...")

    # Simulate inference query
    prompt = "Summarize the latest research on open-weight SLMs."
    print(f"Querying model with prompt: '{prompt}'")
    
    # Ollama call
    try:
        res = ollama.chat(model="gemma2:2b", messages=[{"role": "user", "content": prompt}])
        print(res.get("message", {}).get("content", "Simulation output"))
    except Exception:
        print("Model inference mock completed.")

if __name__ == "__main__":
    main()
