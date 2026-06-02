"""Уровень 1: ML-ранжирование тренировочных планов.

Загружает обученную модель XGBoost rank:ndcg и ранжирует пул из 60 планов
для конкретного пользователя. Возвращает топ-N с обеспечением разнообразия
по модальности (modality diversity sampling).
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import MODEL_PATH, PLANS_PATH


# Порядок признаков и кодирование должны совпадать с тренировочным пайплайном.
# Берутся из артефакта final_model_v2.pkl (поле "feature_order" и "ordinal_maps").
class RankingService:
    """Загружает модель XGBoost и пул из 60 планов. Ранжирует планы под
    профиль пользователя.
    """

    def __init__(self) -> None:
        with open(MODEL_PATH, "rb") as f:
            self.artifact: dict[str, Any] = pickle.load(f)
        self.model = self.artifact["model"]
        self.feature_names: list[str] = self.artifact["feature_names"]
        self.encoder = self.artifact["encoder"]
        with open(PLANS_PATH, encoding="utf-8") as f:
            self.plans: list[dict] = json.load(f)
        print(f"[RankingService] Модель: {self.artifact.get('model_type')}, "
              f"NDCG@3 на тесте: {self.artifact.get('NDCG@3_test', 0):.4f}, "
              f"планов в пуле: {len(self.plans)}")

    def rank_all_plans(self, user: dict) -> list[tuple[dict, float]]:
        """Возвращает все планы со скорами в убывающем порядке."""
        # Создаем DataFrame для всех планов
        data = []
        for plan in self.plans:
            row = {}
            for col in self.feature_names:
                if col in user:
                    row[col] = user[col]
                elif col in plan:
                    row[col] = plan[col]
                else:
                    row[col] = None  # Или значение по умолчанию
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Кодируем признаки через ColumnTransformer из артефакта
        X_encoded = self.encoder.transform(df)
        
        # Получаем предсказания
        scores = self.model.predict(X_encoded)
        
        ranked = sorted(zip(self.plans, scores.tolist()),
                        key=lambda t: -t[1])
        return ranked

    def select_top_diverse(self, user: dict, n: int,
                            forbidden_plan_ids: set[int] | None = None,
                            medical_conditions: list[str] | None = None,
                            protocols: dict | None = None,
                            ) -> list[tuple[dict, float]]:
        """Возвращает топ-N планов, разнообразных по модальности.

        Алгоритм: жадно выбираем самый высокий план, потом из оставшихся
        — самый высокий с другой модальностью, и так далее. Это даёт
        пользователю несколько разных типов тренировок в недельном цикле.

        Если переданы medical_conditions и protocols, дополнительно
        отсеиваются планы, противопоказанные по клиническим правилам.
        Это safety-net: ML-модель может изредка ошибаться, а жёсткий
        фильтр гарантирует отсутствие опасных рекомендаций.
        """
        from logic.clinical_rules import is_plan_contraindicated

        ranked = self.rank_all_plans(user)
        forbidden_plan_ids = forbidden_plan_ids or set()
        ranked = [(p, s) for p, s in ranked
                  if p["plan_id"] not in forbidden_plan_ids]

        # Safety-фильтр: убираем противопоказанные планы
        if medical_conditions and protocols is not None:
            ranked_safe = []
            for p, s in ranked:
                contra, _reason = is_plan_contraindicated(
                    user, p, medical_conditions, protocols)
                if not contra:
                    ranked_safe.append((p, s))
            if ranked_safe:
                ranked = ranked_safe

        selected: list[tuple[dict, float]] = []
        used_modalities: list[str] = []

        # Сначала берём планы с разными модальностями
        for plan, score in ranked:
            if plan["modality"] not in used_modalities:
                selected.append((plan, score))
                used_modalities.append(plan["modality"])
                if len(selected) == n:
                    return selected

        # Если модальностей не хватило — добираем по убыванию скора
        for plan, score in ranked:
            if (plan, score) not in selected:
                selected.append((plan, score))
                if len(selected) == n:
                    break
        return selected
