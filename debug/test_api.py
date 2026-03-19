import httpx
from openai import OpenAI
import os

# 使用用户提供的 API Key 和 Base URL 进行最小化连通性测试
def test_api_connectivity():
    api_key = "sk-dlzLGhbWtT9j4OjPSC2C4FslWcXcFNIuYpROALEcc06Oqq7Q"
    base_url = "https://svip.xty.app/v1"
    model = "gemini-3.1-pro-preview-thinking" # 先用最基础的模型测试 Key 的权限

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
            {"role": "user", "content": "Hello! This is a connectivity test."}
          ]
        )
        print("\n[SUCCESS] API is working!")
        print(f"Response: {completion.choices[0].message.content}")
    except Exception as e:
        print("\n[FAILURE] API call failed.")
        print(f"Error detail: {e}")

if __name__ == "__main__":
    test_api_connectivity()
