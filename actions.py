import re
import spacy
import numpy as np
from rasa_sdk import Action
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from rasa_sdk.interfaces import Tracker
from typing import Text, Dict, Any, List
from transformers import BertTokenizer, BertModel
import torch
from sklearn.metrics.pairwise import cosine_similarity

import logging

logger = logging.getLogger(name)

# Загружаем токенизатор и модель BERT
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

# Функция для получения эмбеддингов с помощью BERT
def get_embedding(text: str):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
    # Берем эмбеддинг из последнего слоя модели
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings

# Функция для расчета косинусного расстояния
def calculate_similarity(embedding1, embedding2):
    return cosine_similarity(embedding1.cpu().numpy(), embedding2.cpu().numpy())[0][0]

class ActionCheckCandidate(Action):
    def name(self) -> Text:
        return "action_check_candidate"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Получаем значения из слотов
        role = tracker.get_slot("role")
        experience = tracker.get_slot("experience")
        skills = tracker.get_slot("skills")
        salary_text = tracker.get_slot("salary_expectation")
        age = tracker.get_slot("age")  # Слот для возраста

        # Проверка на обязательные поля
        if not role or not experience or not skills or not salary_text or age is None:
            dispatcher.utter_message(text="Пожалуйста, заполните все обязательные поля.")
            return []

        # Проверка возраста на старше 18 лет
        if isinstance(age, int) and age < 18:
            dispatcher.utter_message(text="Кандидат должен быть старше 18 лет.")
            return []

        # Преобразуем опыт в целое число, извлекая только цифры
        experience = self.extract_experience(experience)

        # Преобразуем строку навыков в список, если это строка
        if isinstance(skills, str):
            skills = skills.split(",")  # Преобразуем строку в список

        # Извлекаем зарплату
        salary = self.extract_salary(salary_text)
        if salary is None:
            dispatcher.utter_message(
                text="Не удалось извлечь ожидаемую зарплату. Пожалуйста, введите корректное значение.")
            return []

        # Создаем эмбеддинги для роли, опыта и навыков
        role_embedding = get_embedding(role)
        skills_embedding = get_embedding(" ".join(skills))  # Объединяем навыки в одну строку
        experience_embedding = get_embedding(str(experience))

        # Пример заданных требований для разных ролей
        required_experience = {
            "Data Scientist": 2,
            "Project Manager": 3,
            "Data Engineer": 2,
            "Data Analyst": 1,
            "MLOps Engineer": 2
        }

        required_skills = {
            "Data Scientist": ["Python", "ML"],
            "Project Manager": ["Agile", "Scrum"],
            
            "Data Engineer": ["SQL", "ETL"],
            "Data Analyst": ["SQL", "BI"],
            "MLOps Engineer": ["Docker", "Kubernetes"]
        }

        # Проверка на соответствие требованиям
        if role in required_experience:
            min_exp = required_experience[role]
            required_skills_list = required_skills[role]
            
            # Создаем эмбеддинг для требуемых навыков
            required_skills_embedding = get_embedding(" ".join(required_skills_list))

            # Проверка на соответствие опыта и навыков
            experience_similarity = calculate_similarity(experience_embedding, get_embedding(str(min_exp)))
            skills_similarity = calculate_similarity(skills_embedding, required_skills_embedding)

            # Сравнение на соответствие требованиям
            if experience >= min_exp and experience_similarity > 0.8 and skills_similarity > 0.8:
                dispatcher.utter_message(text="Кандидат соответствует всем требованиям.")
            else:
                dispatcher.utter_message(text="Кандидат не соответствует требованиям.")

        return []


