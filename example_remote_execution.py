import lium
# Example 4: Model inference with dependencies
@lium.machine(machine="A100", requirements=["torch", "transformers", "accelerate"])
def run_inference(model_name, prompt):
    """Run model inference on remote GPU."""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, device_map="cuda")

    tokens = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        generated = model.generate(**tokens, max_new_tokens=100)

    return tokenizer.decode(generated[0], skip_special_tokens=True)


if __name__ == "__main__":
    answer = run_inference("sshleifer/tiny-gpt2", "what is the capital of france?")
    print(f"Answer: {answer}")
