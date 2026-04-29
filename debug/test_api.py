import httpx
from openai import OpenAI
import os
import argparse


DEFAULT_PROMPT = "Hello! This is a connectivity test."

# 使用用户提供的 API Key 和 Base URL 进行最小化连通性测试
def test_api_connectivity(model, prompt, api_key, base_url):

    print(f"Testing connectivity to {base_url} with model {model}...")

    client = OpenAI(
        base_url=base_url, 
        api_key=api_key,
        http_client=httpx.Client(
            base_url=base_url,
            follow_redirects=True,
        ),
    )

    try:
        completion = client.chat.completions.create(
          model=model,
          messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
          ]
        )
        print("\n[SUCCESS] API is working!")
        print(f"Response: {completion.choices[0].message.content}")
    except Exception as e:
        print("\n[FAILURE] API call failed.")
        print(f"Error detail: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="llama2-7b")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--api-key", default=os.getenv("API_KEY", "sk-dlzLGhbWtT9j4OjPSC2C4FslWcXcFNIuYpROALEcc06Oqq7Q"))
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "https://svip.xty.app/v1"))
    args = parser.parse_args()
    test_api_connectivity(args.model, args.prompt, args.api_key, args.base_url)
