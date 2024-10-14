import openai
import chromadb
import nltk
from nltk.tokenize import sent_tokenize
import json
import logging
import pickle

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

def download_nltk_resources():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')

download_nltk_resources()

# Преобразование текста в эмбеддинги
def create_embeddings(file_path, batch_size=10):
    logger.info("Начато преобразование текста в эмбеддинги...")
    with open(file_path, 'r', encoding='utf-8') as file:
        text_content = file.read()

    sentences = sent_tokenize(text_content)
    all_embeddings = []

    for start_index in range(0, len(sentences), batch_size):
        end_index = min(start_index + batch_size, len(sentences))
        sentence_batch = sentences[start_index:end_index]
        inputs = [sentence for sentence in sentence_batch if sentence.strip()]

        if not inputs:
            continue

        response = openai_client.embeddings.create(
            input=inputs,
            model="text-embedding-ada-002"
        )
        embeddings = response.data

        ids = [str(start_index + i) for i in range(len(inputs))]
        embeddings_data = [embedding.embedding for embedding in embeddings]

        # Добавление текстов и их векторов в коллекцию
        embedding_collection.upsert(ids=ids, documents=inputs, embeddings=embeddings_data)
        all_embeddings.extend(zip(ids, inputs, embeddings_data))

    logger.info("Преобразование текста в эмбеддинги завершено")
    return all_embeddings

# Сохранение данных в файл
def save_data_to_file(data, file_path):
    with open(file_path, 'wb') as file:
        pickle.dump(data, file)
    logger.info(f"Данные сохранены в файл {file_path}")

if __name__ == "__main__":
    embeddings = create_embeddings('input_text.txt')
    data = {"embeddings": embeddings}
    save_data_to_file(data, 'data.pkl')