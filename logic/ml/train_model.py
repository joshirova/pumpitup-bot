import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
import pickle
from pathlib import Path

# Пути к файлам
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "ml_model.pkl"
ENCODERS_PATH = BASE_DIR / "label_encoders.pkl"
DATASET_PATH = BASE_DIR / "ml_dataset.csv"

# Загрузка датасета
df = pd.read_csv(DATASET_PATH)

# Кодируем категориальные признаки
label_encoders = {}
X = pd.DataFrame()

for column in ["goal", "gender", "age_group", "level", "type"]:
    le = LabelEncoder()
    X[column] = le.fit_transform(df[column])
    label_encoders[column] = le

# Добавим BMI как числовой признак
X["bmi"] = df["bmi"]

# Целевая переменная
y = df["plan_index"]

# Обучение модели
model = DecisionTreeClassifier(max_depth=5, random_state=42)
model.fit(X, y)

# Сохраняем модель
with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

# Сохраняем энкодеры
with open(ENCODERS_PATH, "wb") as f:
    pickle.dump(label_encoders, f)

print("✅ Модель и энкодеры успешно обучены и сохранены.")
