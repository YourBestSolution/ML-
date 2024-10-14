import openai
import chromadb
import json
import logging
import pickle
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Отключение отладочных сообщений
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.WARNING)

# API ключ / прокси
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

OPENAI_API_KEY = config['OPENAI_API_KEY']
OPENAI_API_BASE = config['OPENAI_API_BASE']

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

# Создание клиента и коллекции ChromaDB
chroma_client = chromadb.Client()
embedding_collection = chroma_client.create_collection("doc_vectors")

def load_data_from_file(file_path):
    with open(file_path, 'rb') as file:
        data = pickle.load(file)
    logger.info(f"Данные загружены из файла {file_path}")
    return data

def initialize_embedding_collection(embeddings):
    ids = [embedding[0] for embedding in embeddings]
    documents = [embedding[1] for embedding in embeddings]
    embeddings_data = [embedding[2] for embedding in embeddings]
    embedding_collection.upsert(ids=ids, documents=documents, embeddings=embeddings_data)

@lru_cache(maxsize=128)
async def get_response(query):
    response = openai_client.embeddings.create(
        input=[query],
        model="text-embedding-ada-002"
    )
    query_embedding = response.data[0].embedding

    results = embedding_collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    if results['documents']:
        closest_documents = results['documents']
        combined_response = ' '.join(
            [doc if isinstance(doc, str) else ' '.join(doc) for doc in closest_documents])
        return combined_response
    else:
        return "Данная информация вне моей компетенции."

def generate_instructions():
    instructions = [
        "Определи, отвечает ли последний документ на запрос или связан с ним.",
        "Если документ не отвечает на запрос, верни 'Данная информация вне моей компетенции'.",
        "Если он подходит, выдели только ту часть текста, которая отвечает на запрос, и исправь ошибки в выделенной части, если это необходимо.",
        "Если не знаешь, что по смыслу должно быть, то не исправляй.",
        "В ответе не указывай дополнительную собственную писанину, только исправленный текст.",
        "Если ответ содержит список, сохрани форматирование и начинай каждый пункт с новой строки."
    ]
    return "\n".join(instructions)

async def post_process_response(history):
    prompt_lines = [
        "Учитывая следующий контекст:"
    ]

    for message in history:
        prompt_lines.append(f"{message['role']}: {message['content']}")
    
    prompt_lines.append(generate_instructions())
    prompt = "\n".join(prompt_lines)

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Ты технический помощник-ассистент"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500
    )
    
    result = response.choices[0].message.content.strip()
    if "Данная информация вне моей компетенции" in result:
        return "Данная информация вне моей компетенции."
    else:
        return result