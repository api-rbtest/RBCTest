import json
import os
import openai
import uuid
from hashlib import md5

def post_processing(response: str) -> str:
    """
    This function use to parse Groovy code snippet

    Args:
        response (str): Response to be parsed

    Returns:
        str: Parse Groovy code
    """
    # Extract the code between ```groovy and ```
    if "```groovy" not in response:
        return response
    return response.split("```groovy")[1].split("```")[0]

def store_response(prompt: str, response: str) -> None:
    """
    This function use to store the response to a file

    Args:
        prompt (str): Prompt to be stored
        response (str): Response to be stored
    """
    uuid_str = str(uuid.uuid4())
    gpt_response_folder = "gpt_response"
    os.makedirs(gpt_response_folder, exist_ok=True)
    file_name = f"{gpt_response_folder}/api_response_{uuid_str}.json"
    with open(file_name, "w") as f:
        json.dump({"prompt": prompt, "response": response, 'prompt_hash': md5(prompt.encode()).hexdigest()}, f)

def find_previous_response(prompt: str) -> str:
    """
    This function use to find the previous response for a prompt

    Args:
        prompt (str): Prompt to be found

    Returns:
        str: Previous response
    """
    gpt_response_folder = "gpt_response"
    if not os.path.exists(gpt_response_folder):
        return None
    for file in os.listdir(gpt_response_folder):
        with open(f"{gpt_response_folder}/{file}", "r") as f:
            data = json.load(f)
            if data['prompt_hash'] == md5(prompt.encode()).hexdigest():
                return data['response']
    return None

def GPTChatCompletion(prompt, system="", model='gpt-4-turbo', temperature=0.2, top_p = 0.9, max_tokens=-1):
    previous_response = find_previous_response(prompt)
    if previous_response:
        return previous_response
    
    if system:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    else:
        messages = [
            {"role": "user", "content": prompt}
        ]
        
    try:
        if max_tokens == -1:
            response = openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p = top_p
            )
        else:
            response = openai.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p
            )

        store_response(prompt, response.choices[0].message.content)
        return response.choices[0].message.content
    except Exception as e:
        print(e)
        return None
