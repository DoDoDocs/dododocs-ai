from ktb_prompts import *
from ktb_func import *

import numpy as np
import os
import time
from typing import List, Dict, Optional, Tuple, Any, Generator

"""**FUNCTION FOR LLM API**"""

def get_completion(
    messages: List[Dict],
    model: Optional[str] = MODEL,
    temperature: Optional[float] = TEMPERATURE,
    stop: Optional[List[str]] = None,
    seed: Optional[int] = SEED,
    tools: Optional[List] = None,
    logprobs: Optional[int] = None,
    top_logprobs: Optional[Dict[str, float]] = None,
    max_tokens: Optional[int] = None,
    stream: Optional[bool] = False,
) -> str:
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    if tools:
        params["tools"] = tools

    if model.startswith("gpt") :
        params["stop"] = stop
        params["logprobs"] = logprobs
        params["top_logprobs"] = top_logprobs
        params["seed"] = seed

        completion = client_gpt.chat.completions.create(**params)
        return completion.choices[0].message.content, completion

    elif model.startswith("claude") :
        params["max_tokens"] = max_tokens
        params["stop_sequences"] = stop

        completion = client_claude.messages.create(**params)
        return completion.content[0].text, completion

#parameters for gpt
def get_json_data(
    messages: List[Dict[str, str]],
    model: Optional[str] = MODEL,
    temperature: Optional[float] = TEMPERATURE,
    stop: Optional[List[str]] = None,
    seed: Optional[int] = SEED,
    tools: Optional[List] = None,
    logprobs: Optional[int] = None,
    top_logprobs: Optional[Dict[str, float]] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, any]:
    """Generate JSON data for API request based on model type."""
    
    params = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }
    
    if tools:
        params["tools"] = tools

    # Handle parameters for GPT models
    if model.startswith("gpt"):
        params["stop"] = stop
        params["logprobs"] = logprobs
        params["top_logprobs"] = top_logprobs
        params["seed"] = seed
        # Return the parameters for GPT models
        return params

    # Handle parameters for Claude models
    elif model.startswith("claude"):
        params["max_tokens"] = 8192
        params["stop_sequences"] = stop
        # Return the parameters for Claude models
        return params

    # In case of an unsupported model, you can raise an exception or return None
    raise ValueError(f"Unsupported model type: {model}")

#chat_format
def chat_format(prompt: str, contents: str) -> list[dict[str, str]]:
  if MODEL.startswith("gpt") :
    system = "system"
  else :
    system = "assistant"

  return [{"role": system, "content": prompt}, {"role": "user", "content": contents}]

#doc 생성
def generate_doc(code: str, prompt: str, file_name: str, path: str) -> str:
  DOC_RESPONSE, _ = get_completion(
      chat_format(prompt, code)
      )

  current_time = time.strftime("%H%M%S")
  os.makedirs(path, exist_ok=True)
  with open(path+file_name.replace('java', 'md'), "w", encoding="utf-8") as file:
      file.write(DOC_RESPONSE)

  print("doc generating complete : ", f"{current_time}_{file_name}")

  return DOC_RESPONSE

def translate_doc(doc: str, prompt: str, path: str) -> str:
  DOC_RESPONSE, _ = get_completion(
      chat_format(prompt, doc)
      )

  current_time = time.strftime("%H%M%S")
  filename = f"translate_output_docs_{current_time}.txt"

  with open(path+filename, "w", encoding="utf-8") as file:
      file.write(DOC_RESPONSE)

  print("doc generating complete : ", filename)

  return DOC_RESPONSE

def get_score(SCORE_RESPONSE) -> list:
    scores = []
    for i in range(len(SCORE_RESPONSE.choices[0].logprobs.content)):
        top_logprobs = SCORE_RESPONSE.choices[0].logprobs.content[i].top_logprobs
        if top_logprobs[0].token.isdigit() :
            score = 0
            tokens = []
            logprobs = []
            for n in range(len(top_logprobs)):
                if top_logprobs[n].token.isdigit() :
                    tokens.append(int(top_logprobs[n].token))
                    logprobs.append(np.exp(top_logprobs[n].logprob))
                    #print(i, int(top_logprobs[n].token), np.exp(top_logprobs[n].logprob))

            probabilities = np.array(logprobs)
            normalized_probs = probabilities / probabilities.sum()
            score = np.dot(tokens, normalized_probs)
            #print(normalized_probs)
            scores.append(score)
    #print(scores)
    return scores

def eval_doc(code: str, prompt: str, doc: str) -> dict:
    _, SCORE_RESPONSE = get_completion(
        chat_format(prompt, code, doc),
        logprobs=True,
        top_logprobs=TOP_LOGPROBS,
        model = 'gpt-4o-mini'
    )

    print("doc evaluating complete")
    print(SCORE_RESPONSE.choices[0].message.content)

    total_score = {}
    categories = [
        "Structure Documentation",
        "Strategy Pattern Implementation",
        "Component Details",
        "Visual Documentation"
    ]
    scores = get_score(SCORE_RESPONSE)
    for category, score in zip(categories, scores):
        total_score[category] = score

    return total_score

def process_single_file(args: Tuple[str, str], path: str) -> Tuple[str, dict]:
    """단일 파일에 대한 처리를 수행합니다."""
    filename, content = args
    try:
        # 파일명 추출
        processed_filename = extract_filename(filename)

        # 문서 생성
        doc = generate_doc(content, GENERATE_DOC_PROMPT, processed_filename, path)

        # 점수 평가
        #score = eval_doc(content, scoring_prompt, doc)

        # 번역
        #translate_doc(doc, translate_prompt)

        return processed_filename
    except Exception as e:
        print(f"파일 처리 중 오류 발생 ({filename}): {str(e)}")
        return processed_filename
